from django.core.management.base import BaseCommand

from api.services.bootstrap import bootstrap_backend


class Command(BaseCommand):
    help = "Creates MongoDB indexes and seeds the initial super admin when environment variables are present."

    def handle(self, *args, **options):
        super_admin = bootstrap_backend()
        self.stdout.write(self.style.SUCCESS("MongoDB indexes have been created successfully."))
        if super_admin:
            self.stdout.write(
                self.style.SUCCESS(f"Super admin is ready: {super_admin.get('email')}")
            )
        else:
            self.stdout.write("No super admin was seeded. Set SUPER_ADMIN_* variables to create one.")
