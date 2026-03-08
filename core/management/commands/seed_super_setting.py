"""Seed SuperSetting with game API credentials (secret, token, callback URL) from api-doc."""
from django.core.management.base import BaseCommand

from core.models import SuperSetting


# Credentials and default game server (api-doc / PHP reference)
GAME_API_SECRET = "4d45bba519ac2d39d1618f57120b84b7"
GAME_API_TOKEN = "184de030-912d-4c26-81fc-6c5cd3c05add"
# Callback URL must be the exact URL where your Django API is served (provider will POST here).
# If your API is at https://admin.kingxclub.com/api, use https://admin.kingxclub.com/api/callback/
GAME_API_CALLBACK_URL = "https://admin.kingxclub.com/api/callback/"
# Base URL for getProvider/providerGame; launch must use launch_game1_js (launch_game_js returns errors)
GAME_API_BASE_URL_DEFAULT = "https://allapi.online"
GAME_API_LAUNCH_URL_DEFAULT = "https://allapi.online/launch_game1_js"


class Command(BaseCommand):
    help = (
        "Seed or update SuperSetting with game API secret, token, and callback URL. "
        "Optionally set game_api_url with --base-url, game_api_domain_url with --domain-url, game_api_launch_url with --launch-url."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="If provided, set game_api_url (e.g. https://YOUR_GAME_API_SERVER).",
        )
        parser.add_argument(
            "--callback-url",
            type=str,
            default=None,
            help="If provided, set game_api_callback_url (e.g. https://admin.kingxclub.com/api/callback/). Must be the URL where your Django API is served.",
        )
        parser.add_argument(
            "--domain-url",
            type=str,
            default=None,
            help="If provided, set game_api_domain_url (e.g. https://kingxclub.com for launch payload).",
        )
        parser.add_argument(
            "--launch-url",
            type=str,
            default=None,
            help="If provided, set game_api_launch_url (e.g. https://allapi.online/launch_game1_js for allapi launch).",
        )

    def handle(self, *args, **options):
        obj = SuperSetting.objects.first()
        if obj is None:
            obj = SuperSetting()
        obj.game_api_secret = GAME_API_SECRET
        obj.game_api_token = GAME_API_TOKEN
        callback_url = options.get("callback_url")
        if callback_url:
            obj.game_api_callback_url = callback_url.strip()
        else:
            obj.game_api_callback_url = GAME_API_CALLBACK_URL
        base_url = options.get("base_url")
        domain_url = options.get("domain_url")
        if base_url:
            obj.game_api_url = base_url.strip()
        else:
            obj.game_api_url = GAME_API_BASE_URL_DEFAULT
        if domain_url:
            obj.game_api_domain_url = domain_url.strip()
        launch_url = options.get("launch_url")
        if launch_url:
            obj.game_api_launch_url = launch_url.strip()
        else:
            obj.game_api_launch_url = GAME_API_LAUNCH_URL_DEFAULT
        obj.save()
        self.stdout.write(
            self.style.SUCCESS(
                "SuperSetting seeded with game API secret, token, and callback URL."
            )
        )
        if base_url:
            self.stdout.write(self.style.SUCCESS(f"game_api_url set to: {base_url}"))
        if callback_url:
            self.stdout.write(self.style.SUCCESS(f"game_api_callback_url set to: {callback_url}"))
        self.stdout.write(self.style.SUCCESS(f"game_api_callback_url = {obj.game_api_callback_url or '(empty)'} (give this URL to your game provider)"))
        if domain_url:
            self.stdout.write(self.style.SUCCESS(f"game_api_domain_url set to: {domain_url}"))
        self.stdout.write(self.style.SUCCESS(f"game_api_launch_url set to: {obj.game_api_launch_url or '(empty)'}"))
