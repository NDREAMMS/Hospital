"""
Hospital Staffing — Moteur de génération de planning
=====================================================
Implémente un Recuit Simulé (Simulated Annealing) pour l'optimisation.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict, Set
import random
import math
from copy import deepcopy

from django.db.models import Q

from .models import (
    Staff, Shift, ShiftAssignment, Rule, Service,
)
from .validators import (
    check_no_overlap, check_certifications, check_night_shift_rest,
    check_contract_allows_shift, check_no_absence, check_weekly_hours_quota,
    check_hard_preferences, check_maximum_staffing_on_create,
)
from .soft_validators import calculate_total_penalty


class SimulatedAnnealing:
    """
    Implémentation du Recuit Simulé pour l'optimisation du planning hospitalier.
    
    Paramètres:
        initial_temp: Température initiale (typiquement 1000-5000)
        final_temp: Température finale (typiquement 0.1-1)
        cooling_rate: Taux de refroidissement (0.95-0.999)
        max_iter_per_temp: Itérations par palier de température
        max_no_improve: Arrêt après N paliers sans amélioration
    """
    
    def __init__(
        self,
        initial_temp: float = 2000.0,
        final_temp: float = 0.5,
        cooling_rate: float = 0.997,
        max_iter_per_temp: int = 50,
        max_no_improve: int = 30,
    ):
        self.initial_temp = initial_temp
        self.final_temp = final_temp
        self.cooling_rate = cooling_rate
        self.max_iter_per_temp = max_iter_per_temp
        self.max_no_improve = max_no_improve
        
    def acceptance_probability(self, delta_e: float, temperature: float) -> float:
        """Calcule la probabilité d'accepter une solution worse."""
        if delta_e < 0:
            return 1.0
        return math.exp(-delta_e / temperature)
    
    def run(
        self,
        initial_solution: Dict[int, List[int]],  # shift_id -> list of staff_id
        cost_function,
        neighborhood_function,
        is_valid_function,
        get_staff_context_function,
        progress_callback=None,
    ) -> Tuple[Dict[int, List[int]], float, dict]:
        """
        Exécute le recuit simulé.
        
        Args:
            initial_solution: Solution initiale {shift_id: [staff_ids]}
            cost_function: Fonction de coût à minimiser
            neighborhood_function: Génère un voisin
            is_valid_function: Vérifie les contraintes dures
            get_staff_context_function: Contexte pour évaluation
            
        Returns:
            (best_solution, best_cost, stats)
        """
        current_solution = deepcopy(initial_solution)
        current_cost = cost_function(current_solution, get_staff_context_function)
        
        best_solution = deepcopy(current_solution)
        best_cost = current_cost
        
        temperature = self.initial_temp
        iteration = 0
        no_improve_count = 0
        
        stats = {
            'iterations': 0,
            'accepted': 0,
            'rejected': 0,
            'improved': 0,
            'temperature_history': [],
            'cost_history': [],
        }
        
        while temperature > self.final_temp and no_improve_count < self.max_no_improve:
            for _ in range(self.max_iter_per_temp):
                iteration += 1
                stats['iterations'] = iteration
                
                neighbor = neighborhood_function(current_solution)
                
                if not is_valid_function(neighbor):
                    stats['rejected'] += 1
                    continue
                
                neighbor_cost = cost_function(neighbor, get_staff_context_function)
                delta_e = neighbor_cost - current_cost
                
                if self.acceptance_probability(delta_e, temperature) > random.random():
                    current_solution = neighbor
                    current_cost = neighbor_cost
                    stats['accepted'] += 1
                    
                    if current_cost < best_cost:
                        best_solution = deepcopy(current_solution)
                        best_cost = current_cost
                        stats['improved'] += 1
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                
                if progress_callback and iteration % 100 == 0:
                    progress_callback({
                        'iteration': iteration,
                        'temperature': temperature,
                        'current_cost': current_cost,
                        'best_cost': best_cost,
                    })
            
            stats['temperature_history'].append(temperature)
            stats['cost_history'].append(best_cost)
            
            temperature *= self.cooling_rate
            temperature = max(temperature, self.final_temp)
        
        stats['final_cost'] = best_cost
        stats['final_temperature'] = temperature
        
        return best_solution, best_cost, stats


@dataclass
class PenaltyBreakdown:
    consecutive_nights: float = 0.0
    preference_violation: float = 0.0
    workload_imbalance: float = 0.0
    service_change: float = 0.0
    weekend_ratio: float = 0.0
    new_service_without_adaptation: float = 0.0
    lack_of_continuity: float = 0.0

    def total(self) -> float:
        return (
            self.consecutive_nights + self.preference_violation +
            self.workload_imbalance + self.service_change +
            self.weekend_ratio + self.new_service_without_adaptation +
            self.lack_of_continuity
        )


@dataclass
class CandidateAssignment:
    staff: Staff
    shift: Shift
    penalty: float = 0.0


@dataclass
class GenerationResult:
    success: bool
    assignments: list
    unassigned_shifts: list
    score: float
    penalty_breakdown: PenaltyBreakdown
    iterations: int = 0
    message: str = ""


class PlanningGenerator:
    DEFAULT_MAX_CONSECUTIVE_NIGHTS = 3

    def __init__(self, period_start: date, period_end: date, service_ids: list = None):
        self.period_start = period_start
        self.period_end = period_end
        self.service_ids = service_ids or []
        self._staff_cache = list(Staff.objects.filter(is_active=True).select_related())
        self._shifts_cache = None
        self._shifts_cache_dict = {}
        self._staff_cache_dict = {}

    def _get_shifts(self) -> list:
        if self._shifts_cache is not None:
            return self._shifts_cache
        
        qs = Shift.objects.filter(
            start_datetime__date__gte=self.period_start,
            start_datetime__date__lte=self.period_end,
        ).select_related('care_unit__service', 'shift_type')

        if self.service_ids:
            qs = qs.filter(care_unit__service_id__in=self.service_ids)

        self._shifts_cache = list(qs.order_by('start_datetime'))
        return self._shifts_cache

    def _validate_hard_constraints(self, staff: Staff, shift: Shift) -> bool:
        try:
            check_no_absence(staff, shift)
            check_contract_allows_shift(staff, shift)
            check_no_overlap(staff, shift)
            check_certifications(staff, shift)
            check_night_shift_rest(staff, shift)
            check_weekly_hours_quota(staff, shift)
            check_hard_preferences(staff, shift)
            check_maximum_staffing_on_create(shift)
            return True
        except Exception:
            return False

    def _get_staff_context(self, staff: Staff, shift: Shift) -> dict:
        from datetime import timedelta
        shift_date = shift.start_datetime.date()
        monday = shift_date - timedelta(days=shift_date.weekday())
        sunday = monday + timedelta(days=6)

        week_assignments = list(
            ShiftAssignment.objects.filter(
                staff=staff,
                shift__start_datetime__date__gte=monday,
                shift__start_datetime__date__lte=sunday,
            ).select_related('shift__care_unit__service')
        )

        service_ids = list(
            Staff.objects.filter(
                is_active=True,
                service_assignments__service_id=shift.care_unit.service_id,
            ).values_list('id', flat=True)
        )

        all_week_assignments = list(
            ShiftAssignment.objects.filter(
                staff_id__in=service_ids,
                shift__start_datetime__date__gte=monday,
                shift__start_datetime__date__lte=sunday,
            ).select_related('shift__shift_type')
        )

        return {
            'week_assignments': week_assignments,
            'weekend_days_worked': sum(1 for a in week_assignments if a.shift.start_datetime.weekday() >= 5),
            'services_this_week': {a.shift.care_unit.service_id for a in week_assignments},
            'consecutive_nights': self._count_consecutive_nights(staff, shift),
            'all_week_assignments': all_week_assignments,
            'shift_date': shift_date,
        }

    def _count_consecutive_nights(self, staff: Staff, shift: Shift) -> int:
        if not ("nuit" in shift.shift_type.name.lower() or shift.start_datetime.hour >= 21):
            return 0

        from datetime import timedelta
        shift_date = shift.start_datetime.date()
        consecutive = 1
        check_date = shift_date - timedelta(days=1)

        while True:
            night_shift = ShiftAssignment.objects.filter(
                staff=staff,
                shift__start_datetime__date=check_date,
            ).filter(
                Q(shift__shift_type__name__icontains="nuit") |
                Q(shift__start_datetime__hour__gte=21) |
                Q(shift__start_datetime__hour__lt=6)
            ).exists()

            if night_shift:
                consecutive += 1
                check_date -= timedelta(days=1)
            else:
                break

        return consecutive

    def _evaluate_penalty(self, staff: Staff, shift: Shift) -> float:
        context = self._get_staff_context(staff, shift)
        penalty, _ = calculate_total_penalty(staff, shift, context)
        return penalty

    def generate_greedy(self) -> tuple:
        shifts = self._get_shifts()
        assignments = []
        unassigned = []

        for shift in shifts:
            current_count = ShiftAssignment.objects.filter(shift=shift).count()
            needed = shift.min_staff - current_count

            if needed <= 0:
                continue

            candidates = []
            for staff in self._staff_cache:
                if self._validate_hard_constraints(staff, shift):
                    penalty = self._evaluate_penalty(staff, shift)
                    candidates.append(CandidateAssignment(staff=staff, shift=shift, penalty=penalty))

            candidates.sort(key=lambda c: c.penalty)

            for i in range(min(needed, len(candidates))):
                assignments.append(candidates[i])

            if len(candidates) < needed:
                unassigned.append({
                    'shift_id': shift.id,
                    'shift': str(shift),
                    'needed': needed - len(candidates),
                    'available': len(candidates),
                })

        return assignments, unassigned

    def _calculate_total_penalty(self, assignments: List[CandidateAssignment]) -> tuple:
        breakdown = PenaltyBreakdown()
        staff_contexts = {}

        for candidate in assignments:
            sid = candidate.staff.id
            if sid not in staff_contexts:
                staff_contexts[sid] = self._get_staff_context(candidate.staff, candidate.shift)

            context = staff_contexts[sid]
            _, detail = calculate_total_penalty(candidate.staff, candidate.shift, context)

            breakdown.consecutive_nights += detail.get('consecutive_nights', 0)
            breakdown.preference_violation += detail.get('preference_violation', 0)
            breakdown.workload_imbalance += detail.get('workload_imbalance', 0)
            breakdown.service_change += detail.get('service_change', 0)
            breakdown.weekend_ratio += detail.get('weekend_ratio', 0)
            breakdown.new_service_without_adaptation += detail.get('new_service_without_adaptation', 0)
            breakdown.lack_of_continuity += detail.get('lack_of_continuity', 0)

        return breakdown.total(), breakdown

    def generate(self, use_optimization: bool = False, max_iterations: int = 100) -> GenerationResult:
        greedy_assignments, unassigned = self.generate_greedy()

        if use_optimization and greedy_assignments:
            optimized_solution, opt_score, opt_breakdown, sa_stats = self._optimize_with_sa(
                greedy_assignments,
                max_iterations=max_iterations,
            )
            
            result_assignments = []
            for shift_id, staff_ids in optimized_solution.items():
                shift = self._shifts_cache_dict.get(shift_id)
                if shift:
                    for staff_id in staff_ids:
                        staff = self._staff_cache_dict.get(staff_id)
                        if staff:
                            try:
                                assignment = ShiftAssignment.objects.create(
                                    staff=staff,
                                    shift=shift,
                                )
                                result_assignments.append({
                                    'id': assignment.id,
                                    'staff_id': assignment.staff_id,
                                    'staff_name': str(staff),
                                    'shift_id': assignment.shift_id,
                                    'shift': str(shift),
                                    'start': shift.start_datetime.isoformat(),
                                    'end': shift.end_datetime.isoformat(),
                                    'service': shift.care_unit.service.name,
                                    'unit': shift.care_unit.name,
                                    'shift_type': shift.shift_type.name,
                                })
                            except Exception:
                                pass
            
            message = (
                f"Optimisé avec Recuit Simulé. "
                f"{len(result_assignments)} affectations, score: {opt_score:.2f} "
                f"({sa_stats['iterations']} itérations)"
            )
            
            return GenerationResult(
                success=True,
                assignments=result_assignments,
                unassigned_shifts=unassigned,
                score=opt_score,
                penalty_breakdown=opt_breakdown,
                iterations=sa_stats['iterations'],
                message=message,
            )

        result_assignments = []
        for candidate in greedy_assignments:
            try:
                assignment = ShiftAssignment.objects.create(
                    staff=candidate.staff,
                    shift=candidate.shift,
                )
                result_assignments.append({
                    'id': assignment.id,
                    'staff_id': assignment.staff_id,
                    'staff_name': str(candidate.staff),
                    'shift_id': assignment.shift_id,
                    'shift': str(candidate.shift),
                    'start': candidate.shift.start_datetime.isoformat(),
                    'end': candidate.shift.end_datetime.isoformat(),
                    'service': candidate.shift.care_unit.service.name,
                    'unit': candidate.shift.care_unit.name,
                    'shift_type': candidate.shift.shift_type.name,
                })
            except Exception:
                pass

        final_score, final_breakdown = self._calculate_total_penalty(greedy_assignments)

        return GenerationResult(
            success=True,
            assignments=result_assignments,
            unassigned_shifts=unassigned,
            score=final_score,
            penalty_breakdown=final_breakdown,
            iterations=0,
            message=f"Généré avec succès. {len(result_assignments)} affectations, {len(unassigned)} créneaux non pourvus."
        )
    
    def _optimize_with_sa(
        self,
        greedy_assignments: List[CandidateAssignment],
        max_iterations: int = 100,
    ) -> Tuple[Dict[int, List[int]], float, PenaltyBreakdown, dict]:
        """Optimise le planning avec le Recuit Simulé."""
        
        self._build_caches()
        
        initial_solution = {}
        for cand in greedy_assignments:
            shift_id = cand.shift.id
            if shift_id not in initial_solution:
                initial_solution[shift_id] = []
            initial_solution[shift_id].append(cand.staff.id)
        
        max_temp = 2000.0 if max_iterations >= 500 else 1000.0
        cooling = 0.998 if max_iterations >= 500 else 0.995
        iter_per_temp = max(20, max_iterations // 50)
        
        sa = SimulatedAnnealing(
            initial_temp=max_temp,
            final_temp=0.5,
            cooling_rate=cooling,
            max_iter_per_temp=iter_per_temp,
            max_no_improve=max(20, max_iterations // 10),
        )
        
        def cost_function(solution, context_fn):
            return self._calculate_solution_cost(solution, context_fn)
        
        def neighborhood_function(solution):
            return self._generate_neighbor(solution)
        
        def is_valid_function(solution):
            return self._is_valid_solution(solution)
        
        best_solution, best_cost, stats = sa.run(
            initial_solution,
            cost_function,
            neighborhood_function,
            is_valid_function,
            self._get_staff_context_for_solution,
        )
        
        final_breakdown = self._calculate_solution_breakdown(best_solution)
        
        return best_solution, best_cost, final_breakdown, stats
    
    def _build_caches(self):
        """Construit les dictionnaires de cache."""
        if self._shifts_cache is None:
            self._get_shifts()
        
        self._shifts_cache_dict = {s.id: s for s in self._shifts_cache}
        self._staff_cache_dict = {s.id: s for s in self._staff_cache}
    
    def _calculate_solution_cost(
        self,
        solution: Dict[int, List[int]],
        context_fn,
    ) -> float:
        """Calcule le coût total d'une solution."""
        total = 0.0
        context_cache = {}
        
        for shift_id, staff_ids in solution.items():
            shift = self._shifts_cache_dict.get(shift_id)
            if not shift:
                continue
                
            for staff_id in staff_ids:
                staff = self._staff_cache_dict.get(staff_id)
                if not staff:
                    continue
                
                if staff_id not in context_cache:
                    context_cache[staff_id] = context_fn(staff)
                
                context = context_cache[staff_id]
                penalty, _ = calculate_total_penalty(staff, shift, context)
                total += penalty
                
                context['week_assignments'] = context.get('week_assignments', []) + [
                    type('obj', (object,), {'shift': shift})()
                ]
        
        return total
    
    def _generate_neighbor(
        self,
        solution: Dict[int, List[int]],
    ) -> Dict[int, List[int]]:
        """Génère une solution voisine par échange."""
        new_solution = deepcopy(solution)
        
        shift_ids = list(new_solution.keys())
        if len(shift_ids) < 2:
            return new_solution
        
        num_swaps = random.randint(1, min(3, len(shift_ids) // 2 + 1))
        
        for _ in range(num_swaps):
            shift1_id = random.choice(shift_ids)
            shift2_id = random.choice([s for s in shift_ids if s != shift1_id])
            
            if not new_solution[shift1_id] or not new_solution[shift2_id]:
                continue
            
            staff1 = random.choice(new_solution[shift1_id])
            staff2 = random.choice(new_solution[shift2_id])
            
            if staff1 in new_solution[shift1_id]:
                new_solution[shift1_id].remove(staff1)
            if staff2 in new_solution[shift2_id]:
                new_solution[shift2_id].remove(staff2)
            
            new_solution[shift1_id].append(staff2)
            new_solution[shift2_id].append(staff1)
        
        return new_solution
    
    def _is_valid_solution(self, solution: Dict[int, List[int]]) -> bool:
        """Vérifie que la solution respecte les contraintes dures."""
        for shift_id, staff_ids in solution.items():
            shift = self._shifts_cache_dict.get(shift_id)
            if not shift:
                return False
            
            if len(staff_ids) > shift.max_staff:
                return False
            
            for staff_id in staff_ids:
                staff = self._staff_cache_dict.get(staff_id)
                if not staff:
                    return False
                
                if not self._validate_hard_constraints(staff, shift):
                    return False
        
        return True
    
    def _get_staff_context_for_solution(self, staff: Staff) -> dict:
        """Récupère le contexte pour un soignant."""
        return self._get_staff_context(staff, list(self._shifts_cache_dict.values())[0])
    
    def _calculate_solution_breakdown(
        self,
        solution: Dict[int, List[int]],
    ) -> PenaltyBreakdown:
        """Calcule la répartition des pénalités."""
        breakdown = PenaltyBreakdown()
        
        for shift_id, staff_ids in solution.items():
            shift = self._shifts_cache_dict.get(shift_id)
            if not shift:
                continue
            
            for staff_id in staff_ids:
                staff = self._staff_cache_dict.get(staff_id)
                if not staff:
                    continue
                
                context = self._get_staff_context(staff, shift)
                _, detail = calculate_total_penalty(staff, shift, context)
                
                breakdown.consecutive_nights += detail.get('consecutive_nights', 0)
                breakdown.preference_violation += detail.get('preference_violation', 0)
                breakdown.workload_imbalance += detail.get('workload_imbalance', 0)
                breakdown.service_change += detail.get('service_change', 0)
                breakdown.weekend_ratio += detail.get('weekend_ratio', 0)
                breakdown.new_service_without_adaptation += detail.get('new_service_without_adaptation', 0)
                breakdown.lack_of_continuity += detail.get('lack_of_continuity', 0)
        
        return breakdown


def generate_planning(
    period_start: date,
    period_end: date,
    service_ids: list = None,
    use_optimization: bool = True,
    max_iterations: int = 100,
) -> GenerationResult:
    generator = PlanningGenerator(period_start, period_end, service_ids)
    return generator.generate(use_optimization=use_optimization, max_iterations=max_iterations)
