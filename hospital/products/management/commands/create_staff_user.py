from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from products.models import Staff


class Command(BaseCommand):
    help = "Create (or link) a Django auth user for a Staff row."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Staff email (must exist in Staff table)")
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        email: str = options["email"]
        password: str = options["password"]

        try:
            staff = Staff.objects.get(email=email)
        except Staff.DoesNotExist as exc:
            raise CommandError(f"Staff with email '{email}' does not exist.") from exc

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={"email": email},
        )
        user.set_password(password)
        user.save(update_fields=["password"])

        staff.user = user
        staff.save(update_fields=["user"])

        self.stdout.write(self.style.SUCCESS(f"Linked staff id={staff.id} to user id={user.id}"))

