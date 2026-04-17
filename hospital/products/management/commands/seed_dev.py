from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import (
    CareUnit,
    Contract,
    ContractType,
    Role,
    Service,
    Shift,
    ShiftAssignment,
    ShiftType,
    Staff,
    StaffRole,
    StaffServiceAssignment,
)


class Command(BaseCommand):
    help = "Seed development data: groups/users + demo staff/services/shifts."

    def handle(self, *args, **options):
        # Groups / permissions
        admin_group, _ = Group.objects.get_or_create(name="Administrateur")
        chief_group, _ = Group.objects.get_or_create(name="Medecin chef")
        nurse_group, _ = Group.objects.get_or_create(name="Infirmier")

        products_perms = Permission.objects.filter(content_type__app_label="products")
        admin_group.permissions.set(products_perms)
        chief_group.permissions.set(
            products_perms.filter(
                codename__in=[
                    "view_staff",
                    "view_shift",
                    "view_shiftassignment",
                    "add_shiftassignment",
                    "change_shiftassignment",
                ]
            )
        )
        nurse_group.permissions.set(
            products_perms.filter(
                codename__in=[
                    "view_shift",
                    "view_shiftassignment",
                ]
            )
        )

        # Domain reference data
        role_chief, _ = Role.objects.get_or_create(name="Medecin chef")
        role_nurse, _ = Role.objects.get_or_create(name="Infirmier")

        service_specs = [
            ("Urgences", 20, 4, ["Unite URG"]),
            ("Reanimation", 10, 5, ["Unite REA", "USI"]),
            ("Cardiologie", 18, 4, ["Unite CARDIO", "Soins Intensifs Cardio"]),
            ("Pediatrie", 16, 3, ["Unite PED", "Neonat"]),
            ("Bloc Operatoire", 12, 5, ["Bloc A", "Bloc B"]),
            ("Imagerie", 8, 2, ["Radiologie", "IRM Scanner"]),
        ]

        services: dict[str, Service] = {}
        care_units: dict[str, CareUnit] = {}
        for service_name, beds, criticality, units in service_specs:
            service, _ = Service.objects.get_or_create(
                name=service_name,
                defaults={"bed_capacity": beds, "criticality_level": criticality},
            )
            services[service_name] = service
            for unit_name in units:
                unit, _ = CareUnit.objects.get_or_create(service=service, name=unit_name)
                care_units[f"{service_name}::{unit_name}"] = unit

        day, _ = ShiftType.objects.get_or_create(
            name="Jour",
            defaults={"duration_hours": 8, "requires_rest_after": False},
        )
        night, _ = ShiftType.objects.get_or_create(
            name="Nuit",
            defaults={"duration_hours": 12, "requires_rest_after": True},
        )
        oncall, _ = ShiftType.objects.get_or_create(
            name="Astreinte",
            defaults={"duration_hours": 8, "requires_rest_after": False},
        )

        cdi, _ = ContractType.objects.get_or_create(
            name="CDI",
            defaults={
                "max_hours_per_week": 48,
                "leave_days_per_year": 25,
                "night_shift_allowed": True,
            },
        )
        cdd_no_night, _ = ContractType.objects.get_or_create(
            name="CDD (sans nuit)",
            defaults={
                "max_hours_per_week": 35,
                "leave_days_per_year": 20,
                "night_shift_allowed": False,
            },
        )

        # Users + staff
        User = get_user_model()

        def upsert_user(username: str, password: str):
            user, _ = User.objects.get_or_create(username=username, defaults={"email": username})
            user.set_password(password)
            user.save(update_fields=["password"])
            return user

        admin_user = upsert_user("admin", "admin123")
        admin_user.groups.add(admin_group)

        chief_user = upsert_user("dr_martin", "medecin123")
        chief_user.groups.add(chief_group)

        nurse_user = upsert_user("inf_benali", "infirmier123")
        nurse_user.groups.add(nurse_group)

        dr, _ = Staff.objects.get_or_create(
            email="claire.martin@hospital.local",
            defaults={
                "first_name": "Claire",
                "last_name": "Martin",
                "phone": "",
                "is_active": True,
            },
        )
        if not dr.user_id:
            dr.user = chief_user
            dr.save(update_fields=["user"])
        StaffRole.objects.get_or_create(staff=dr, role=role_chief)
        StaffServiceAssignment.objects.get_or_create(
            staff=dr,
            service=services["Urgences"],
            defaults={"start_date": timezone.now().date()},
        )
        Contract.objects.get_or_create(
            staff=dr,
            contract_type=cdi,
            start_date=timezone.now().date(),
            defaults={"workload_percent": 100},
        )

        nurse, _ = Staff.objects.get_or_create(
            email="hamid.benali@hospital.local",
            defaults={
                "first_name": "Hamid",
                "last_name": "Benali",
                "phone": "",
                "is_active": True,
            },
        )
        if not nurse.user_id:
            nurse.user = nurse_user
            nurse.save(update_fields=["user"])
        StaffRole.objects.get_or_create(staff=nurse, role=role_nurse)
        StaffServiceAssignment.objects.get_or_create(
            staff=nurse,
            service=services["Reanimation"],
            defaults={"start_date": timezone.now().date()},
        )
        Contract.objects.get_or_create(
            staff=nurse,
            contract_type=cdd_no_night,
            start_date=timezone.now().date(),
            defaults={"workload_percent": 100},
        )

        # Shifts
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        shifts_to_create = [
            # Urgences
            (care_units["Urgences::Unite URG"], day, now + timedelta(hours=8)),
            (care_units["Urgences::Unite URG"], night, now + timedelta(hours=20)),
            # Reanimation
            (care_units["Reanimation::Unite REA"], day, now + timedelta(hours=9)),
            (care_units["Reanimation::USI"], oncall, now + timedelta(hours=16)),
            # Cardiologie
            (care_units["Cardiologie::Unite CARDIO"], day, now + timedelta(hours=7)),
            (care_units["Cardiologie::Soins Intensifs Cardio"], night, now + timedelta(hours=19)),
            # Pediatrie
            (care_units["Pediatrie::Unite PED"], day, now + timedelta(hours=8)),
            (care_units["Pediatrie::Neonat"], oncall, now + timedelta(hours=14)),
            # Bloc
            (care_units["Bloc Operatoire::Bloc A"], day, now + timedelta(hours=6)),
            (care_units["Bloc Operatoire::Bloc B"], oncall, now + timedelta(hours=12)),
            # Imagerie
            (care_units["Imagerie::Radiologie"], day, now + timedelta(hours=10)),
            (care_units["Imagerie::IRM Scanner"], oncall, now + timedelta(hours=18)),
        ]

        for care_unit, stype, start in shifts_to_create:
            end = start + timedelta(hours=stype.duration_hours)
            Shift.objects.get_or_create(
                care_unit=care_unit,
                shift_type=stype,
                start_datetime=start,
                end_datetime=end,
                defaults={"min_staff": 1, "max_staff": 1},
            )

        # Mark one shift as already assigned to show "Affecte" in Postes
        first_shift = Shift.objects.order_by("start_datetime").first()
        if first_shift:
            ShiftAssignment.objects.get_or_create(staff=dr, shift=first_shift)

        self.stdout.write(self.style.SUCCESS("Seed completed. Test accounts:"))
        self.stdout.write("  - admin / admin123")
        self.stdout.write("  - dr_martin / medecin123")
        self.stdout.write("  - inf_benali / infirmier123")

