"""
Hospital Staffing — Vues API pour la génération de planning
=============================================================
Phase 3: Endpoints pour le générateur de planning.
"""

from datetime import date, datetime
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Service
from .generator import generate_planning, PlanningGenerator


class PlanningGenerateSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    use_optimization = serializers.BooleanField(default=True)
    max_iterations = serializers.IntegerField(default=1000, min_value=1, max_value=10000)

    def validate(self, attrs):
        period_start = attrs.get('period_start')
        period_end = attrs.get('period_end')

        today = date.today()

        if period_end < period_start:
            raise serializers.ValidationError({
                'period_end': "La date de fin doit être postérieure à la date de début."
            })

        if (period_end - period_start).days > 31:
            raise serializers.ValidationError({
                'period_end': "La période ne peut pas dépasser 31 jours."
            })

        return attrs

    def validate_service_ids(self, value):
        if value:
            existing = Service.objects.filter(id__in=value).values_list('id', flat=True)
            missing = set(value) - set(existing)
            if missing:
                raise serializers.ValidationError(
                    f"Services introuvables: {list(missing)}"
                )
        return value


class PlanningGenerateView(APIView):
    """
    POST /api/plannings/generate/

    Génère un planning pour une période donnée.

    Corps de la requête:
    {
        "period_start": "2026-04-20",
        "period_end": "2026-04-26",
        "service_ids": [1, 2],  // optionnel
        "use_optimization": true,
        "max_iterations": 1000
    }

    Réponse:
    {
        "success": true,
        "assignments": [...],
        "unassigned_shifts": [...],
        "score": 150.5,
        "penalty_breakdown": {
            "consecutive_nights": 0,
            "preference_violation": 50,
            ...
        },
        "iterations": 750,
        "message": "..."
    }
    """

    def post(self, request):
        serializer = PlanningGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        period_start = serializer.validated_data['period_start']
        period_end = serializer.validated_data['period_end']
        service_ids = serializer.validated_data.get('service_ids', [])
        use_optimization = serializer.validated_data.get('use_optimization', True)
        max_iterations = serializer.validated_data.get('max_iterations', 1000)

        result = generate_planning(
            period_start=period_start,
            period_end=period_end,
            service_ids=service_ids if service_ids else None,
            use_optimization=use_optimization,
            max_iterations=max_iterations,
        )

        return Response({
            'success': result.success,
            'assignments': result.assignments,
            'unassigned_shifts': result.unassigned_shifts,
            'score': result.score,
            'penalty_breakdown': {
                'consecutive_nights': result.penalty_breakdown.consecutive_nights,
                'preference_violation': result.penalty_breakdown.preference_violation,
                'workload_imbalance': result.penalty_breakdown.workload_imbalance,
                'service_change': result.penalty_breakdown.service_change,
                'weekend_ratio': result.penalty_breakdown.weekend_ratio,
                'new_service_without_adaptation': result.penalty_breakdown.new_service_without_adaptation,
                'lack_of_continuity': result.penalty_breakdown.lack_of_continuity,
            },
            'iterations': result.iterations,
            'message': result.message,
        })


class PlanningPreviewSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )


class PlanningPreviewView(APIView):
    """
    POST /api/plannings/preview/

    Prévisualise les créneaux à couvrir sans générer le planning.
    Utile pour vérifier la disponibilité avant génération.

    Réponse:
    {
        "shifts_to_cover": [...],
        "total_shifts": 25,
        "already_covered": 15,
        "needs_coverage": 10,
        "services": [...]
    }
    """

    def post(self, request):
        serializer = PlanningPreviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        period_start = serializer.validated_data['period_start']
        period_end = serializer.validated_data['period_end']
        service_ids = serializer.validated_data.get('service_ids', [])

        from .models import Shift, ShiftAssignment

        qs = Shift.objects.filter(
            start_datetime__date__gte=period_start,
            start_datetime__date__lte=period_end,
        ).select_related('care_unit__service', 'shift_type')

        if service_ids:
            qs = qs.filter(care_unit__service_id__in=service_ids)

        shifts = list(qs.order_by('start_datetime'))

        covered = []
        needs_coverage = []
        all_shifts_info = []

        for shift in shifts:
            current = ShiftAssignment.objects.filter(shift=shift).count()
            info = {
                'id': shift.id,
                'service': shift.care_unit.service.name,
                'service_id': shift.care_unit.service_id,
                'unit': shift.care_unit.name,
                'shift_type': shift.shift_type.name,
                'start': shift.start_datetime.isoformat(),
                'end': shift.end_datetime.isoformat(),
                'current_staff': current,
                'min_staff': shift.min_staff,
                'max_staff': shift.max_staff,
                'status': 'covered' if current >= shift.min_staff else 'understaffed',
            }
            all_shifts_info.append(info)

            if current >= shift.min_staff:
                covered.append(info)
            else:
                needs_coverage.append(info)

        service_ids = list(qs.values_list('care_unit__service_id', flat=True).distinct())
        service_stats = []
        for sid in service_ids:
            service = Service.objects.get(pk=sid)
            service_shifts = [s for s in all_shifts_info if s['service_id'] == sid]
            total_needed = sum(s['min_staff'] for s in service_shifts)
            total_current = sum(s['current_staff'] for s in service_shifts)
            uncovered_shifts = [s for s in service_shifts if s['status'] == 'understaffed']
            service_stats.append({
                'id': sid,
                'name': service.name,
                'bed_capacity': service.bed_capacity,
                'total_shifts': len(service_shifts),
                'min_staff_needed': total_needed,
                'current_staff': total_current,
                'shortage': max(0, total_needed - total_current),
                'uncovered_shifts': len(uncovered_shifts),
            })

        services = list(
            qs.values_list('care_unit__service__name', flat=True).distinct()
        )

        return Response({
            'shifts_to_cover': needs_coverage,
            'all_shifts': all_shifts_info,
            'total_shifts': len(shifts),
            'already_covered': len(covered),
            'needs_coverage': len(needs_coverage),
            'services': services,
            'service_stats': service_stats,
        })


class PlanningValidateEditSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()


class PlanningValidateEditView(APIView):
    """
    POST /api/plannings/validate-edit/

    Valide une modification manuelle du planning contre les contraintes dures.
    Ne persiste pas l'affectation, juste la valide.

    Corps de la requête:
    {
        "staff_id": 5,
        "shift_id": 10
    }

    Réponse:
    {
        "valid": true/false,
        "violations": [...]
    }
    """

    def post(self, request):
        from django.core.exceptions import ValidationError
        from .services import _run_all_hard_constraints
        from .models import Staff, Shift

        serializer = PlanningValidateEditSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            staff = Staff.objects.get(pk=serializer.validated_data['staff_id'], is_active=True)
        except Staff.DoesNotExist:
            return Response(
                {'valid': False, 'violations': ['Soignant introuvable ou inactif.']},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            shift = Shift.objects.select_related(
                'shift_type', 'care_unit__service'
            ).get(pk=serializer.validated_data['shift_id'])
        except Shift.DoesNotExist:
            return Response(
                {'valid': False, 'violations': ['Créneau introuvable.']},
                status=status.HTTP_404_NOT_FOUND
            )

        violations = []
        try:
            _run_all_hard_constraints(staff, shift)
        except ValidationError as e:
            violations = list(getattr(e, 'messages', [str(e)]))

        return Response({
            'valid': len(violations) == 0,
            'violations': violations,
        })


class PlanningScoreView(APIView):
    """
    GET /api/plannings/score/

    Calcule le score global du planning actuel pour une période donnée.

    Query params:
    - period_start: date (required)
    - period_end: date (required)
    - service_ids: comma-separated integers (optional)

    Réponse:
    {
        "score": 150.5,
        "penalty_breakdown": {...},
        "total_assignments": 45,
        "unassigned_shifts": [...]
    }
    """

    def get(self, request):
        from datetime import datetime as dt

        period_start_str = request.query_params.get('period_start')
        period_end_str = request.query_params.get('period_end')
        service_ids_str = request.query_params.get('service_ids', '')

        if not period_start_str or not period_end_str:
            return Response(
                {'error': 'period_start et period_end sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            period_start = dt.strptime(period_start_str, '%Y-%m-%d').date()
            period_end = dt.strptime(period_end_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_ids = []
        if service_ids_str:
            try:
                service_ids = [int(x) for x in service_ids_str.split(',') if x]
            except ValueError:
                return Response(
                    {'error': 'Format invalide pour service_ids.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        generator = PlanningGenerator(period_start, period_end, service_ids if service_ids else None)

        from .models import ShiftAssignment
        qs = ShiftAssignment.objects.filter(
            shift__start_datetime__date__gte=period_start,
            shift__start_datetime__date__lte=period_end,
        ).select_related('shift__care_unit__service', 'shift__shift_type', 'staff')

        if service_ids:
            qs = qs.filter(shift__care_unit__service_id__in=service_ids)

        assignments = list(qs)

        from .soft_validators import calculate_total_penalty, PenaltyBreakdown
        total_penalty = 0.0
        breakdown = PenaltyBreakdown()

        staff_contexts = {}
        for assignment in assignments:
            sid = assignment.staff_id
            if sid not in staff_contexts:
                context = generator._get_staff_context(assignment.staff, assignment.shift)
                staff_contexts[sid] = context
            else:
                context = staff_contexts[sid]

            penalty, detail = calculate_total_penalty(assignment.staff, assignment.shift, context)
            total_penalty += penalty

        from .models import Shift
        shift_qs = Shift.objects.filter(
            start_datetime__date__gte=period_start,
            start_datetime__date__lte=period_end,
        )
        if service_ids:
            shift_qs = shift_qs.filter(care_unit__service_id__in=service_ids)

        unassigned = []
        for shift in shift_qs:
            current = ShiftAssignment.objects.filter(shift=shift).count()
            if current < shift.min_staff:
                unassigned.append({
                    'shift_id': shift.id,
                    'shift': str(shift),
                    'current': current,
                    'needed': shift.min_staff - current,
                })

        return Response({
            'score': total_penalty,
            'penalty_breakdown': {
                'consecutive_nights': breakdown.consecutive_nights,
                'preference_violation': breakdown.preference_violation,
                'workload_imbalance': breakdown.workload_imbalance,
                'service_change': breakdown.service_change,
                'weekend_ratio': breakdown.weekend_ratio,
                'new_service_without_adaptation': breakdown.new_service_without_adaptation,
                'lack_of_continuity': breakdown.lack_of_continuity,
            },
            'total_assignments': len(assignments),
            'unassigned_shifts': unassigned,
        })


class PenaltyWeightsSerializer(serializers.Serializer):
    rule_type = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField()


class PenaltyWeightsView(APIView):
    """
    GET /api/plannings/penalty-weights/

    Retourne les poids actuels des pénalités pour les contraintes molles.
    """

    def get(self, request):
        from .models import Rule

        weight_rules = [
            'penalty_consecutive_nights',
            'penalty_preference_violation',
            'penalty_workload_imbalance',
            'penalty_service_change',
            'penalty_weekend_ratio',
            'penalty_new_service_without_adaptation',
            'penalty_lack_of_continuity',
        ]

        weights = []
        for rule_type in weight_rules:
            try:
                rule = Rule.objects.get(rule_type=rule_type)
                weights.append({
                    'rule_type': rule_type,
                    'value': float(rule.value),
                    'description': rule.description or rule.name,
                })
            except Rule.DoesNotExist:
                display_name = rule_type.replace('penalty_', '').replace('_', ' ').title()
                weights.append({
                    'rule_type': rule_type,
                    'value': 0.0,
                    'description': f'Poids pour {display_name}',
                })

        return Response({'weights': weights})

    def patch(self, request):
        from .models import Rule

        rule_type = request.data.get('rule_type')
        value = request.data.get('value')

        if not rule_type or value is None:
            return Response(
                {'error': 'rule_type et value sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rule = Rule.objects.get(rule_type=rule_type)
            rule.value = float(value)
            rule.save()
        except Rule.DoesNotExist:
            Rule.objects.create(
                name=f'Penalty: {rule_type}',
                rule_type=rule_type,
                value=float(value),
                unit='points',
                description=request.data.get('description', ''),
            )

        return Response({'success': True, 'rule_type': rule_type, 'value': float(value)})
