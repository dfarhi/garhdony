# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import garhdony_app.storage
import datetime
import garhdony_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0005_auto_20150411_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nonplayercharacter',
            name='photo',
            field=models.ImageField(storage=garhdony_app.storage.DogmasFileSystemStorage(), null=True, upload_to=garhdony_app.models.getuploadpath, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='playerprofile',
            name='picture',
            field=models.ImageField(storage=garhdony_app.storage.DogmasFileSystemStorage(), upload_to=garhdony_app.models.getuploadpath, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2015, 4, 11, 17, 6, 59, 714923), null=True),
            preserve_default=True,
        ),
    ]
