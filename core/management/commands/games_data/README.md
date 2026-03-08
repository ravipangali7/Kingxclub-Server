# Game data for Super Game Seeder

This folder is shipped with the app so `super_game_seeder` works on VPS without path config.

## Contents (included)

- **XLSX:** Evolution live.xlsx, evoplay asia.xlsx, Pragmatic live.xlsx, SmartSoft Gaming.xlsx, SABA Sports.xlsx, Sexy Gaming.xlsx
- **TXT:** spribe.txt, lucksportsgaming.txt
- **Image folders:** evolutionwebp, ezugiwebp, jiliwebp, pragmaticlivewebp, sexygamingwebp, spribe

Ezugi and JILI game lists are embedded in the command; their images come from ezugiwebp and jiliwebp here.

## Run on VPS

```bash
python manage.py super_game_seeder --full-reset
```

Optionally: `--dry-run`, `--fresh`, `--providers=ezugi,jili,...`, `--images-only`.
