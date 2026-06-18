import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.models import Tenant


class Command(BaseCommand):
    help = (
        "Buat atau perbarui akun superuser HRIS (hak tertinggi). "
        "Berguna setelah migrasi MySQL atau login demo gagal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("HRIS_SUPERUSER", "admin"),
            help="Username superuser (default: admin atau HRIS_SUPERUSER)",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("HRIS_ADMIN_PASSWORD", "Admin123456!"),
            help="Password (default: Admin123456! atau HRIS_ADMIN_PASSWORD)",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("HRIS_ADMIN_EMAIL", "admin@hris.local"),
            help="Email superuser",
        )
        parser.add_argument(
            "--tenant",
            default=os.environ.get("HRIS_DEFAULT_TENANT_SLUG", "default"),
            help="Slug tenant yang dihubungkan ke superuser",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        email = options["email"]
        tenant_slug = options["tenant"]

        tenant, created = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={"name": tenant_slug.upper()},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Tenant dibuat: {tenant.slug}"))

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "role": User.Role.ADMIN,
                "tenant": tenant,
            },
        )

        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.role = User.Role.ADMIN
        user.tenant = tenant
        user.set_password(password)
        user.is_active = True
        user.save()

        action = "Dibuat" if created else "Diperbarui"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} superuser '{username}' (tenant={tenant.slug}, role=admin)."
            )
        )
        self.stdout.write(f"Login: {username} / {password}")
