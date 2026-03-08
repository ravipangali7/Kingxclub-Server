# Remove GameSubCategory model and Game.subcategory FK

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_gamesubcategory_unique_per_category"),
    ]

    operations = [
        # Remove FK from Game to GameSubCategory first
        migrations.RemoveField(
            model_name="game",
            name="subcategory",
        ),
        # Remove the unique constraint before deleting the model
        migrations.RemoveConstraint(
            model_name="gamesubcategory",
            name="unique_gamesubcategory_per_category",
        ),
        # Delete the GameSubCategory model (drops the table)
        migrations.DeleteModel(
            name="GameSubCategory",
        ),
    ]
