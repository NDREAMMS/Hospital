"""
Hospital Staffing — Validateurs de contraintes molles (implémentation complète)
==============================================================================
Chaque fonction retourne une pénalité numérique normalisée (0 si la contrainte est respectée).
Les poids sont configurables via le modèle Rule en base de données.
"""

from datetime import timedelta, date
from django.db.models import Q, Count
from .models import (
    Staff, Shift, ShiftAssignment, Preference, Rule,
    ContractType, Service, StaffServiceAssignment, StaffRole,
)


PENALTY_NIGHT_CONSECUTIVE = 100
PENALTY_PREFERENCE_VIOLATION = 50
PENALTY_WORKLOAD_IMBALANCE = 75
PENALTY_SERVICE_CHANGE = 60
PENALTY_WEEKEND_RATIO = 40
PENALTY_NEW_SERVICE_WITHOUT_ADAPTATION = 80
PENALTY_LACK_OF_CONTINUITY = 90


def _get_rule_value(rule_type: str, default: float) -> float:
    """Récupère la valeur d'une règle ou retourne la valeur par défaut."""
    try:
        return float(Rule.objects.get(rule_type=rule_type).value)
    except Rule.DoesNotExist:
        return default


def _is_night_shift(shift: Shift) -> bool:
    """Détermine si un shift est une garde de nuit."""
    return (
        "nuit" in shift.shift_type.name.lower()
        or shift.shift_type.requires_rest_after
        or shift.start_datetime.hour >= 21
        or shift.start_datetime.hour < 6
    )


def _is_weekend(shift: Shift) -> bool:
    """Détermine si un shift est un week-end (samedi ou dimanche)."""
    return shift.start_datetime.weekday() >= 5


def _get_iso_week(self, shift_date):
    """Calcule le lundi et dimanche de la semaine ISO."""
    monday = shift_date - timedelta(days=shift_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _get_staff_role(staff: Staff) -> str | None:
    """Récupère le rôle principal du soignant."""
    sr = StaffRole.objects.select_related("role").filter(staff=staff).first()
    return sr.role.name if sr else None


def _get_staff_service_history(staff: Staff) -> set:
    """Récupère l'historique des services où le soignant a travaillé."""
    assignment_services = set(
        StaffServiceAssignment.objects.filter(staff=staff)
        .values_list('service_id', flat=True)
    )
    shift_services = set(
        ShiftAssignment.objects.filter(staff=staff)
        .select_related('shift__care_unit__service')
        .values_list('shift__care_unit__service_id', flat=True)
    )
    return assignment_services | shift_services


def _get_weekend_count_for_staff(staff: Staff, start_date, end_date) -> int:
    """Compte le nombre de week-ends travaillés par un soignant sur une période."""
    assignments = ShiftAssignment.objects.filter(
        staff=staff,
        shift__start_datetime__date__gte=start_date,
        shift__start_datetime__date__lte=end_date,
    )
    return sum(1 for a in assignments if _is_weekend(a.shift))


def _get_consecutive_nights_count(staff: Staff, shift_date: date) -> int:
    """Compte le nombre de nuits consécutives autour d'une date."""
    consecutive = 0
    check_date = shift_date

    while True:
        has_night = ShiftAssignment.objects.filter(
            staff=staff,
            shift__start_datetime__date=check_date,
        ).filter(
            Q(shift__shift_type__name__icontains="nuit")
            | Q(shift__start_datetime__hour__gte=21)
            | Q(shift__start_datetime__hour__lt=6)
        ).exists()

        if has_night:
            consecutive += 1
            check_date -= timedelta(days=1)
        else:
            break

    return consecutive


def _get_services_this_week(staff: Staff, shift_date) -> set:
    """Récupère les services d'un soignant pour la semaine ISO."""
    monday = shift_date - timedelta(days=shift_date.weekday())
    sunday = monday + timedelta(days=6)

    return set(
        ShiftAssignment.objects.filter(
            staff=staff,
            shift__start_datetime__date__gte=monday,
            shift__start_datetime__date__lte=sunday,
        ).select_related('shift__care_unit__service')
        .values_list('shift__care_unit__service_id', flat=True)
    )


def _get_same_grade_staff_ids(staff: Staff, service_id: int) -> list:
    """Récupère les IDs des soignants de même rôle dans un service."""
    role = _get_staff_role(staff)
    if not role:
        return list(
            Staff.objects.filter(is_active=True)
            .values_list('id', flat=True)
        )

    return list(
        Staff.objects.filter(
            is_active=True,
            staff_roles__role__name=role,
            service_assignments__service_id=service_id,
            service_assignments__end_date__isnull=True,
        ).values_list('id', flat=True)
    )


def _get_staff_workload_this_week(staff_id: int, shift_date, role_staff_ids: list) -> dict:
    """Calcule la charge de travail (heures) par soignant pour la semaine."""
    monday = shift_date - timedelta(days=shift_date.weekday())
    sunday = monday + timedelta(days=6)

    workloads = {}
    for sid in role_staff_ids:
        hours = sum(
            a.shift.shift_type.duration_hours
            for a in ShiftAssignment.objects.filter(
                staff_id=sid,
                shift__start_datetime__date__gte=monday,
                shift__start_datetime__date__lte=sunday,
            ).select_related('shift__shift_type')
        )
        workloads[sid] = hours

    return workloads


def _calculate_std_dev(values: list) -> float:
    """Calcule l'écart-type d'une liste de valeurs."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def _get_quarter_dates(shift_date: date) -> tuple:
    """Retourne les dates de début et fin du trimestre."""
    quarter_start_month = (shift_date.month - 1) // 3 * 3 + 1
    quarter_start = date(shift_date.year, quarter_start_month, 1)

    if quarter_start_month == 10:
        quarter_end = date(shift_date.year + 1, 1, 1) - timedelta(days=1)
    elif quarter_start_month == 7:
        quarter_end = date(shift_date.year, 10, 1) - timedelta(days=1)
    elif quarter_start_month == 4:
        quarter_end = date(shift_date.year, 7, 1) - timedelta(days=1)
    else:
        quarter_end = date(shift_date.year, 4, 1) - timedelta(days=1)

    return quarter_start, quarter_end


def _get_patient_group_key(shift: Shift) -> str | None:
    """
    Détermine la clé du groupe de patients/postes pour la continuité des soins.
    Retourne None si le service ne requiert pas de continuité.
    """
    if hasattr(shift.care_unit, 'requires_continuity') and not shift.care_unit.requires_continuity:
        return None
    return f"unit_{shift.care_unit_id}"


def _get_previous_day_assignment(staff: Staff, shift: Shift) -> ShiftAssignment | None:
    """Récupère l'affectation du jour précédent pour le même groupe."""
    previous_date = shift.start_datetime.date() - timedelta(days=1)
    group_key = _get_patient_group_key(shift)

    if not group_key:
        return None

    return (
        ShiftAssignment.objects.filter(
            staff=staff,
            shift__start_datetime__date=previous_date,
            shift__care_unit_id=shift.care_unit_id,
        ).select_related('shift__care_unit')
        .first()
    )


def evaluate_consecutive_nights(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-01: Pénalité si le shift proposé entraîne plus de N nuits consécutives.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel (peut contenir consecutive_nights)

    Returns:
        Pénalité normalisée (0 si respecté)
    """
    if not _is_night_shift(shift):
        return 0.0

    max_consecutive = int(_get_rule_value("max_consecutive_nights", 3))

    if context and 'consecutive_nights' in context:
        current_consecutive = context['consecutive_nights']
    else:
        current_consecutive = _get_consecutive_nights_count(staff, shift.start_datetime.date())

    new_consecutive = current_consecutive + 1

    if new_consecutive > max_consecutive:
        excess = new_consecutive - max_consecutive
        return PENALTY_NIGHT_CONSECUTIVE * excess

    return 0.0


def evaluate_preference_violation(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-02: Pénalité si le shift proposé viole une préférence molle du soignant.

    Les préférences molles sont de type='preference' et is_hard_constraint=False.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel

    Returns:
        Pénalité normalisée (0 si respecté)
    """
    shift_date = shift.start_datetime.date()
    shift_weekday = shift.start_datetime.weekday()
    shift_hour = shift.start_datetime.hour
    is_night = _is_night_shift(shift)
    is_weekend = _is_weekend(shift)

    soft_preferences = Preference.objects.filter(
        staff=staff,
        is_hard_constraint=False,
        type="preference",
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=shift_date)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=shift_date)
    )

    penalty = 0.0
    for pref in soft_preferences:
        tag = pref.description.strip().lower()

        if tag == "pref_no_night" or tag == "no_night":
            if is_night:
                penalty += PENALTY_PREFERENCE_VIOLATION * 0.8

        elif tag == "pref_morning" or tag == "prefer_morning":
            if not (6 <= shift_hour < 12):
                penalty += PENALTY_PREFERENCE_VIOLATION * 0.5

        elif tag == "pref_afternoon" or tag == "prefer_afternoon":
            if not (12 <= shift_hour < 18):
                penalty += PENALTY_PREFERENCE_VIOLATION * 0.5

        elif tag == "pref_evening" or tag == "prefer_evening":
            if not (18 <= shift_hour < 22):
                penalty += PENALTY_PREFERENCE_VIOLATION * 0.5

        elif tag == "pref_no_weekend" or tag == "no_weekend":
            if is_weekend:
                penalty += PENALTY_PREFERENCE_VIOLATION * 0.7

        elif tag.startswith("pref_unit:") or tag.startswith("prefer_unit:"):
            try:
                unit_id = int(tag.split(":")[1].strip())
                if shift.care_unit_id != unit_id:
                    penalty += PENALTY_PREFERENCE_VIOLATION * 0.3
            except (ValueError, IndexError):
                pass

        elif tag.startswith("pref_service:") or tag.startswith("prefer_service:"):
            try:
                service_id = int(tag.split(":")[1].strip())
                if shift.care_unit.service_id != service_id:
                    penalty += PENALTY_PREFERENCE_VIOLATION * 0.3
            except (ValueError, IndexError):
                pass

    return min(penalty, PENALTY_PREFERENCE_VIOLATION * 2)


def evaluate_workload_imbalance(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-03: Pénalité si l'affectation déséquilibre la charge de travail.

    Compare le nombre d'heures attribuées aux soignants de même grade/rôle
    dans le même service sur la semaine ISO.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel

    Returns:
        Pénalité normalisée (0 si équilibré)
    """
    shift_date = shift.start_datetime.date()
    service_id = shift.care_unit.service_id
    new_hours = shift.shift_type.duration_hours

    role_staff_ids = _get_same_grade_staff_ids(staff, service_id)

    if context and 'all_week_assignments' in context:
        all_assignments = context['all_week_assignments']
        workloads = {}
        for sid in role_staff_ids:
            hours = sum(
                a.shift.shift_type.duration_hours
                for a in all_assignments
                if a.staff_id == sid
            )
            workloads[sid] = hours
    else:
        workloads = _get_staff_workload_this_week(staff, shift_date, role_staff_ids)

    workloads[staff.id] = workloads.get(staff.id, 0) + new_hours

    values = list(workloads.values())
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0

    std_dev = _calculate_std_dev(values)
    max_allowed_std = mean * 0.3

    if std_dev > max_allowed_std:
        excess = (std_dev - max_allowed_std) / max_allowed_std
        return PENALTY_WORKLOAD_IMBALANCE * excess

    return 0.0


def evaluate_service_change(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-04: Pénalité si le soignant change de service sur une même semaine.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel (peut contenir services_this_week)

    Returns:
        Pénalité normalisée (0 si un seul service)
    """
    shift_date = shift.start_datetime.date()
    new_service_id = shift.care_unit.service_id

    if context and 'services_this_week' in context:
        services = context['services_this_week']
    else:
        services = _get_services_this_week(staff, shift_date)

    services.add(new_service_id)

    if len(services) > 1:
        return PENALTY_SERVICE_CHANGE * (len(services) - 1)

    return 0.0


def evaluate_weekend_ratio(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-05: Pénalité pour les déséquilibres dans la répartition des gardes de week-end
    sur un trimestre.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel

    Returns:
        Pénalité normalisée (0 si équilibré)
    """
    if not _is_weekend(shift):
        return 0.0

    shift_date = shift.start_datetime.date()
    quarter_start, quarter_end = _get_quarter_dates(shift_date)

    service_id = shift.care_unit.service_id
    role = _get_staff_role(staff)

    same_role_staff = Staff.objects.filter(
        is_active=True,
    )
    if role:
        same_role_staff = same_role_staff.filter(staff_roles__role__name=role)

    same_role_staff = same_role_staff.filter(
        service_assignments__service_id=service_id,
        service_assignments__end_date__isnull=True,
    )

    weekend_counts = {}
    for s in same_role_staff:
        weekend_counts[s.id] = _get_weekend_count_for_staff(s, quarter_start, quarter_end)

    weekend_counts[staff.id] = weekend_counts.get(staff.id, 0) + 1

    values = list(weekend_counts.values())
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0

    std_dev = _calculate_std_dev(values)
    max_allowed_std = max(mean * 0.5, 1)

    if std_dev > max_allowed_std:
        staff_we = weekend_counts[staff.id]
        deviation = abs(staff_we - mean) / mean if mean > 0 else 0
        return PENALTY_WEEKEND_RATIO * deviation

    return 0.0


def evaluate_new_service_adaptation(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-06: Pénalité si le soignant est affecté à un service où il n'a jamais
    travaillé sans période d'intégration.

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel

    Returns:
        Pénalité normalisée (0 si service connu ou adaptation)
    """
    service_id = shift.care_unit.service_id
    history = _get_staff_service_history(staff)

    if service_id not in history:
        min_shifts_required = int(_get_rule_value("min_shifts_for_new_service", 3))

        recent_shifts_in_service = ShiftAssignment.objects.filter(
            staff=staff,
            shift__care_unit__service_id=service_id,
        ).count()

        if recent_shifts_in_service < min_shifts_required:
            return PENALTY_NEW_SERVICE_WITHOUT_ADAPTATION

    return 0.0


def evaluate_continuity_of_care(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    M-07: Pénalité si l'affectation rompt la continuité de soins
    (ex: ne pas affecter le même soignant aux mêmes patients/postes sur jours consécutifs).

    Args:
        staff: Le soignant à affecter
        shift: Le shift proposé
        context: Contexte optionnel

    Returns:
        Pénalité normalisée (0 si continuité respectée)
    """
    if not _get_patient_group_key(shift):
        return 0.0

    previous_assignment = _get_previous_day_assignment(staff, shift)

    if previous_assignment is None:
        return PENALTY_LACK_OF_CONTINUITY * 0.3

    return 0.0


def calculate_total_penalty(staff: Staff, shift: Shift, context: dict = None) -> float:
    """
    Calcule la pénalité totale pour une affectation candidate.

    Returns:
        Tuple (total, breakdown_dict)
    """
    from dataclasses import dataclass

    @dataclass
    class PenaltyBreakdown:
        consecutive_nights: float = 0.0
        preference_violation: float = 0.0
        workload_imbalance: float = 0.0
        service_change: float = 0.0
        weekend_ratio: float = 0.0
        new_service_without_adaptation: float = 0.0
        lack_of_continuity: float = 0.0

    breakdown = PenaltyBreakdown()
    breakdown.consecutive_nights = evaluate_consecutive_nights(staff, shift, context)
    breakdown.preference_violation = evaluate_preference_violation(staff, shift, context)
    breakdown.workload_imbalance = evaluate_workload_imbalance(staff, shift, context)
    breakdown.service_change = evaluate_service_change(staff, shift, context)
    breakdown.weekend_ratio = evaluate_weekend_ratio(staff, shift, context)
    breakdown.new_service_without_adaptation = evaluate_new_service_adaptation(staff, shift, context)
    breakdown.lack_of_continuity = evaluate_continuity_of_care(staff, shift, context)

    total = (
        breakdown.consecutive_nights +
        breakdown.preference_violation +
        breakdown.workload_imbalance +
        breakdown.service_change +
        breakdown.weekend_ratio +
        breakdown.new_service_without_adaptation +
        breakdown.lack_of_continuity
    )

    return total, {
        'consecutive_nights': breakdown.consecutive_nights,
        'preference_violation': breakdown.preference_violation,
        'workload_imbalance': breakdown.workload_imbalance,
        'service_change': breakdown.service_change,
        'weekend_ratio': breakdown.weekend_ratio,
        'new_service_without_adaptation': breakdown.new_service_without_adaptation,
        'lack_of_continuity': breakdown.lack_of_continuity,
    }
