from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import CareUnit, Service, Shift, ShiftType, Staff


class Command(BaseCommand):
    help = "Seed demo data for local development."

    def add_arguments(self, parser):
        parser.add_argument("--shifts", type=int, default=10)

    def handle(self, *args, **options):
        shifts_count: int = options["shifts"]

        staff, _ = Staff.objects.get_or_create(
            email="demo.manager@hospital.local",
            defaults={
                "first_name": "Demo",
                "last_name": "Manager",
                "phone": "",
                "is_active": True,
            },
        )

        service, _ = Service.objects.get_or_create(
            name="Emergency",
            defaults={
                "manager": staff,
                "bed_capacity": 20,
                "criticality_level": 5,
            },
        )

        care_unit, _ = CareUnit.objects.get_or_create(
            service=service,
            name="ER Unit",
        )

        shift_type_day, _ = ShiftType.objects.get_or_create(
            name="Day",
            defaults={"duration_hours": 8, "requires_rest_after": False},
        )
        shift_type_night, _ = ShiftType.objects.get_or_create(
            name="Night",
            defaults={"duration_hours": 12, "requires_rest_after": True},
        )

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        created = 0
        for i in range(shifts_count):
            shift_type = shift_type_day if i % 2 == 0 else shift_type_night
            start = now + timedelta(hours=12 * i)
            end = start + timedelta(hours=shift_type.duration_hours)
            _, was_created = Shift.objects.get_or_create(
                care_unit=care_unit,
                shift_type=shift_type,
                start_datetime=start,
                end_datetime=end,
                defaults={"min_staff": 1, "max_staff": 5},
            )
            created += 1 if was_created else 0

        self.stdout.write(self.style.SUCCESS(f"Seeded shifts created: {created}"))
