import os

from ..constants import ROLE_SUPER_ADMIN, VERIFICATION_APPROVED
from ..repositories import ComplaintRepository, FeedbackRepository, ProjectRepository, SchemeRepository, UserRepository
from .auth_service import hash_password

_bootstrapped = False


def create_super_admin_if_needed():
    email = os.getenv("SUPER_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        return None

    user_repository = UserRepository()
    existing = user_repository.find_by_email(email)
    if existing:
        return existing

    username = os.getenv("SUPER_ADMIN_USERNAME", email.split("@")[0]).strip().lower()
    return user_repository.create(
        {
            "full_name": os.getenv("SUPER_ADMIN_NAME", username).strip(),
            "email": email,
            "username": username,
            "mobile_number": os.getenv("SUPER_ADMIN_MOBILE", "9999999999").strip(),
            "password_hash": hash_password(password),
            "role": ROLE_SUPER_ADMIN,
            "verification_status": VERIFICATION_APPROVED,
            "government_id_type": "other",
            "government_id_number": f"SUPER-{os.getenv('SUPER_ADMIN_MOBILE', '9999999999').strip()}",
            "employee_id": "SUPER-ADMIN",
            "department": "Platform Administration",
            "designation": "Super Administrator",
            "village": os.getenv("SUPER_ADMIN_VILLAGE", "Head Office").strip(),
            "district": os.getenv("SUPER_ADMIN_DISTRICT", "Head Office").strip(),
            "state": os.getenv("SUPER_ADMIN_STATE", "Head Office").strip(),
            "pincode": os.getenv("SUPER_ADMIN_PINCODE", "500001").strip(),
            "address_line1": "Platform administration office",
        }
    )


def bootstrap_backend():
    UserRepository().ensure_indexes()
    ComplaintRepository().ensure_indexes()
    FeedbackRepository().ensure_indexes()
    ProjectRepository().ensure_indexes()
    SchemeRepository().ensure_indexes()
    return create_super_admin_if_needed()


def maybe_bootstrap():
    global _bootstrapped
    if _bootstrapped:
        return
    if os.getenv("AUTO_BOOTSTRAP_BACKEND", "False").strip().lower() != "true":
        return

    bootstrap_backend()
    _bootstrapped = True
