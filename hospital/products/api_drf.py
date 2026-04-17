from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Absence, Shift, ShiftAssignment, Staff
from .services import _run_all_hard_constraints, create_assignment


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(
        request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if not user:
        return Response({"detail": "Invalid credentials."}, status=400)

    try:
        staff = Staff.objects.get(user=user, is_active=True)
    except Staff.DoesNotExist:
        return Response(
            {"detail": "No active staff profile linked to this user."}, status=403
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "staff": {"id": staff.id, "fullName": str(staff), "email": staff.email},
        }
    )


@api_view(["GET"])
def me_view(request):
    staff = Staff.objects.get(user=request.user)
    return Response({"id": staff.id, "fullName": str(staff), "email": staff.email})


@dataclass(frozen=True)
class EligibilityResult:
    ok: bool
    errors: list[str]


def check_shift_eligibility(staff: Staff, shift: Shift) -> EligibilityResult:
    try:
        _run_all_hard_constraints(staff, shift)
        return EligibilityResult(ok=True, errors=[])
    except ValidationError as exc:
        return EligibilityResult(ok=False, errors=list(getattr(exc, "messages", [])))


@api_view(["GET"])
def shifts_view(request):
    """
    Query params:
      - include_ineligible=1 : include ineligible shifts (with eligible=false)
    """
    include_ineligible = request.query_params.get("include_ineligible") == "1"

    staff = Staff.objects.get(user=request.user, is_active=True)
    shifts = (
        Shift.objects.select_related("care_unit__service", "shift_type")
        .prefetch_related("assignments")
        .order_by("start_datetime")[:400]
    )

    payload: list[dict[str, Any]] = []
    for shift in shifts:
        eligibility = check_shift_eligibility(staff, shift)
        if not include_ineligible and not eligibility.ok:
            continue
        payload.append(
            {
                "id": shift.id,
                "title": f"{shift.care_unit} - {shift.shift_type}",
                "start": shift.start_datetime.isoformat(),
                "end": shift.end_datetime.isoformat(),
                "staffCount": shift.assignments.count(),
                "eligible": eligibility.ok,
                "eligibilityErrors": eligibility.errors,
            }
        )

    return Response(payload)


class AssignmentCreateSerializer(serializers.Serializer):
    shift_id = serializers.IntegerField()

    def validate_shift_id(self, value):
        try:
            return Shift.objects.select_related("shift_type", "care_unit__service").get(
                pk=value
            )
        except Shift.DoesNotExist:
            raise serializers.ValidationError("Shift not found.")


@api_view(["GET", "POST"])
def my_assignments_view(request):
    staff = Staff.objects.get(user=request.user, is_active=True)

    if request.method == "GET":
        assignments = (
            ShiftAssignment.objects.select_related(
                "shift__shift_type", "shift__care_unit__service"
            )
            .filter(staff=staff)
            .order_by("-assigned_at")[:500]
        )
        return Response(
            [
                {
                    "id": a.id,
                    "shiftId": a.shift_id,
                    "staffId": a.staff_id,
                    "assignedAt": a.assigned_at.isoformat(),
                }
                for a in assignments
            ]
        )

    serializer = AssignmentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    shift: Shift = serializer.validated_data["shift_id"]

    try:
        assignment = create_assignment(staff=staff, shift=shift)
    except ValidationError as exc:
        return Response({"errors": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "id": assignment.id,
            "shiftId": assignment.shift_id,
            "staffId": assignment.staff_id,
            "assignedAt": assignment.assigned_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def my_absences_view(request):
    staff = Staff.objects.get(user=request.user, is_active=True)
    absences = (
        Absence.objects.select_related("absence_type")
        .filter(staff=staff)
        .order_by("-start_date")[:500]
    )
    return Response(
        [
            {
                "id": a.id,
                "staffId": a.staff_id,
                "start": a.start_date.isoformat(),
                "end": a.expected_end_date.isoformat(),
                "reason": a.absence_type.name,
            }
            for a in absences
        ]
    )
