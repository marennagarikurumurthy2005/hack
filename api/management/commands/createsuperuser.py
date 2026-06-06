from getpass import getpass
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError

from api.constants import ROLE_SUPER_ADMIN, VERIFICATION_APPROVED
from api.repositories import UserRepository
from api.services.auth_service import hash_password


class Command(BaseCommand):
    help = "Creates a platform super admin in MongoDB for this project."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Super admin email address")
        parser.add_argument("--username", type=str, help="Super admin username")
        parser.add_argument("--password", type=str, help="Super admin password")
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            dest="non_interactive",
            help="Fail instead of prompting for missing values",
        )

    def handle(self, *args, **options):
        user_repository = UserRepository()
        user_repository.ensure_indexes()

        non_interactive = options["non_interactive"]

        email = self._resolve_value(options["email"], "Email", non_interactive).strip().lower()
        username = self._resolve_value(options["username"], "Username", non_interactive).strip().lower()
        password = self._resolve_password(options["password"], non_interactive)
        full_name = username
        mobile_number = self._generate_unique_mobile_number(user_repository)
        village = "Head Office"
        district = "Head Office"
        state = "Head Office"
        pincode = "500001"
        address_line1 = "Platform administration office"
        employee_id = self._build_unique_identifier(user_repository.find_by_employee_id, f"SUPER-{username.upper()}")
        government_id_number = self._build_unique_identifier(
            user_repository.find_by_government_id_number,
            f"SUPERID-{username.upper()}",
        )

        if user_repository.find_by_email(email):
            raise CommandError(f"A user with email '{email}' already exists.")
        if user_repository.find_by_username(username):
            raise CommandError(f"A user with username '{username}' already exists.")

        user = user_repository.create(
            {
                "full_name": full_name,
                "email": email,
                "username": username,
                "mobile_number": mobile_number,
                "password_hash": hash_password(password),
                "role": ROLE_SUPER_ADMIN,
                "verification_status": VERIFICATION_APPROVED,
                "government_id_type": "other",
                "government_id_number": government_id_number,
                "employee_id": employee_id,
                "department": "Platform Administration",
                "designation": "Super Administrator",
                "village": village,
                "district": district,
                "state": state,
                "pincode": pincode,
                "address_line1": address_line1,
                "address_line2": None,
                "ward_number": None,
                "review_notes": "Created via management command.",
                "verified_at": None,
                "verified_by": {
                    "id": "system",
                    "full_name": "Management Command",
                    "role": ROLE_SUPER_ADMIN,
                    "is_super_admin": True,
                },
                "last_login_at": None,
            }
        )

        self.stdout.write(self.style.SUCCESS("MongoDB super admin created successfully."))
        self.stdout.write(f"Email: {user.get('email')}")
        self.stdout.write(f"Username: {user.get('username')}")
        self.stdout.write("You can now log in through `/api/auth/login/`.")

    def _resolve_value(self, value, label, non_interactive: bool, default: str | None = None):
        if value:
            return value
        if non_interactive and default is None:
            raise CommandError(f"{label} is required in non-interactive mode.")
        if non_interactive and default is not None:
            return default

        prompt = f"{label}"
        if default is not None:
            prompt = f"{prompt} [{default}]"
        prompt = f"{prompt}: "

        entered = input(prompt).strip()
        if entered:
            return entered
        if default is not None:
            return default
        raise CommandError(f"{label} is required.")

    def _resolve_password(self, value, non_interactive: bool):
        if value:
            return value
        if non_interactive:
            raise CommandError("Password is required in non-interactive mode.")

        password = getpass("Password: ").strip()
        confirm_password = getpass("Password (again): ").strip()
        if not password:
            raise CommandError("Password cannot be empty.")
        if password != confirm_password:
            raise CommandError("Passwords do not match.")
        return password

    def _generate_unique_mobile_number(self, user_repository: UserRepository) -> str:
        while True:
            candidate = f"9{uuid4().int % 1_000_000_000:09d}"
            if not user_repository.find_by_mobile_number(candidate):
                return candidate

    def _build_unique_identifier(self, lookup_func, base_value: str) -> str:
        candidate = base_value
        counter = 2
        while lookup_func(candidate):
            candidate = f"{base_value}-{counter}"
            counter += 1
        return candidate
