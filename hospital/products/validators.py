"""
Hospital Staffing — Validateurs de contraintes dures
=====================================================
8 fonctions indépendantes, une par contrainte.
Chacune lève ValidationError avec un message détaillé.
"""

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import (
    Absence, Certification, Contract, Preference, Rule,
    Shift, ShiftAssignment, ShiftRequiredCertification,
    Staff, StaffCertification,
)


# ══════════════════════════════════════════════════════════════════════════════
# C-01  Chevauchement horaire
# ══════════════════════════════════════════════════════════════════════════════

def check_no_overlap(staff: Staff, shift: Shift, exclude_assignment_id: int = None):
    """
    Détecte tout chevauchement entre le shift proposé et les affectations
    existantes du soignant, même partiel (y compris shifts imbriqués).

    Algorithme :
        Deux intervalles [A_start, A_end[ et [B_start, B_end[ se chevauchent
        si et seulement si :  A_start < B_end  ET  A_end > B_start
        (intervalles semi-ouverts — deux shifts adjacents bout-à-bout
        ne sont PAS considérés comme chevauchants).

    Couverture des cas :
        NOUVEAU :   [=======]           existant contient nouveau
        EXISTANT :  [===========]

        NOUVEAU :   [===========]       nouveau contient existant
        EXISTANT :    [=======]

        NOUVEAU :   [=======]           chevauchement à gauche
        EXISTANT :        [=======]

        NOUVEAU :         [=======]     chevauchement à droite
        EXISTANT :   [=======]

        NOUVEAU :   [===]               adjacents → OK, pas de conflit
        EXISTANT :        [===]

    exclude_assignment_id : identifiant de l'affectation en cours de
    modification (PATCH) à exclure pour éviter un faux positif sur soi-même.
    """
    if shift.start_datetime >= shift.end_datetime:
        raise ValidationError(
            f"Créneau invalide : start ({shift.start_datetime}) "
            f"doit être strictement antérieur à end ({shift.end_datetime})."
        )

    qs = (
        ShiftAssignment.objects
        .filter(
            staff=staff,
            shift__start_datetime__lt=shift.end_datetime,
            shift__end_datetime__gt=shift.start_datetime,
        )
        .select_related("shift__shift_type", "shift__care_unit__service")
    )
    if exclude_assignment_id:
        qs = qs.exclude(pk=exclude_assignment_id)

    conflicts = list(qs)
    if not conflicts:
        return

    lines = [
        f"  • {a.shift.shift_type.name} — {a.shift.care_unit} "
        f"({a.shift.start_datetime:%d/%m/%Y %H:%M}→{a.shift.end_datetime:%H:%M})"
        for a in conflicts
    ]
    raise ValidationError(
        f"{staff} a {len(conflicts)} affectation(s) qui chevauche(nt) "
        f"le créneau {shift.start_datetime:%d/%m/%Y %H:%M}–{shift.end_datetime:%H:%M} :\n"
        + "\n".join(lines)
    )


# ══════════════════════════════════════════════════════════════════════════════
# C-02  Certifications requises et non expirées
# ══════════════════════════════════════════════════════════════════════════════

def check_certifications(staff: Staff, shift: Shift):
    """
    Le soignant doit posséder TOUTES les certifications requises par le shift,
    et aucune ne doit être expirée à la date de DÉBUT de la garde.

    Logique pas-à-pas :

    1. Lire les certifications requises dans ShiftRequiredCertification.
       Si aucune → validation immédiatement réussie.

    2. Pour chaque certification requise, chercher dans StaffCertification
       une entrée valide :
           obtained_date <= shift_date
           ET (expiration_date IS NULL  OU  expiration_date >= shift_date)

    3. Construire deux ensembles distincts pour le message d'erreur :
         ABSENTES : le soignant n'a jamais eu cette certification
         EXPIRÉES : il l'a eue mais elle est périmée à la date du shift

    Date de référence = date de début du shift (le soignant doit être
    certifié au moment où il prend son poste).
    """
    shift_date = shift.start_datetime.date()

    # 1. certifications exigées
    required_ids = list(
        ShiftRequiredCertification.objects
        .filter(shift=shift)
        .values_list("certification_id", flat=True)
    )
    if not required_ids:
        return

    # 2. certifications valides détenues par le soignant
    valid_ids = set(
        StaffCertification.objects
        .filter(
            staff=staff,
            certification_id__in=required_ids,
            obtained_date__lte=shift_date,
        )
        .filter(
            Q(expiration_date__isnull=True) | Q(expiration_date__gte=shift_date)
        )
        .values_list("certification_id", flat=True)
    )

    missing_ids = set(required_ids) - valid_ids
    if not missing_ids:
        return

    # 3. différencier absentes / expirées
    expired_rows = (
        StaffCertification.objects
        .filter(
            staff=staff,
            certification_id__in=missing_ids,
            expiration_date__lt=shift_date,
        )
        .select_related("certification")
    )
    expired_ids = {r.certification_id for r in expired_rows}
    absent_ids  = missing_ids - expired_ids

    parts = []
    if absent_ids:
        names = list(
            Certification.objects.filter(pk__in=absent_ids)
            .values_list("name", flat=True)
        )
        parts.append("Absente(s) : " + ", ".join(names))

    if expired_ids:
        details = ", ".join(
            f"{r.certification.name} (expirée le {r.expiration_date:%d/%m/%Y})"
            for r in expired_rows
        )
        parts.append("Expirée(s) : " + details)

    raise ValidationError(
        f"Certification(s) insuffisante(s) pour {staff} "
        f"(shift du {shift_date:%d/%m/%Y}) — " + " / ".join(parts) + "."
    )


# ══════════════════════════════════════════════════════════════════════════════
# C-03  Repos minimal post-garde de nuit
# ══════════════════════════════════════════════════════════════════════════════

def check_night_shift_rest(staff: Staff, shift: Shift):
    """
    Après toute garde de nuit terminée, un repos minimal doit s'écouler
    avant le DÉBUT de toute nouvelle affectation (peu importe son type).

    Logique pas-à-pas :

    1. Lire la durée de repos depuis Rule(rule_type='min_rest_after_night').
       Unité attendue : heures (champ `value`).
       Fallback : 11 h (directive UE 2003/88/CE).

    2. Identifier la garde de nuit la plus récente du soignant qui s'est
       terminée AVANT (strictement) le début du nouveau shift.
       Une garde est "de nuit" si :
           ShiftType.name contient "nuit"  (insensible à la casse)
           OU ShiftType.requires_rest_after = True

    3. earliest_allowed = fin_garde_nuit + durée_repos
       Si shift.start_datetime < earliest_allowed → violation.
       (Débuter exactement à earliest_allowed est autorisé.)

    Cas limites :
        Aucune garde de nuit antérieure → pas de contrainte.
        Garde chevauchant minuit → on considère l'heure de FIN, pas de début.
        Plusieurs gardes de nuit successives → seule la plus récente compte.
    """
    # 1. durée configurable
    try:
        rule = Rule.objects.get(rule_type="min_rest_after_night")
        rest_hours = float(rule.value)
    except Rule.DoesNotExist:
        rest_hours = 11.0

    # 2. dernière garde de nuit terminée avant ce shift
    last_night = (
        ShiftAssignment.objects
        .filter(
            staff=staff,
            shift__end_datetime__lte=shift.start_datetime,
        )
        .filter(
            Q(shift__shift_type__name__icontains="nuit") |
            Q(shift__shift_type__requires_rest_after=True)
        )
        .order_by("-shift__end_datetime")
        .select_related("shift__shift_type")
        .first()
    )
    if last_night is None:
        return

    # 3. calcul et vérification
    night_end        = last_night.shift.end_datetime
    earliest_allowed = night_end + timedelta(hours=rest_hours)

    if shift.start_datetime < earliest_allowed:
        remaining     = earliest_allowed - shift.start_datetime
        total_seconds = int(remaining.total_seconds())
        h, r          = divmod(total_seconds, 3600)
        m             = r // 60
        raise ValidationError(
            f"Repos post-garde de nuit insuffisant pour {staff}. "
            f"Dernière garde : '{last_night.shift.shift_type.name}' "
            f"terminée le {night_end:%d/%m/%Y à %H:%M}. "
            f"Repos réglementaire : {rest_hours:.0f}h → "
            f"début autorisé à partir du {earliest_allowed:%d/%m/%Y à %H:%M} "
            f"(il manque encore {h}h{m:02d})."
        )


# ══════════════════════════════════════════════════════════════════════════════
# C-04  Seuil minimal / maximal de soignants sur un shift
# ══════════════════════════════════════════════════════════════════════════════

def check_minimum_staffing_on_delete(shift: Shift):
    """
    Appelée APRÈS suppression d'une affectation (dans transaction.atomic).
    Si le nombre de soignants restants passe sous shift.min_staff,
    l'exception déclenche le rollback automatique.

    Logique :
    1. min_staff <= 0 → aucun seuil défini, on sort immédiatement.
    2. Compter les affectations restantes sur ce shift.
    3. Si count < min_staff → refus.
    """
    if shift.min_staff <= 0:
        return

    remaining = ShiftAssignment.objects.filter(shift=shift).count()
    if remaining < shift.min_staff:
        shortage = shift.min_staff - remaining
        raise ValidationError(
            f"Suppression refusée : '{shift.shift_type.name}' "
            f"du {shift.start_datetime:%d/%m/%Y %H:%M} "
            f"à '{shift.care_unit}' passerait à {remaining} soignant(s) "
            f"affecté(s), sous le seuil de sécurité de {shift.min_staff}. "
            f"Trouvez d'abord {shortage} remplaçant(s)."
        )


def check_maximum_staffing_on_create(shift: Shift):
    """
    Appelée AVANT création d'une affectation.
    max_staff <= 0 signifie « pas de plafond ».
    """
    if shift.max_staff <= 0:
        return

    current = ShiftAssignment.objects.filter(shift=shift).count()
    if current >= shift.max_staff:
        raise ValidationError(
            f"Capacité maximale atteinte pour '{shift.shift_type.name}' "
            f"du {shift.start_datetime:%d/%m/%Y %H:%M} "
            f"({current}/{shift.max_staff} soignants). Affectation impossible."
        )


# ══════════════════════════════════════════════════════════════════════════════
# C-05  Contrat actif autorisant ce type de garde
# ══════════════════════════════════════════════════════════════════════════════

def check_contract_allows_shift(staff: Staff, shift: Shift):
    """
    Deux sous-contraintes :
        A) Le soignant possède un contrat actif à la date du shift.
        B) Ce contrat autorise le type de garde demandé.

    Logique pas-à-pas :

    1. Chercher un contrat actif à shift_date :
           start_date <= shift_date
           ET (end_date IS NULL  OU  end_date >= shift_date)
       En cas de contrats multiples actifs (chevauchement),
       on prend le plus récent (start_date MAX).

    2. Aucun contrat → erreur contextualisée avec le dernier contrat connu.

    3. Détection "garde de nuit" (multi-critères, par ordre de priorité) :
         a. ShiftType.name contient "nuit"  (tag explicite)
         b. ShiftType.requires_rest_after = True  (flag générique)
         c. Heure de début entre 21h et 05h59  (heure locale)

    4. Si garde de nuit ET contract_type.night_shift_allowed = False → refus
       avec détail du critère de détection utilisé.
    """
    shift_date = shift.start_datetime.date()

    # 1. contrat actif le plus récent
    active = (
        Contract.objects
        .filter(staff=staff, start_date__lte=shift_date)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=shift_date))
        .order_by("-start_date")
        .select_related("contract_type")
        .first()
    )

    # 2. pas de contrat actif
    if not active:
        last = (
            Contract.objects.filter(staff=staff)
            .order_by("-start_date")
            .select_related("contract_type")
            .first()
        )
        if last and last.end_date:
            raise ValidationError(
                f"{staff} n'a pas de contrat actif au {shift_date:%d/%m/%Y}. "
                f"Dernier contrat : '{last.contract_type.name}' "
                f"(du {last.start_date:%d/%m/%Y} au {last.end_date:%d/%m/%Y}, expiré)."
            )
        raise ValidationError(
            f"{staff} n'a aucun contrat enregistré dans le système."
        )

    # 3. détection garde de nuit
    hour           = shift.start_datetime.hour
    night_by_name  = "nuit" in shift.shift_type.name.lower()
    night_by_flag  = shift.shift_type.requires_rest_after
    night_by_hour  = (hour >= 21 or hour < 6)
    is_night       = night_by_name or night_by_flag or night_by_hour

    # 4. vérification autorisation
    if is_night and not active.contract_type.night_shift_allowed:
        if night_by_name:
            detection = f"type de shift '{shift.shift_type.name}' contient 'nuit'"
        elif night_by_flag:
            detection = "ShiftType.requires_rest_after = True"
        else:
            detection = f"heure de début {hour:02d}h (plage 21h–06h)"

        raise ValidationError(
            f"Le contrat de {staff} ('{active.contract_type.name}', "
            f"depuis le {active.start_date:%d/%m/%Y}) "
            f"n'autorise pas les gardes de nuit. "
            f"Détecté via : {detection}."
        )


# ══════════════════════════════════════════════════════════════════════════════
# C-06  Absence déclarée
# ══════════════════════════════════════════════════════════════════════════════

def check_no_absence(staff: Staff, shift: Shift):
    """
    Un soignant en absence déclarée ne peut pas être affecté,
    quelle que soit la raison (maladie, congé, formation…).

    Logique pas-à-pas :

    1. Date de référence = date de DÉBUT du shift.

    2. Une absence couvre shift_date si :
           start_date <= shift_date
           ET l'une des deux conditions :
               — absence encore ouverte (pas de retour réel) :
                     actual_end_date IS NULL
                     ET expected_end_date >= shift_date
               — absence clôturée mais retour réel >= shift_date :
                     actual_end_date IS NOT NULL
                     ET actual_end_date >= shift_date

       Priorité à actual_end_date sur expected_end_date :
           Retour anticipé (actual < expected) → disponible dès actual + 1j.
           Prolongation (actual > expected) → bloqué jusqu'à actual_end_date.

    3. Si une absence est trouvée → refus avec type, dates, planifiée ou non.
    """
    shift_date = shift.start_datetime.date()

    absence = (
        Absence.objects
        .filter(staff=staff, start_date__lte=shift_date)
        .filter(
            Q(actual_end_date__isnull=True,  expected_end_date__gte=shift_date) |
            Q(actual_end_date__isnull=False, actual_end_date__gte=shift_date)
        )
        .select_related("absence_type")
        .first()
    )

    if not absence:
        return

    end_date    = absence.actual_end_date or absence.expected_end_date
    planned_lbl = "planifiée" if absence.is_planned else "non planifiée (urgente)"

    raise ValidationError(
        f"{staff} est en absence {planned_lbl} "
        f"(motif : '{absence.absence_type.name}') "
        f"du {absence.start_date:%d/%m/%Y} au {end_date:%d/%m/%Y}. "
        f"Affectation au {shift_date:%d/%m/%Y} impossible."
    )


# ══════════════════════════════════════════════════════════════════════════════
# C-07  Quota d'heures hebdomadaires contractuelles
# ══════════════════════════════════════════════════════════════════════════════

def check_weekly_hours_quota(staff: Staff, shift: Shift, exclude_assignment_id: int = None):
    """
    Le total des heures planifiées dans la semaine ISO (lundi–dimanche)
    ne peut pas dépasser le quota hebdomadaire contractuel proratisé.

    Logique pas-à-pas :

    1. Semaine ISO : lundi = shift_date - shift_date.weekday()
                    dimanche = lundi + 6 jours

    2. Quota effectif :
           max_hours_per_week (du ContractType)
           × workload_percent / 100  (du Contract)
       Exemple : CDI 35h/sem à 80% → quota = 28h.

    3. Heures déjà planifiées = Σ ShiftType.duration_hours
       pour toutes les affectations du soignant dont le start_datetime
       tombe dans [lundi, dimanche].
       On utilise duration_hours (champ du modèle) et non (end - start)
       pour rester cohérent avec le modèle de données.

    4. Heures nouvelles = shift.shift_type.duration_hours.

    5. Si planned + new > quota → refus avec détail du dépassement.

    Cas limites :
        Un shift débutant lundi 23h et finissant mardi 7h est comptabilisé
        dans la semaine de son DÉBUT (lundi).
        exclude_assignment_id : en PATCH, exclure l'ancienne affectation
        pour ne pas compter ses heures deux fois.
        Aucun contrat actif → on laisse passer (C-05 a déjà refusé).
    """
    shift_date = shift.start_datetime.date()

    # 1. semaine ISO
    monday = shift_date - timedelta(days=shift_date.weekday())
    sunday = monday + timedelta(days=6)

    # 2. quota contractuel effectif
    active = (
        Contract.objects
        .filter(staff=staff, start_date__lte=shift_date)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=shift_date))
        .order_by("-start_date")
        .select_related("contract_type")
        .first()
    )
    if not active:
        return  # géré par C-05

    max_weekly    = active.contract_type.max_hours_per_week
    workload_rate = active.workload_percent / 100.0
    quota         = max_weekly * workload_rate

    # 3. heures déjà planifiées cette semaine
    week_qs = (
        ShiftAssignment.objects
        .filter(
            staff=staff,
            shift__start_datetime__date__gte=monday,
            shift__start_datetime__date__lte=sunday,
        )
        .select_related("shift__shift_type")
    )
    if exclude_assignment_id:
        week_qs = week_qs.exclude(pk=exclude_assignment_id)

    planned = sum(a.shift.shift_type.duration_hours for a in week_qs)

    # 4 + 5. vérification
    new_hours = shift.shift_type.duration_hours
    total     = planned + new_hours

    if total > quota:
        overflow = total - quota
        raise ValidationError(
            f"Quota hebdomadaire dépassé pour {staff} "
            f"(semaine du {monday:%d/%m} au {sunday:%d/%m/%Y}) : "
            f"{planned}h planifiées + {new_hours}h (ce shift) = {total}h "
            f"> {quota:.1f}h autorisées "
            f"({max_weekly}h × {int(workload_rate * 100)}% — "
            f"contrat '{active.contract_type.name}'). "
            f"Dépassement : +{overflow:.1f}h."
        )


# ══════════════════════════════════════════════════════════════════════════════
# C-08  Contraintes impératives du soignant (F-07)
# ══════════════════════════════════════════════════════════════════════════════

_WEEKDAY_TAGS = {
    "no_monday": 0, "no_tuesday": 1, "no_wednesday": 2,
    "no_thursday": 3, "no_friday": 4, "no_saturday": 5, "no_sunday": 6,
    "no_lundi": 0, "no_mardi": 1, "no_mercredi": 2,
    "no_jeudi": 3, "no_vendredi": 4, "no_samedi": 5, "no_dimanche": 6,
}


def check_hard_preferences(staff: Staff, shift: Shift):
    """
    Évalue chaque contrainte impérative (is_hard_constraint=True,
    type='contrainte') active à la date du shift.

    Logique pas-à-pas :

    1. Récupérer les Preference du soignant avec :
           is_hard_constraint = True  et  type = 'contrainte'
           (start_date IS NULL  OU  start_date <= shift_date)
           (end_date   IS NULL  OU  end_date   >= shift_date)

    2. Pour chaque contrainte, interpréter le champ `description` comme
       un TAG structuré (insensible à la casse) :

       TAG                      VIOLATION si…
       ──────────────────────────────────────────────────────────────────
       no_night                 shift est de nuit (mêmes critères que C-05)
       no_weekend               shift commence un samedi ou dimanche
       no_monday … no_sunday    shift commence ce jour (EN ou FR)
       no_unit:<id>             shift dans l'unité de soins n°<id>
       no_service:<id>          shift dans le service n°<id>
       no_shift_type:<id>       shift de ce ShiftType
       ──────────────────────────────────────────────────────────────────

    3. TOUTES les violations sont collectées avant de lever l'exception
       (retour exhaustif en une seule passe pour l'appelant).

    Cas limites :
        Contrainte sans start_date ni end_date → permanente.
        is_hard_constraint = False → ignorée ici (soft, pour le moteur d'optim).
        Tag inconnu → ignoré silencieusement (fail-open) pour éviter les
        blocages sur fautes de frappe — à loguer en production.
    """
    shift_date    = shift.start_datetime.date()
    shift_weekday = shift.start_datetime.weekday()
    shift_hour    = shift.start_datetime.hour
    errors        = []

    # 1. contraintes impératives actives
    constraints = Preference.objects.filter(
        staff=staff,
        is_hard_constraint=True,
        type="contrainte",
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=shift_date)
    ).filter(
        Q(end_date__isnull=True)   | Q(end_date__gte=shift_date)
    )

    for c in constraints:
        tag = c.description.strip().lower()

        # ── no_night ────────────────────────────────────────────────────
        if tag == "no_night":
            is_night = (
                "nuit" in shift.shift_type.name.lower()
                or shift.shift_type.requires_rest_after
                or shift_hour >= 21
                or shift_hour < 6
            )
            if is_night:
                errors.append(
                    f"Contrainte '{c.description}' : {staff} ne peut pas "
                    f"faire de gardes de nuit "
                    f"(shift '{shift.shift_type.name}' à {shift_hour:02d}h)."
                )

        # ── no_weekend ──────────────────────────────────────────────────
        elif tag == "no_weekend":
            if shift_weekday >= 5:
                day_name = "samedi" if shift_weekday == 5 else "dimanche"
                errors.append(
                    f"Contrainte '{c.description}' : {staff} ne travaille "
                    f"pas le week-end (shift le {day_name} {shift_date:%d/%m/%Y})."
                )

        # ── no_<jour> ───────────────────────────────────────────────────
        elif tag in _WEEKDAY_TAGS:
            if shift_weekday == _WEEKDAY_TAGS[tag]:
                errors.append(
                    f"Contrainte '{c.description}' : {staff} n'est pas "
                    f"disponible ce jour ({shift_date:%A %d/%m/%Y})."
                )

        # ── no_unit:<id> ────────────────────────────────────────────────
        elif tag.startswith("no_unit:"):
            try:
                unit_id = int(tag.split(":", 1)[1].strip())
                if shift.care_unit_id == unit_id:
                    errors.append(
                        f"Contrainte '{c.description}' : {staff} ne peut "
                        f"pas être affecté(e) à l'unité '{shift.care_unit}'."
                    )
            except (ValueError, IndexError):
                pass  # tag malformé → fail-open

        # ── no_service:<id> ─────────────────────────────────────────────
        elif tag.startswith("no_service:"):
            try:
                service_id = int(tag.split(":", 1)[1].strip())
                if shift.care_unit.service_id == service_id:
                    errors.append(
                        f"Contrainte '{c.description}' : {staff} ne peut "
                        f"pas être affecté(e) au service '{shift.care_unit.service}'."
                    )
            except (ValueError, IndexError):
                pass

        # ── no_shift_type:<id> ──────────────────────────────────────────
        elif tag.startswith("no_shift_type:"):
            try:
                stype_id = int(tag.split(":", 1)[1].strip())
                if shift.shift_type_id == stype_id:
                    errors.append(
                        f"Contrainte '{c.description}' : {staff} ne peut "
                        f"pas effectuer le type de garde '{shift.shift_type.name}'."
                    )
            except (ValueError, IndexError):
                pass

        # ── tag inconnu → fail-open ─────────────────────────────────────
        # else: logger.warning("Tag inconnu : '%s' (preference id=%s)", tag, c.pk)

    if errors:
        raise ValidationError(errors)