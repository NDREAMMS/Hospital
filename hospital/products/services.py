"""
Hospital Staffing — Couche service
===================================
Orchestre les validateurs. Toute création / modification / suppression
d'affectation passe obligatoirement par ce module.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from typing import List, Tuple
from .models import Shift, ShiftAssignment, Staff
from .validators import (
    check_certifications,
    check_contract_allows_shift,
    check_hard_preferences,
    check_maximum_staffing_on_create,
    check_minimum_staffing_on_delete,
    check_night_shift_rest,
    check_no_absence,
    check_no_overlap,
    check_weekly_hours_quota,
)
from .soft_validators import (
    evaluate_consecutive_nights,
    evaluate_preference_violation,
    evaluate_workload_imbalance,
    evaluate_service_change,
    evaluate_weekend_ratio,
    evaluate_new_service_adaptation,
    evaluate_continuity_of_care,
)


def _run_all_hard_constraints(
    staff: Staff,
    shift: Shift,
    exclude_assignment_id: int = None,
):
    """
    Exécute les 8 contraintes dures dans un ordre optimisé
    (les checks les moins coûteux en base en premier).

    Toutes les violations sont collectées avant de lever l'exception
    pour offrir un retour exhaustif en une seule passe.
    """
    errors = []

    checks = [
        lambda: check_no_absence(staff, shift),                               # C-06 — 1 requête simple
        lambda: check_contract_allows_shift(staff, shift),                    # C-05 — 1 requête
        lambda: check_no_overlap(staff, shift, exclude_assignment_id),        # C-01 — 1 requête
        lambda: check_certifications(staff, shift),                           # C-02 — 2 requêtes
        lambda: check_night_shift_rest(staff, shift),                         # C-03 — 1 requête + Rule
        lambda: check_weekly_hours_quota(staff, shift, exclude_assignment_id),# C-07 — 1 requête
        lambda: check_hard_preferences(staff, shift),                         # C-08 — 1 requête
        lambda: check_maximum_staffing_on_create(shift),                      # C-04 max — 1 count
    ]

    for check in checks:
        try:
            check()
        except ValidationError as e:
            errors.extend(e.messages)

    if errors:
        raise ValidationError(errors)


@transaction.atomic
def create_assignment(staff: Staff, shift: Shift) -> ShiftAssignment:
    """
    Valide toutes les contraintes dures puis crée l'affectation.
    Lève ValidationError (avec la liste de tous les problèmes) si refus.
    """
    _run_all_hard_constraints(staff, shift)
    return ShiftAssignment.objects.create(staff=staff, shift=shift)


@transaction.atomic
def update_assignment(
    assignment: ShiftAssignment,
    new_shift: Shift = None,
    new_staff: Staff = None,
) -> ShiftAssignment:
    """
    Revalide toutes les contraintes sur les nouvelles valeurs,
    en excluant l'affectation actuelle du check de chevauchement et quota.
    """
    staff = new_staff or assignment.staff
    shift = new_shift or assignment.shift

    _run_all_hard_constraints(staff, shift, exclude_assignment_id=assignment.pk)

    assignment.staff = staff
    assignment.shift = shift
    assignment.save()
    return assignment


@transaction.atomic
def delete_assignment(assignment: ShiftAssignment) -> None:
    """
    Supprime l'affectation puis vérifie que le seuil de sécurité
    du shift est encore atteint. Si non, le rollback est automatique.
    """
    shift = assignment.shift
    assignment.delete()
    check_minimum_staffing_on_delete(shift)  # C-04 min — appelé APRÈS delete