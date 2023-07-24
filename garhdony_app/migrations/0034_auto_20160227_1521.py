# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0033_auto_20160128_1425'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name=b'Name')),
                ('blurb', models.TextField()),
                ('about', models.TextField()),
                ('app', models.TextField()),
            ],
            options={
                'permissions': (('writer', 'Writer'),),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='gameinstance',
            name='template',
            field=models.ForeignKey(related_name='instances', to='garhdony_app.GameTemplate', null=True),
            preserve_default=True,
        ),
    ]
