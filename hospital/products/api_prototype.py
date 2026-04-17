from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Absence,
    Role,
    Service,
    Preference,
    Rule,
    Certification,
    Contract,
    ContractType,
    Shift,
    ShiftRequiredCertification,
    ShiftAssignment,
    Staff,
    StaffCertification,
    StaffRole,
    StaffServiceAssignment,
)
from .services import _run_all_hard_constraints, create_assignment


def _staff_role_name(staff: Staff) -> str | None:
    sr = StaffRole.objects.select_related("role").filter(staff=staff).first()
    return sr.role.name if sr else None


def _staff_service_name(staff: Staff) -> str | None:
    sa = (
        StaffServiceAssignment.objects.select_related("service")
        .filter(staff=staff, end_date__isnull=True)
        .order_by("-start_date")
        .first()
    )
    if not sa:
        sa = (
            StaffServiceAssignment.objects.select_related("service")
            .filter(staff=staff)
            .order_by("-start_date")
            .first()
        )
    return sa.service.name if sa else None


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name"]


class StaffReadSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    certificationCount = serializers.SerializerMethodField()
    activeContract = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id",
            "fullName",
            "email",
            "phone",
            "is_active",
            "role",
            "service",
            "status",
            "certificationCount",
            "activeContract",
        ]

    def get_fullName(self, obj: Staff) -> str:
        return str(obj)

    def get_role(self, obj: Staff) -> str | None:
        return _staff_role_name(obj)

    def get_service(self, obj: Staff) -> str | None:
        return _staff_service_name(obj)

    def get_status(self, obj: Staff) -> str:
        return "Actif" if obj.is_active else "Inactif"

    def get_certificationCount(self, obj: Staff) -> int:
        today = timezone.now().date()
        return (
            StaffCertification.objects.filter(
                staff=obj,
                obtained_date__lte=today,
            )
            .filter(Q(expiration_date__isnull=True) | Q(expiration_date__gte=today))
            .count()
        )

    def get_activeContract(self, obj: Staff) -> str | None:
        today = timezone.now().date()
        active = (
            Contract.objects.filter(staff=obj, start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .select_related("contract_type")
            .order_by("-start_date")
            .first()
        )
        return active.contract_type.name if active else None


class StaffWriteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    is_active = serializers.BooleanField(default=True, required=False)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    service_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        staff_id = self.context.get("staff_id")
        qs = Staff.objects.filter(email=value)
        if staff_id:
            qs = qs.exclude(pk=staff_id)
        if qs.exists():
            raise serializers.ValidationError("Cet email existe déjà.")
        return value

    def validate_role_id(self, value):
        if value is None:
            return None
        try:
            return Role.objects.get(pk=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError("Role introuvable.")

    def validate_service_id(self, value):
        if value is None:
            return None
        try:
            return Service.objects.get(pk=value)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service introuvable.")


class StaffListView(APIView):
    def get(self, request):
        staff = Staff.objects.all().order_by("last_name", "first_name")
        return Response(StaffReadSerializer(staff, many=True).data)

    def post(self, request):
        serializer = StaffWriteSerializer(data=request.data, context={"staff_id": None})
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                s = Staff.objects.create(
                    first_name=serializer.validated_data["first_name"],
                    last_name=serializer.validated_data["last_name"],
                    email=serializer.validated_data["email"],
                    phone=serializer.validated_data.get("phone", ""),
                    is_active=serializer.validated_data.get("is_active", True),
                )

                role: Role | None = serializer.validated_data.get("role_id")
                if role:
                    StaffRole.objects.create(staff=s, role=role)

                service: Service | None = serializer.validated_data.get("service_id")
                if service:
                    StaffServiceAssignment.objects.create(
                        staff=s, service=service, start_date=timezone.now().date()
                    )

                # Prototype convenience: make sure a staff member can be assigned.
                # Constraints require an active contract at the shift date.
                default_ct, _ = ContractType.objects.get_or_create(
                    name="CDI",
                    defaults={
                        "max_hours_per_week": 40,
                        "leave_days_per_year": 25,
                        "night_shift_allowed": True,
                    },
                )
                Contract.objects.get_or_create(
                    staff=s,
                    contract_type=default_ct,
                    start_date=timezone.now().date(),
                    defaults={"workload_percent": 100},
                )
        except IntegrityError:
            return Response({"email": ["Cet email existe déjà."]}, status=400)

        return Response(StaffReadSerializer(s).data, status=status.HTTP_201_CREATED)


class StaffDetailView(APIView):
    def patch(self, request, pk: int):
        try:
            staff = Staff.objects.get(pk=pk)
        except Staff.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=404)

        serializer = StaffWriteSerializer(
            data=request.data, partial=True, context={"staff_id": staff.pk}
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                for field in ["first_name", "last_name", "email", "phone", "is_active"]:
                    if field in serializer.validated_data:
                        setattr(staff, field, serializer.validated_data[field])
                staff.save()

                if "role_id" in serializer.validated_data:
                    role = serializer.validated_data["role_id"]
                    StaffRole.objects.filter(staff=staff).delete()
                    if role:
                        StaffRole.objects.create(staff=staff, role=role)

                if "service_id" in serializer.validated_data:
                    service = serializer.validated_data["service_id"]
                    StaffServiceAssignment.objects.filter(
                        staff=staff, end_date__isnull=True
                    ).update(end_date=timezone.now().date())
                    if service:
                        StaffServiceAssignment.objects.create(
                            staff=staff, service=service, start_date=timezone.now().date()
                        )
        except IntegrityError:
            return Response({"email": ["Cet email existe déjà."]}, status=400)

        return Response(StaffReadSerializer(staff).data)

    def delete(self, request, pk: int):
        try:
            staff = Staff.objects.get(pk=pk)
        except Staff.DoesNotExist:
            return Response(status=204)

        staff.delete()
        return Response(status=204)


class ShiftReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    service = serializers.CharField()
    unit = serializers.CharField()
    shiftType = serializers.CharField()
    start = serializers.CharField()
    end = serializers.CharField()
    status = serializers.CharField()
    assignmentsCount = serializers.IntegerField()
    minStaff = serializers.IntegerField()
    maxStaff = serializers.IntegerField()
    assignedStaff = serializers.ListField()
    requiredCertifications = serializers.ListField()


class ShiftListView(APIView):
    def get(self, request):
        qs = (
            Shift.objects.select_related("care_unit__service", "shift_type", "care_unit")
            .prefetch_related("assignments__staff", "required_certifications__certification")
            .order_by("start_datetime")[:500]
        )
        payload: list[dict[str, Any]] = []
        for sh in qs:
            assignments_count = sh.assignments.count()
            available = assignments_count < sh.max_staff
            assigned_staff = [
                {
                    "id": assignment.staff_id,
                    "fullName": str(assignment.staff),
                    "role": _staff_role_name(assignment.staff),
                }
                for assignment in sh.assignments.all()
            ]
            payload.append(
                {
                    "id": sh.id,
                    "title": f"{sh.care_unit.service.name} / {sh.care_unit.name} - {sh.shift_type.name}",
                    "service": sh.care_unit.service.name,
                    "unit": sh.care_unit.name,
                    "shiftType": sh.shift_type.name,
                    "start": sh.start_datetime.isoformat(),
                    "end": sh.end_datetime.isoformat(),
                    "status": "Disponible" if available else "Affecte",
                    "assignmentsCount": assignments_count,
                    "minStaff": sh.min_staff,
                    "maxStaff": sh.max_staff,
                    "assignedStaff": assigned_staff,
                    "requiredCertifications": [
                        row.certification.name for row in sh.required_certifications.all()
                    ],
                }
            )
        return Response(payload)
class AssignmentCreateSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()

    def validate_staff_id(self, value):
        try:
            return Staff.objects.get(pk=value, is_active=True)
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Soignant introuvable ou inactif.")

    def validate_shift_id(self, value):
        try:
            return Shift.objects.select_related("shift_type", "care_unit__service").get(
                pk=value
            )
        except Shift.DoesNotExist:
            raise serializers.ValidationError("Créneau introuvable.")


class AssignmentCreateView(APIView):
    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        staff = serializer.validated_data["staff_id"]
        shift = serializer.validated_data["shift_id"]

        try:
            assignment = create_assignment(staff=staff, shift=shift)
        except Exception as exc:
            # create_assignment raises django.core.exceptions.ValidationError (messages)
            messages = getattr(exc, "messages", None)
            if messages:
                return Response({"detail": "\n".join(messages)}, status=400)
            raise

        return Response(
            {
                "id": assignment.id,
                "staffId": assignment.staff_id,
                "shiftId": assignment.shift_id,
                "assignedAt": assignment.assigned_at.isoformat(),
            },
            status=201,
        )


class AssignmentCheckSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()

    def validate_staff_id(self, value):
        try:
            return Staff.objects.get(pk=value, is_active=True)
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Soignant introuvable ou inactif.")

    def validate_shift_id(self, value):
        try:
            return Shift.objects.select_related("shift_type", "care_unit__service").get(
                pk=value
            )
        except Shift.DoesNotExist:
            raise serializers.ValidationError("Créneau introuvable.")


class AssignmentCheckView(APIView):
    def post(self, request):
        serializer = AssignmentCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        staff: Staff = serializer.validated_data["staff_id"]
        shift: Shift = serializer.validated_data["shift_id"]
        shift_date = shift.start_datetime.date()

        reasons: list[str] = []
        try:
            _run_all_hard_constraints(staff, shift)
        except ValidationError as exc:
            reasons = list(getattr(exc, "messages", []))

        required_rows = ShiftRequiredCertification.objects.filter(shift=shift).select_related(
            "certification"
        )
        required = [row.certification.name for row in required_rows]
        required_ids = [row.certification_id for row in required_rows]

        valid_rows = StaffCertification.objects.filter(
            staff=staff,
            certification_id__in=required_ids,
            obtained_date__lte=shift_date,
        ).filter(Q(expiration_date__isnull=True) | Q(expiration_date__gte=shift_date))
        valid_ids = set(valid_rows.values_list("certification_id", flat=True))
        missing_ids = set(required_ids) - valid_ids
        expired_rows = StaffCertification.objects.filter(
            staff=staff,
            certification_id__in=missing_ids,
            expiration_date__lt=shift_date,
        ).select_related("certification")
        expired_names = [row.certification.name for row in expired_rows]
        expired_ids = set(row.certification_id for row in expired_rows)
        missing_names = list(
            Certification.objects.filter(pk__in=(missing_ids - expired_ids)).values_list(
                "name", flat=True
            )
        )

        return Response(
            {
                "eligible": len(reasons) == 0,
                "reasons": reasons,
                "requiredCertifications": required,
                "missingCertifications": missing_names,
                "expiredCertifications": expired_names,
            }
        )


class StaffProfileView(APIView):
    def get(self, request, pk: int):
        try:
            staff = Staff.objects.get(pk=pk)
        except Staff.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=404)

        certifications = (
            StaffCertification.objects.filter(staff=staff)
            .select_related("certification")
            .order_by("certification__name")
        )
        contracts = (
            Contract.objects.filter(staff=staff)
            .select_related("contract_type")
            .order_by("-start_date")
        )
        assignments = (
            ShiftAssignment.objects.filter(staff=staff)
            .select_related("shift__care_unit__service", "shift__shift_type")
            .order_by("-shift__start_datetime")[:30]
        )
        absences = (
            Absence.objects.filter(staff=staff)
            .select_related("absence_type")
            .order_by("-start_date")[:20]
        )
        hard_preferences = (
            Preference.objects.filter(staff=staff, is_hard_constraint=True)
            .order_by("-start_date")
            .values_list("description", flat=True)
        )
        rules = list(
            Rule.objects.all().order_by("rule_type").values("rule_type", "value", "unit")
        )

        return Response(
            {
                "staff": StaffReadSerializer(staff).data,
                "certifications": [
                    {
                        "name": row.certification.name,
                        "obtainedDate": row.obtained_date.isoformat(),
                        "expirationDate": row.expiration_date.isoformat()
                        if row.expiration_date
                        else None,
                    }
                    for row in certifications
                ],
                "contracts": [
                    {
                        "type": row.contract_type.name,
                        "startDate": row.start_date.isoformat(),
                        "endDate": row.end_date.isoformat() if row.end_date else None,
                        "workloadPercent": row.workload_percent,
                        "nightShiftAllowed": row.contract_type.night_shift_allowed,
                        "maxHoursPerWeek": row.contract_type.max_hours_per_week,
                    }
                    for row in contracts
                ],
                "shiftHistory": [
                    {
                        "assignmentId": row.id,
                        "assignedAt": row.assigned_at.isoformat(),
                        "shiftId": row.shift_id,
                        "service": row.shift.care_unit.service.name,
                        "unit": row.shift.care_unit.name,
                        "shiftType": row.shift.shift_type.name,
                        "start": row.shift.start_datetime.isoformat(),
                        "end": row.shift.end_datetime.isoformat(),
                    }
                    for row in assignments
                ],
                "absences": [
                    {
                        "type": row.absence_type.name,
                        "startDate": row.start_date.isoformat(),
                        "expectedEndDate": row.expected_end_date.isoformat(),
                        "actualEndDate": row.actual_end_date.isoformat()
                        if row.actual_end_date
                        else None,
                    }
                    for row in absences
                ],
                "constraints": {
                    "hardPreferences": list(hard_preferences),
                    "globalRules": rules,
                },
            }
        )


class MetaView(APIView):
    def get(self, request):
        roles = Role.objects.all().order_by("name")
        services = Service.objects.all().order_by("name")
        return Response(
            {
                "roles": RoleSerializer(roles, many=True).data,
                "services": ServiceSerializer(services, many=True).data,
            }
        )

