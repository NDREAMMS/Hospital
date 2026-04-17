
"""
Hospital Staffing - Django Models
Traduit depuis le schéma DBML (PostgreSQL)
"""

from django.conf import settings
from django.db import models


# =========================
# F-01 Personnel & Profils
# =========================

class Staff(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_profile",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff"
        verbose_name = "Personnel"
        verbose_name_plural = "Personnels"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Role(models.Model):
    name = models.CharField(max_length=100)  # médecin, infirmier, etc.

    class Meta:
        db_table = "role"
        verbose_name = "Rôle"

    def __str__(self):
        return self.name


class StaffRole(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="staff_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="staff_roles")

    class Meta:
        db_table = "staff_role"
        unique_together = ("staff", "role")
        verbose_name = "Rôle du personnel"

    def __str__(self):
        return f"{self.staff} - {self.role}"


class Specialty(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children"
    )

    class Meta:
        db_table = "specialty"
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"

    def __str__(self):
        return self.name


class StaffSpecialty(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="staff_specialties")
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name="staff_specialties")

    class Meta:
        db_table = "staff_specialty"
        unique_together = ("staff", "specialty")
        verbose_name = "Spécialité du personnel"

    def __str__(self):
        return f"{self.staff} - {self.specialty}"


# =========================
# F-02 Contrats (temporalité)
# =========================

class ContractType(models.Model):
    name = models.CharField(max_length=100)  # CDI, CDD, intérim...
    max_hours_per_week = models.IntegerField()
    leave_days_per_year = models.IntegerField()
    night_shift_allowed = models.BooleanField(default=False)

    class Meta:
        db_table = "contract_type"
        verbose_name = "Type de contrat"

    def __str__(self):
        return self.name


class Contract(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="contracts")
    contract_type = models.ForeignKey(ContractType, on_delete=models.PROTECT, related_name="contracts")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    workload_percent = models.IntegerField()  # 100, 50...

    class Meta:
        db_table = "contract"
        verbose_name = "Contrat"

    def __str__(self):
        return f"{self.staff} - {self.contract_type} ({self.start_date})"


# =========================
# F-03 Certifications
# =========================

class Certification(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "certification"
        verbose_name = "Certification"

    def __str__(self):
        return self.name


class CertificationDependency(models.Model):
    parent_cert = models.ForeignKey(
        Certification, on_delete=models.CASCADE, related_name="dependencies"
    )
    required_cert = models.ForeignKey(
        Certification, on_delete=models.CASCADE, related_name="required_by"
    )

    class Meta:
        db_table = "certification_dependency"
        unique_together = ("parent_cert", "required_cert")
        verbose_name = "Dépendance de certification"

    def __str__(self):
        return f"{self.parent_cert} requiert {self.required_cert}"


class StaffCertification(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="certifications")
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE, related_name="staff_certifications")
    obtained_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "staff_certification"
        verbose_name = "Certification du personnel"

    def __str__(self):
        return f"{self.staff} - {self.certification}"


# =========================
# F-04 Services & Unités
# =========================

class Service(models.Model):
    name = models.CharField(max_length=150)
    manager = models.ForeignKey(
        Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_services"
    )
    bed_capacity = models.IntegerField()
    criticality_level = models.IntegerField()

    class Meta:
        db_table = "service"
        verbose_name = "Service"

    def __str__(self):
        return self.name


class CareUnit(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="care_units")
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "care_unit"
        verbose_name = "Unité de soins"
        verbose_name_plural = "Unités de soins"

    def __str__(self):
        return f"{self.name} ({self.service})"


class ServiceStatus(models.Model):
    STATUS_CHOICES = [
        ("ouvert", "Ouvert"),
        ("ferme", "Fermé"),
        ("sous-effectif", "Sous-effectif"),
    ]
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="statuses")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "service_status"
        verbose_name = "Statut du service"

    def __str__(self):
        return f"{self.service} - {self.status} ({self.start_date})"


class StaffServiceAssignment(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="service_assignments")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="staff_assignments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "staff_service_assignment"
        verbose_name = "Affectation principale"

    def __str__(self):
        return f"{self.staff} → {self.service} ({self.start_date})"


# =========================
# F-05 Gardes & créneaux
# =========================

class ShiftType(models.Model):
    name = models.CharField(max_length=100)  # jour, nuit, week-end...
    duration_hours = models.IntegerField()
    requires_rest_after = models.BooleanField(default=False)

    class Meta:
        db_table = "shift_type"
        verbose_name = "Type de garde"

    def __str__(self):
        return self.name


class Shift(models.Model):
    care_unit = models.ForeignKey(CareUnit, on_delete=models.CASCADE, related_name="shifts")
    shift_type = models.ForeignKey(ShiftType, on_delete=models.PROTECT, related_name="shifts")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    min_staff = models.IntegerField()
    max_staff = models.IntegerField()

    class Meta:
        db_table = "shift"
        verbose_name = "Garde / Créneau"

    def __str__(self):
        return f"{self.care_unit} - {self.shift_type} ({self.start_datetime})"


class ShiftRequiredCertification(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="required_certifications")
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE, related_name="required_for_shifts")

    class Meta:
        db_table = "shift_required_certification"
        unique_together = ("shift", "certification")
        verbose_name = "Certification requise pour garde"

    def __str__(self):
        return f"{self.shift} → {self.certification}"


class ShiftAssignment(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="assignments")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="shift_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shift_assignment"
        verbose_name = "Affectation de garde"

    def __str__(self):
        return f"{self.staff} → {self.shift}"


# =========================
# F-06 Absences
# =========================

class AbsenceType(models.Model):
    name = models.CharField(max_length=100)
    impacts_quota = models.BooleanField(default=True)

    class Meta:
        db_table = "absence_type"
        verbose_name = "Type d'absence"

    def __str__(self):
        return self.name


class Absence(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="absences")
    absence_type = models.ForeignKey(AbsenceType, on_delete=models.PROTECT, related_name="absences")
    start_date = models.DateField()
    expected_end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    is_planned = models.BooleanField(default=True)

    class Meta:
        db_table = "absence"
        verbose_name = "Absence"

    def __str__(self):
        return f"{self.staff} - {self.absence_type} ({self.start_date})"


# =========================
# F-07 Préférences & Contraintes
# =========================

class Preference(models.Model):
    TYPE_CHOICES = [
        ("preference", "Préférence"),
        ("contrainte", "Contrainte"),
    ]
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="preferences")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    is_hard_constraint = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "preference"
        verbose_name = "Préférence / Contrainte"

    def __str__(self):
        return f"{self.staff} - {self.type}: {self.description}"


# =========================
# F-08 Charge patient
# =========================

class PatientLoad(models.Model):
    care_unit = models.ForeignKey(CareUnit, on_delete=models.CASCADE, related_name="patient_loads")
    date = models.DateField()
    patient_count = models.IntegerField()
    occupancy_rate = models.FloatField()

    class Meta:
        db_table = "patient_load"
        verbose_name = "Charge patient"
        unique_together = ("care_unit", "date")

    def __str__(self):
        return f"{self.care_unit} - {self.date}: {self.patient_count} patients"


# =========================
# F-09 Prêts inter-services
# =========================

class StaffLoan(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="loans")
    from_service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="loans_out")
    to_service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="loans_in")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "staff_loan"
        verbose_name = "Prêt inter-services"

    def __str__(self):
        return f"{self.staff}: {self.from_service} → {self.to_service} ({self.start_date})"


# =========================
# F-10 Règles métier configurables
# =========================

class Rule(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=50)  # ex: "max_hours", "rest_time"
    value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)  # hours, days...
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "rule"
        verbose_name = "Règle métier"

    def __str__(self):
        return f"{self.name} ({self.rule_type}: {self.value} {self.unit})"
