# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0039_quizsubmission'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimelineEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('date', models.DateField()),
                ('default_description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TimelineEventCharacterDescription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('unique_description', models.TextField(blank=True)),
                ('character', models.ForeignKey(related_name='event_descriptions', to='garhdony_app.PlayerCharacter', on_delete=models.CASCADE)),
                ('event', models.ForeignKey(related_name='descriptions', to='garhdony_app.TimelineEvent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='timelineeventcharacterdescription',
            unique_together=set([('event', 'character')]),
        ),
        migrations.AddField(
            model_name='timelineevent',
            name='characters',
            field=models.ManyToManyField(to='garhdony_app.PlayerCharacter', through='garhdony_app.TimelineEventCharacterDescription'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='timelineevent',
            name='game',
            field=models.ForeignKey(related_name='timeline_events', to='garhdony_app.GameInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genderizedkeyword',
            name='female',
            field=models.CharField(max_length=50),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genderizedkeyword',
            name='male',
            field=models.CharField(max_length=50),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='playerprofile',
            name='dietary_restrictions',
            field=models.CharField(max_length=200, verbose_name=b'Do you have any dietary restrictions? Any snack preferences?', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='travelprofile',
            name='car_status',
            field=models.CharField(max_length=200, verbose_name=b'What is your car status?', choices=[(b'has car', b"I own a car and can help drive others up (we'll reimburse expenses + some wear and tear)"), (b'personal car', b'I own a car but will only drive myself'), (b'can rent', b"I don't own a car, but I am at least 25 and willing to rent a car (we will pay, of course)"), (b'can rent under 25', b"I don't own a car, but I am under 25 and willing to drive someone else's car"), (b"can't drive", b'I cannot or do not want to drive')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='travelprofile',
            name='departure_location',
            field=models.TextField(verbose_name=b'Where will you be leaving from?'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='travelprofile',
            name='departure_time',
            field=models.TextField(verbose_name=b'What time will you be ready to leave?'),
            preserve_default=True,
        ),
    ]
