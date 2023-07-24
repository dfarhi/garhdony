# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import garhdony_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0031_auto_20150924_1421'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheetrevision',
            name='file',
            field=models.FileField(upload_to=garhdony_app.models.sheetrevisionuploadpath, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='sheet',
            name='sheet_status',
            field=models.ForeignKey(related_name='sheets', blank=True, to='garhdony_app.SheetStatus', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='sheet',
            name='sheet_type',
            field=models.ForeignKey(related_name='sheets', to='garhdony_app.SheetType'),
            preserve_default=True,
        ),
    ]
