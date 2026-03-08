"""Shared helpers for management commands (e.g. game image resolution)."""
from pathlib import Path


def _normalize_for_match(s: str) -> str:
    """Lowercase, alphanumeric only (spaces/underscores/hyphens removed) for matching."""
    return "".join(c for c in (s or "").lower() if c.isalnum())


# Minimum overlap length to consider a partial match (avoids "a" matching "game")
MIN_PARTIAL_OVERLAP = 3


def _longest_common_substring(s: str, t: str) -> int:
    """Length of longest common substring of s and t (for flexible matching e.g. ravigame vs ravilib -> ravi)."""
    if not s or not t:
        return 0
    m, n = len(s), len(t)
    # dp[i][j] = length of LCS ending at s[i-1], t[j-1]
    prev = [0] * (n + 1)
    best = 0
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                curr[j] = prev[j - 1] + 1
                best = max(best, curr[j])
            else:
                curr[j] = 0
        prev = curr
    return best


def _partial_match_score(game_norm: str, stem_norm: str) -> int | None:
    """
    Powerful partial match: containment (ravi in ravigame), prefix/suffix, or longest common substring (ravigame vs ravilib).
    Returns best score for ranking; None if overlap below MIN_PARTIAL_OVERLAP.
    """
    if not game_norm or not stem_norm:
        return None
    scores: list[int] = []

    # Exact equality
    if game_norm == stem_norm:
        return len(game_norm) * 2

    # One contains the other (ravi <-> ravigame, ravi <-> ravilib)
    if game_norm in stem_norm:
        scores.append(len(game_norm))
    if stem_norm in game_norm:
        scores.append(len(stem_norm))

    # Common prefix (ravi + ravigame -> 4)
    prefix = 0
    for i in range(min(len(game_norm), len(stem_norm))):
        if game_norm[i] == stem_norm[i]:
            prefix += 1
        else:
            break
    if prefix >= MIN_PARTIAL_OVERLAP:
        scores.append(prefix)

    # Common suffix
    suffix = 0
    for i in range(1, min(len(game_norm), len(stem_norm)) + 1):
        if game_norm[-i] == stem_norm[-i]:
            suffix += 1
        else:
            break
    if suffix >= MIN_PARTIAL_OVERLAP:
        scores.append(suffix)

    # Longest common substring when neither contains the other (e.g. ravigame vs ravilib -> ravi = 4)
    lcs = _longest_common_substring(game_norm, stem_norm)
    if lcs >= MIN_PARTIAL_OVERLAP:
        scores.append(lcs)

    return max(scores) if scores else None


def find_image_for_game(folder: Path, game_name: str, game_uid: str = "") -> Path | None:
    """
    Return path to a .webp or .png in folder matching game_name or game_uid.
    Order: exact -> normalized -> partial. Partial match uses powerful rules: one contains the other
    (ravi/ravigame), common prefix/suffix, or longest common substring (ravigame/ravilib); min overlap 3 chars.
    """
    if not folder.exists():
        return None
    exts = (".webp", ".png")

    def try_exact(base: str) -> Path | None:
        if not base:
            return None
        base = base.strip()
        for ext in exts:
            p = folder / f"{base}{ext}"
            if p.exists():
                return p
        return None

    def try_normalized(value: str) -> Path | None:
        if not value:
            return None
        norm = _normalize_for_match(value)
        for ext in exts:
            for p in folder.glob(f"*{ext}"):
                if _normalize_for_match(p.stem) == norm:
                    return p
        return None

    def try_partial(value: str) -> Path | None:
        """Best partial match: containment (ravi<->ravigame), prefix/suffix, or LCS (ravigame<->ravilib); prefer longest overlap."""
        if not value:
            return None
        value_norm = _normalize_for_match(value)
        best: tuple[int, Path] | None = None
        for ext in exts:
            for p in folder.glob(f"*{ext}"):
                stem_norm = _normalize_for_match(p.stem)
                score = _partial_match_score(value_norm, stem_norm)
                if score is not None and (best is None or score > best[0]):
                    best = (score, p)
        return best[1] if best else None

    # 1. Exact filename by game name
    if game_name:
        p = try_exact(game_name)
        if p:
            return p
    # 2. Normalized name vs stem
    if game_name:
        p = try_normalized(game_name)
        if p:
            return p
    # 3. Exact filename by game_uid
    if game_uid:
        p = try_exact(game_uid)
        if p:
            return p
    # 4. Normalized uid vs stem
    if game_uid:
        p = try_normalized(game_uid)
        if p:
            return p
    # 5. Partial match: game name vs stem (name in filename or filename in name)
    if game_name:
        p = try_partial(game_name)
        if p:
            return p
    if game_uid:
        p = try_partial(game_uid)
        if p:
            return p
    return None


def get_image_folder_candidates(docs_games: Path, provider_code: str) -> list[Path]:
    """
    Return candidate image folders for a provider (e.g. spribe, evolution_live).
    Tries: <provider_code>, <provider_code_no_underscore>webp, and first-word + webp (evolutionwebp).
    """
    candidates: list[Path] = []
    # Exact slug folder (e.g. spribe, evolution_live)
    candidates.append(docs_games / provider_code)
    # No-underscore + "webp" (e.g. evolutionlivewebp, pragmaticlivewebp, sexygamingwebp)
    no_underscore = provider_code.replace("_", "")
    if no_underscore:
        candidates.append(docs_games / f"{no_underscore}webp")
    # First segment + "webp" (e.g. evolution_live -> evolutionwebp)
    first_part = provider_code.split("_")[0] if provider_code else ""
    if first_part and first_part != no_underscore:
        candidates.append(docs_games / f"{first_part}webp")
    return candidates


def find_image_for_game_in_folders(
    folder_candidates: list[Path], game_name: str, game_uid: str = ""
) -> Path | None:
    """Try find_image_for_game in each folder; return first match."""
    for folder in folder_candidates:
        path = find_image_for_game(folder, game_name, game_uid)
        if path:
            return path
    return None


def infer_category(name: str) -> str:
    """Infer category from game name. Returns category name (max 255 chars). Same logic as JILI seeder."""
    n = (name or "").strip()
    n_lower = n.lower()
    if "fishing" in n_lower:
        return "Fishing"
    if "bingo" in n_lower:
        return "Bingo"
    if "roulette" in n_lower:
        return "Roulette"
    if "keno" in n_lower:
        return "Keno"
    if "crash" in n_lower:
        return "Crash"
    table_keywords = (
        "baccarat", "blackjack", "poker", "teen patti", "teenpatti", "andar bahar",
        "rummy", "ludo", "callbreak", "tongits", "pusoy", "caribbean", "texas hold",
        "sic bo", "video poker", "stud poker", "mini flush", "pool rummy", "ak47",
        "jhandi munda", "fish prawn crab", "speed baccarat", "sabong", "e-sabong",
    )
    for kw in table_keywords:
        if kw in n_lower:
            return "Live Casino"
    return "Slot"


def provider_code_to_slug(code: str) -> str:
    """Normalize provider code/name to a slug for folder names (e.g. 'Evolution live' -> 'evolution_live')."""
    s = (code or "").strip().lower()
    return "".join(c if c.isalnum() or c in " -_" else "" for c in s).replace(" ", "_").replace("-", "_").strip("_") or "unknown"
