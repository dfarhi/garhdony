# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0030_auto_20150422_1408'),
    ]

    operations = [
        migrations.CreateModel(
            name='SheetStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('description', models.CharField(max_length=1000)),
                ('sort_order', models.IntegerField()),
                ('game', models.ForeignKey(related_name='sheet_status', to='garhdony_app.GameInstance')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='sheet',
            name='sheet_status',
            field=models.ForeignKey(related_name='sheets', to='garhdony_app.SheetStatus', null=True),
            preserve_default=True,
        ),
    ]
