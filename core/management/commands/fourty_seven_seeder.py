"""
Forty-Seven Provider PDF Seeder — seeds 47 providers and their games from inout.pdf.

PDF layout: each section has provider name at top center; table has first column =
game name, second column = game uid. Sections are delimited by "-- N of 47 --".
First section is provider "inout"; then "sa gaming", "United gaming", etc.

When seeding providers, the command prompts for api_endpoint, api_secret, and api_token
for each of the 47 providers (optional; leave blank to skip or keep existing).

Options:
  --reset    : Delete all games that appear in the PDF (per provider + game_uid), then reseed.
  --dry-run  : Parse PDF and print counts; no DB writes (no prompts).
  --pdf-path : Override path to PDF (default: inout.pdf next to this command).
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import Game, GameCategory, GameProvider


# ---------------------------------------------------------------------------
# Category inference (mirrors super_game_seeder logic)
# ---------------------------------------------------------------------------

def infer_subcategory(name: str, provider_code: str) -> str:
    """Return a category name inferred from game name and provider."""
    n = (name or "").lower()
    p = (provider_code or "").lower()

    if p in ("saba_sports", "lucksportsgaming", "lucksportgaming"):
        return "Sports Betting"
    if "fishing" in n:
        return "Fishing"
    if "bingo" in n:
        return "Bingo"
    if "roulette" in n:
        return "Roulette"
    if "keno" in n:
        return "Keno"
    if any(kw in n for kw in ("crash", "aviator", "go rush", "balloon")):
        return "Crash"
    if any(kw in n for kw in ("mines", "plinko", "limbo", "tower", "wheel")):
        return "Instant Games"
    if "blackjack" in n:
        return "Blackjack"
    if "baccarat" in n or "bac bo" in n:
        return "Baccarat"
    if any(kw in n for kw in ("poker", "hold'em", "holdem", "stud", "caribbean", "mini flush")):
        return "Poker"
    if any(kw in n for kw in ("teen patti", "teenpatti", "andar bahar", "jhandi munda", "32 cards", "7up7down", "ak47", "hilo", "hi lo")):
        return "Table Games"
    if any(kw in n for kw in ("sic bo", "sicbo", "craps", "dice")):
        return "Dice Games"
    if "dragon tiger" in n or "dragon & tiger" in n:
        return "Dragon Tiger"
    if any(kw in n for kw in ("dream catcher", "monopoly", "crazy time", "funky time", "mega ball", "deal or no deal", "gonzo", "football studio", "stock market", "cash or crash", "crazy coin", "crazy pachinko", "imperial quest", "bac bo")):
        return "Game Shows"
    if any(kw in n for kw in ("lucky 7", "cricket war", "bet on numbers", "color game", "color prediction", "sedie", "fish prawn crab", "thai hi lo", "thai fish")):
        return "Table Games"
    if any(kw in n for kw in ("speed", "lightning", "immersive")):
        return "Live Casino"
    if any(kw in n for kw in ("rummy", "ludo", "callbreak", "tongits", "pusoy", "pool rummy")):
        return "Card & Board Games"
    if "lobby" in n:
        return "Lobby"
    return "Slots"


def provider_name_to_code(display_name: str) -> str:
    """Stable code from provider display name: lowercase, non-alphanumeric -> underscore."""
    name = (display_name or "").strip()
    code = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return code or name.lower() or "unknown"


def is_valid_game_uid(uid: str) -> bool:
    """Accept 32-char hex game UIDs."""
    if not uid or len(uid) != 32:
        return False
    return all(c in "0123456789abcdef" for c in uid.lower())


def parse_pdf_text(text: str) -> list[tuple[str, str, str]]:
    """
    Parse extracted PDF text into (provider_display_name, game_name, game_uid) tuples.
    Sections split by '-- N of 47 --'. First block = inout; each block: first line = provider, rest = table rows.
    """
    # Normalize line endings and split
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]

    # Split into sections by "-- N of 47 --"
    section_re = re.compile(r"^--\s*\d+\s+of\s+47\s*--\s*$", re.IGNORECASE)
    sections = []
    current = []
    for line in lines:
        if section_re.match(line):
            if current:
                sections.append(current)
            current = []
        else:
            current.append(line)
    if current:
        sections.append(current)

    rows = []
    for section in sections:
        # Skip empty and sheet markers
        section = [ln for ln in section if ln and not re.match(r"^Sheet\d+\s*$", ln, re.IGNORECASE)]
        if not section:
            continue
        provider_name = section[0].strip()
        # Match 32-char hex at end of line (game_uid); everything before = game name
        hex32 = re.compile(r"\b([0-9a-fA-F]{32})\s*$")
        for part in section[1:]:
            part = part.strip()
            if not part:
                continue
            m = hex32.search(part)
            if not m:
                continue
            game_uid = m.group(1)
            game_name = part[: m.start()].strip()
            if not game_name:
                continue
            rows.append((provider_name, game_name[:255], game_uid))

    return rows


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract full text from PDF using pdfplumber."""
    import pdfplumber

    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                chunks.append(t)
    return "\n".join(chunks)


class Command(BaseCommand):
    help = "Seed 47 providers and games from inout.pdf; use --reset to delete PDF games and reseed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all games listed in the PDF (per provider + game_uid), then reseed.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse PDF and print provider/game counts; no DB writes.",
        )
        parser.add_argument(
            "--pdf-path",
            type=str,
            default="",
            help="Override path to PDF (default: inout.pdf next to this command).",
        )

    def handle(self, *args, **options):
        reset = options.get("reset", False)
        dry_run = options.get("dry_run", False)
        pdf_path_arg = (options.get("pdf_path") or "").strip()

        default_pdf = Path(__file__).resolve().parent / "inout.pdf"
        pdf_path = Path(pdf_path_arg).resolve() if pdf_path_arg else default_pdf

        if not pdf_path.exists():
            self.stdout.write(self.style.ERROR(f"PDF not found: {pdf_path}"))
            return

        self.stdout.write(f"Reading PDF: {pdf_path}")
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read PDF: {e}"))
            return

        rows = parse_pdf_text(text)
        if not rows:
            self.stdout.write(self.style.WARNING("No game rows parsed from PDF. Check PDF layout and separators '-- N of 47 --'."))
            return

        # Dedupe by (provider_code, game_uid) keeping first
        seen = set()
        unique_rows = []
        for prov_name, game_name, game_uid in rows:
            code = provider_name_to_code(prov_name)
            key = (code, game_uid)
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append((prov_name, game_name, game_uid))

        provider_names = sorted({r[0] for r in unique_rows})
        self.stdout.write(
            self.style.SUCCESS(
                f"Parsed {len(unique_rows)} games across {len(provider_names)} providers."
            )
        )

        if dry_run:
            self.stdout.write(f"Providers: {provider_names}")
            self.stdout.write(self.style.SUCCESS("Dry run: no DB writes."))
            return

        # --reset: delete only games that appear in the PDF
        if reset:
            by_code = {}
            for prov_name, _gn, game_uid in unique_rows:
                code = provider_name_to_code(prov_name)
                by_code.setdefault(code, set()).add(game_uid)
            deleted_total = 0
            for code, uids in by_code.items():
                prov = GameProvider.objects.filter(code=code).first()
                if prov:
                    cnt, _ = Game.objects.filter(provider=prov, game_uid__in=list(uids)).delete()
                    deleted_total += cnt
                    if cnt:
                        self.stdout.write(self.style.WARNING(f"Reset: deleted {cnt} games for provider '{code}'."))
            self.stdout.write(self.style.WARNING(f"Reset: deleted {deleted_total} games total."))

        # Category cache
        cat_cache = {}

        def get_category(cat_name: str) -> GameCategory:
            cat_name = (cat_name or "Other").strip()[:255] or "Other"
            if cat_name in cat_cache:
                return cat_cache[cat_name]
            obj, created = GameCategory.objects.get_or_create(
                name=cat_name,
                defaults={"is_active": True},
            )
            cat_cache[cat_name] = obj
            if created:
                self.stdout.write(f"  Category created: {cat_name}")
            return obj

        # Seed providers (get_or_create by code); prompt for API data for each
        prov_cache = {}
        for prov_name in provider_names:
            code = provider_name_to_code(prov_name)
            self.stdout.write(f"  Provider: {prov_name} ({code})")
            api_endpoint = (input("    api_endpoint [optional]: ").strip() or "https://allapi.online/launch_game1_js")[:200]
            api_secret = (input("    api_secret [optional]: ").strip() or "c3e328ae4568a521971ff61c6b81f667")[:255]
            api_token = (input("    api_token [optional]: ").strip() or "deba4c7e-9ed6-4f31-b814-453d646f7e96")[:255]
            obj, created = GameProvider.objects.get_or_create(
                code=code,
                defaults={
                    "name": prov_name.strip(),
                    "is_active": True,
                    "api_endpoint": api_endpoint,
                    "api_secret": api_secret,
                    "api_token": api_token,
                },
            )
            if not created:
                # Update API fields for existing provider
                obj.api_endpoint = api_endpoint or obj.api_endpoint
                obj.api_secret = api_secret or obj.api_secret
                obj.api_token = api_token or obj.api_token
                obj.save(update_fields=["api_endpoint", "api_secret", "api_token"])
            prov_cache[code] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Provider created: {prov_name} ({code})"))

        # Seed games
        zero = Decimal("0")
        created_count = 0
        skipped_count = 0
        for prov_name, game_name, game_uid in unique_rows:
            code = provider_name_to_code(prov_name)
            provider = prov_cache.get(code)
            if not provider:
                provider = GameProvider.objects.filter(code=code).first()
                if not provider:
                    self.stdout.write(self.style.WARNING(f"Provider '{code}' not found, skipping {game_name!r}."))
                    continue
                prov_cache[code] = provider

            if Game.objects.filter(provider=provider, game_uid=game_uid).exists():
                skipped_count += 1
                continue

            cat_name = infer_subcategory(game_name, code)
            category = get_category(cat_name)
            Game.objects.create(
                provider=provider,
                category=category,
                name=game_name,
                game_uid=game_uid,
                is_active=True,
                min_bet=zero,
                max_bet=zero,
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Providers: {len(provider_names)}. "
                f"Games created: {created_count}, skipped (already exist): {skipped_count}. "
                f"Categories: {len(cat_cache)}."
            )
        )
