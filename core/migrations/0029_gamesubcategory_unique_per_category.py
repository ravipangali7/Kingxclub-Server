# Unique constraint on GameSubCategory (game_category, name) to prevent duplicate subcategories

from django.db import migrations, models


def normalize_and_dedupe_subcategories(apps, schema_editor):
    GameSubCategory = apps.get_model("core", "GameSubCategory")
    Game = apps.get_model("core", "Game")
    # Normalize names
    for sub in GameSubCategory.objects.all():
        stripped = (sub.name or "").strip()[:255]
        if stripped != sub.name:
            sub.name = stripped
            sub.save(update_fields=["name"])
    # Merge duplicates: per (game_category_id, name) keep smallest id, reassign games, delete others
    from collections import defaultdict
    by_key = defaultdict(list)
    for sub in GameSubCategory.objects.order_by("id"):
        key = (sub.game_category_id, (sub.name or "").strip())
        by_key[key].append(sub)
    for key, subs in by_key.items():
        if len(subs) <= 1:
            continue
        keep = subs[0]
        for dup in subs[1:]:
            Game.objects.filter(subcategory_id=dup.id).update(subcategory_id=keep.id)
            dup.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_game_subcategory_fk"),
    ]

    operations = [
        migrations.RunPython(normalize_and_dedupe_subcategories, noop_reverse),
        migrations.AddConstraint(
            model_name="gamesubcategory",
            constraint=models.UniqueConstraint(
                fields=("game_category", "name"),
                name="unique_gamesubcategory_per_category",
            ),
        ),
    ]
