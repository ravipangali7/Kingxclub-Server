from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.models import UserRole


class Command(BaseCommand):
    help = "Create powerhouse, super, and master accounts (password: 12345678)."

    def handle(self, *args, **options):
        User = get_user_model()
        password = "12345678"

        accounts = [
            {
                "username": "powerhouse",
                "role": UserRole.POWERHOUSE,
                "is_superuser": True,
                "is_staff": True,
            },
            {
                "username": "super",
                "role": UserRole.SUPER,
                "is_superuser": True,
                "is_staff": True,
            },
            {
                "username": "master",
                "role": UserRole.MASTER,
                "is_superuser": False,
                "is_staff": True,
            },
        ]

        for data in accounts:
            username = data["username"]
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f"User '{username}' already exists, skipping.")
                )
                continue
            user = User(
                username=username,
                role=data["role"],
                is_superuser=data["is_superuser"],
                is_staff=data["is_staff"],
                is_active=True,
                name=username.capitalize(),
            )
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Created user '{username}' (role={data['role']}, is_superuser={data['is_superuser']}).")
            )

        self.stdout.write(self.style.SUCCESS("Done."))
