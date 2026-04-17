"""
Hospital Staffing — API REST (Django REST Framework)
Endpoints pour la création / modification / suppression d'affectations.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from .models import ShiftAssignment, Staff, Shift
from .services import create_assignment, update_assignment, delete_assignment


# ─────────────────────────────────────────────
# Serializers
# ─────────────────────────────────────────────

class ShiftAssignmentReadSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    shift_label = serializers.SerializerMethodField()

    class Meta:
        model = ShiftAssignment
        fields = ["id", "staff", "staff_name", "shift", "shift_label", "assigned_at"]

    def get_staff_name(self, obj):
        return str(obj.staff)

    def get_shift_label(self, obj):
        return str(obj.shift)


class ShiftAssignmentWriteSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()

    def validate_staff_id(self, value):
        try:
            return Staff.objects.get(pk=value, is_active=True)
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Soignant introuvable ou inactif.")

    def validate_shift_id(self, value):
        try:
            return Shift.objects.select_related(
                "shift_type", "care_unit__service"
            ).get(pk=value)
        except Shift.DoesNotExist:
            raise serializers.ValidationError("Créneau introuvable.")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _django_validation_to_drf(exc: DjangoValidationError):
    """Convertit une ValidationError Django en Response DRF 400."""
    return Response(
        {"errors": exc.messages},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ─────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────

class ShiftAssignmentListCreateView(APIView):
    """
    GET  /api/assignments/        — liste toutes les affectations
    POST /api/assignments/        — crée une affectation (toutes les contraintes dures vérifiées)
    """

    def get(self, request):
        assignments = ShiftAssignment.objects.select_related(
            "staff", "shift__shift_type", "shift__care_unit"
        ).all()
        serializer = ShiftAssignmentReadSerializer(assignments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ShiftAssignmentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        staff = serializer.validated_data["staff_id"]
        shift = serializer.validated_data["shift_id"]

        try:
            assignment = create_assignment(staff=staff, shift=shift)
        except DjangoValidationError as e:
            return _django_validation_to_drf(e)

        return Response(
            ShiftAssignmentReadSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class ShiftAssignmentDetailView(APIView):
    """
    GET    /api/assignments/<id>/   — détail d'une affectation
    PATCH  /api/assignments/<id>/   — modifie le soignant ou le créneau (revalidation complète)
    DELETE /api/assignments/<id>/   — supprime (vérifie le seuil de sécurité)
    """

    def _get_assignment(self, pk):
        try:
            return ShiftAssignment.objects.select_related(
                "staff", "shift__shift_type", "shift__care_unit"
            ).get(pk=pk)
        except ShiftAssignment.DoesNotExist:
            return None

    def get(self, request, pk):
        assignment = self._get_assignment(pk)
        if not assignment:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShiftAssignmentReadSerializer(assignment).data)

    def patch(self, request, pk):
        assignment = self._get_assignment(pk)
        if not assignment:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        new_staff = None
        new_shift = None

        if "staff_id" in request.data:
            try:
                new_staff = Staff.objects.get(pk=request.data["staff_id"], is_active=True)
            except Staff.DoesNotExist:
                return Response({"staff_id": ["Soignant introuvable."]}, status=400)

        if "shift_id" in request.data:
            try:
                new_shift = Shift.objects.select_related("shift_type", "care_unit").get(
                    pk=request.data["shift_id"]
                )
            except Shift.DoesNotExist:
                return Response({"shift_id": ["Créneau introuvable."]}, status=400)

        try:
            assignment = update_assignment(
                assignment=assignment,
                new_staff=new_staff,
                new_shift=new_shift,
            )
        except DjangoValidationError as e:
            return _django_validation_to_drf(e)

        return Response(ShiftAssignmentReadSerializer(assignment).data)

    def delete(self, request, pk):
        assignment = self._get_assignment(pk)
        if not assignment:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        try:
            delete_assignment(assignment)
        except DjangoValidationError as e:
            return _django_validation_to_drf(e)

        return Response(status=status.HTTP_204_NO_CONTENT)
    
