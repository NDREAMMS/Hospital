from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import Contract, ContractType, Staff


class Command(BaseCommand):
    help = "Ensure each staff member has at least one active contract (dev helper)."

    def add_arguments(self, parser):
        parser.add_argument("--name", help="Filter staff by name contains", default=None)

    def handle(self, *args, **options):
        name_filter: str | None = options["name"]

        qs = Staff.objects.all()
        if name_filter:
            qs = qs.filter(first_name__icontains=name_filter) | qs.filter(
                last_name__icontains=name_filter
            )

        default_ct, _ = ContractType.objects.get_or_create(
            name="CDI",
            defaults={
                "max_hours_per_week": 40,
                "leave_days_per_year": 25,
                "night_shift_allowed": True,
            },
        )

        today = timezone.now().date()
        created = 0
        for staff in qs:
            active = (
                Contract.objects.filter(staff=staff, start_date__lte=today)
                .filter(end_date__isnull=True)
                .exists()
            )
            if active:
                continue
            Contract.objects.create(
                staff=staff,
                contract_type=default_ct,
                start_date=today,
                workload_percent=100,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Contracts created: {created}"))

