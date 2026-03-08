"""
Run the app with Daphne (ASGI) so both HTTP and WebSocket work in one process.
Use this instead of 'runserver' when you need real-time (e.g. chat).

  python manage.py runserver_asgi
  python manage.py runserver_asgi 0.0.0.0:8000

Like Node: one server, API + WebSocket from the same port.
"""
import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run HTTP + WebSocket server (Daphne). One process for API and real-time."

    def add_arguments(self, parser):
        parser.add_argument(
            "addrport",
            nargs="?",
            default="0.0.0.0:8000",
            help="Optional host:port (default 0.0.0.0:8000).",
        )

    def handle(self, *args, **options):
        try:
            from daphne.cli import CommandLineInterface as DaphneCLI
        except ImportError:
            self.stderr.write("Install daphne: pip install daphne")
            sys.exit(1)

        addrport = options["addrport"]
        if ":" in addrport:
            host, port = addrport.rsplit(":", 1)
        else:
            host, port = "0.0.0.0", addrport

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "karnalix.settings")

        asgi_app = "karnalix.asgi:application"
        self.stdout.write(f"Starting Daphne (HTTP + WebSocket) on {host}:{port} …")
        self.stdout.write("Quit with CTRL-BREAK.")

        argv = ["daphne", "-b", host, "-p", str(port), asgi_app]
        sys.argv = argv
        DaphneCLI().run()
