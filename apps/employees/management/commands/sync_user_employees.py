from django.core.management.base import BaseCommand

from apps.core.models import User
from apps.employees.services.user_link import ensure_employee_profile, link_user_to_employee


class Command(BaseCommand):
    help = "Link auth users to employee records (and auto-provision when enabled)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--link-only",
            action="store_true",
            help="Only match existing employees; do not auto-provision new rows",
        )

    def handle(self, *args, **options):
        link_only = options["link_only"]
        linked = 0
        provisioned = 0
        skipped = 0

        qs = User.objects.filter(
            is_active=True,
            role__in=[User.Role.EMPLOYEE, User.Role.MANAGER],
        ).select_related("tenant", "plant")

        for user in qs:
            if getattr(user, "employee_profile", None):
                skipped += 1
                continue

            before = link_user_to_employee(user)
            if before:
                linked += 1
                self.stdout.write(f"Linked {user.username} → {before.employee_id}")
                continue

            if link_only:
                self.stdout.write(
                    self.style.WARNING(f"No match for {user.username} (link-only mode)")
                )
                continue

            profile = ensure_employee_profile(user)
            if profile:
                provisioned += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Provisioned {user.username} → {profile.employee_id}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Could not link or provision {user.username}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: linked={linked}, provisioned={provisioned}, already_ok={skipped}"
            )
        )
