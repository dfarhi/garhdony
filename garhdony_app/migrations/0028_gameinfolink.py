# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0027_auto_20150422_1014'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameInfoLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('link_url', models.TextField()),
                ('label', models.CharField(max_length=50)),
                ('game', models.ForeignKey(related_name='info_links', to='garhdony_app.GameInstance', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
