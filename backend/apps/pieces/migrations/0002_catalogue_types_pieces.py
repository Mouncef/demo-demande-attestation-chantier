"""Migration de données : alimente le référentiel des types de pièces depuis `catalogue.py`."""

from django.db import migrations


def alimenter(apps, schema_editor):
    from apps.pieces.catalogue import CATALOGUE

    TypePiece = apps.get_model("pieces", "TypePiece")
    for d in CATALOGUE:
        TypePiece.objects.update_or_create(
            code=d.code, defaults={"libelle": d.libelle, "description": d.description, "ordre": d.ordre},
        )


def vider(apps, schema_editor):
    apps.get_model("pieces", "TypePiece").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("pieces", "0001_initial")]
    operations = [migrations.RunPython(alimenter, vider)]
