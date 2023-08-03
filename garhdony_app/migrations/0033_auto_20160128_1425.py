# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import garhdony_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0032_auto_20150924_1806'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmbeddedImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filename', models.CharField(unique=True, max_length=210)),
                ('file', models.FileField(upload_to=garhdony_app.models.models.embeddedImageUploadTo)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('game', models.ForeignKey(related_name='EmbeddedImages', to='garhdony_app.GameInstance', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='sheetrevision',
            name='embeddedImages',
            field=models.ManyToManyField(default=[], related_name='sheetrevisions', to='garhdony_app.EmbeddedImage'),
            preserve_default=True,
        ),
    ]
