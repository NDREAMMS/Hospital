from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import CareUnit, Service, ServiceStatus, StaffLoan, StaffServiceAssignment


class Command(BaseCommand):
    help = "Merge duplicate service names (aliases) into canonical ones."

    # source_name -> canonical_name
    ALIASES = {
        "Emergency": "Urgences",
        "Réanimation": "Reanimation",
    }

    def handle(self, *args, **options):
        merged = 0
        with transaction.atomic():
            for source_name, canonical_name in self.ALIASES.items():
                source = Service.objects.filter(name=source_name).first()
                if not source:
                    continue

                canonical, _ = Service.objects.get_or_create(
                    name=canonical_name,
                    defaults={
                        "manager": source.manager,
                        "bed_capacity": source.bed_capacity,
                        "criticality_level": source.criticality_level,
                    },
                )

                # Keep manager if canonical has none.
                if canonical.manager_id is None and source.manager_id is not None:
                    canonical.manager_id = source.manager_id
                    canonical.save(update_fields=["manager"])

                CareUnit.objects.filter(service=source).update(service=canonical)
                ServiceStatus.objects.filter(service=source).update(service=canonical)
                StaffServiceAssignment.objects.filter(service=source).update(service=canonical)
                StaffLoan.objects.filter(from_service=source).update(from_service=canonical)
                StaffLoan.objects.filter(to_service=source).update(to_service=canonical)

                source.delete()
                merged += 1

        self.stdout.write(self.style.SUCCESS(f"Service aliases merged: {merged}"))

