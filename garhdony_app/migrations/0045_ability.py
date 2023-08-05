# Generated by Django 4.2.3 on 2023-08-03 20:13

from django.db import migrations, models
import django.db.models.deletion
import garhdony_app.LARPStrings


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0044_timeline_timelineevent_timelineviewer_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ability',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', garhdony_app.LARPStrings.LARPTextField()),
                ('characters', models.ManyToManyField(related_name='abilities', to='garhdony_app.playercharacter')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abilities', to='garhdony_app.gameinstance')),
            ],
        ),
    ]
