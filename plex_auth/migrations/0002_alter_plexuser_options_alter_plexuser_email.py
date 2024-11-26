# Generated by Django 5.1.3 on 2024-11-25 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plex_auth", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="plexuser",
            options={"verbose_name": "Plex User", "verbose_name_plural": "Plex Users"},
        ),
        migrations.AlterField(
            model_name="plexuser",
            name="email",
            field=models.EmailField(
                blank=True, max_length=254, verbose_name="email address"
            ),
        ),
    ]
