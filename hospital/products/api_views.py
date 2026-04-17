from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Absence, Shift, ShiftAssignment


@require_GET
def shifts_list(request):
    shifts = (
        Shift.objects.select_related("care_unit", "shift_type")
        .prefetch_related("assignments")
        .order_by("-start_datetime")[:200]
    )
    payload = [
        {
            "id": shift.id,
            "title": f"{shift.care_unit} - {shift.shift_type}",
            "start": shift.start_datetime.isoformat(),
            "end": shift.end_datetime.isoformat(),
            "staffCount": shift.assignments.count(),
        }
        for shift in shifts
    ]
    return JsonResponse(payload, safe=False)


@require_GET
def assignments_list(request):
    assignments = ShiftAssignment.objects.order_by("-assigned_at")[:500]
    payload = [
        {"id": a.id, "shiftId": a.shift_id, "staffId": a.staff_id} for a in assignments
    ]
    return JsonResponse(payload, safe=False)


@require_GET
def absences_list(request):
    absences = Absence.objects.select_related("absence_type").order_by("-start_date")[
        :500
    ]
    payload = [
        {
            "id": a.id,
            "staffId": a.staff_id,
            "start": a.start_date.isoformat(),
            "end": a.expected_end_date.isoformat(),
            "reason": a.absence_type.name,
        }
        for a in absences
    ]
    return JsonResponse(payload, safe=False)
