# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import garhdony_app.models
import garhdony_app.storage
import garhdony_app.LARPStrings
from django.conf import settings
import djiki.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_name', models.CharField(default=b'', max_length=50, blank=True)),
                ('char_type', models.CharField(max_length=20)),
            ],
            options={
                'ordering': ['-char_type', 'last_name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CharacterStat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(default=b'', max_length=50, blank=True)),
            ],
            options={
                'ordering': ['stat_type'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CharacterStatType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('optional', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', garhdony_app.LARPStrings.LARPTextField(blank=True)),
                ('display_name', garhdony_app.LARPStrings.LARPTextField()),
                ('order_number', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EditLock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('broken', models.BooleanField(default=False)),
                ('saved', models.BooleanField(default=False)),
                ('author', models.ForeignKey(related_name='edit_locks', to=settings.AUTH_USER_MODEL, on_delete=models.RESTRICT)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GameInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name=b'Name')),
                ('usernamesuffix', models.CharField(max_length=50, verbose_name=b'Username Suffix')),
                ('preview_mode', models.BooleanField(default=True)),
                ('complete', models.BooleanField(default=False, verbose_name=b'Game Complete')),
            ],
            options={
                'permissions': (('writer', 'Writer'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GenderizedKeyword',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('male', models.CharField(max_length=50, blank=True)),
                ('female', models.CharField(max_length=50, blank=True)),
                ('category', models.CharField(blank=True, max_length=10, choices=[(b'title', b'title'), (b'name', b'name'), (b'pronoun', b'pronoun')])),
            ],
            options={
                'ordering': ['male'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GenderizedName',
            fields=[
                ('genderizedkeyword_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='garhdony_app.GenderizedKeyword', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('garhdony_app.genderizedkeyword',),
        ),
        migrations.CreateModel(
            name='LogisticalTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('display_text', models.CharField(max_length=400, blank=True)),
                ('deadline', models.DateField(blank=True)),
                ('form_type', models.CharField(blank=True, max_length=30, choices=[(b'confirmation', b'confirmation'), (b'photo', b'photo'), (b'pregame_party', b'pregame_party'), (b'travel_survey', b'travel_survey'), (b'housing_survey', b'housing_survey')])),
                ('sort_order', models.IntegerField()),
                ('page_text', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NonPlayerCharacter',
            fields=[
                ('character_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='garhdony_app.Character', on_delete=models.CASCADE)),
                ('notes', garhdony_app.LARPStrings.LARPTextField(default=b'', blank=True)),
                ('photo', models.ImageField(storage=garhdony_app.storage.DogmasFileSystemStorage(), null=True, upload_to=garhdony_app.models.models.getuploadpath, blank=True)),
                ('npc_gender', models.CharField(default=b'M', max_length=2, choices=[(b'M', b'Male'), (b'F', b'Female')])),
            ],
            options={
            },
            bases=('garhdony_app.character',),
        ),
        migrations.CreateModel(
            name='PlayerCharacter',
            fields=[
                ('character_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='garhdony_app.Character', on_delete=models.CASCADE)),
                ('username', models.CharField(max_length=50, blank=True)),
                ('password', models.CharField(max_length=50, blank=True)),
                ('costuming_hint', garhdony_app.LARPStrings.LARPTextField(default=b'', blank=True)),
                ('default_gender', models.CharField(default=b'M', max_length=2, choices=[(b'M', b'Male'), (b'F', b'Female')])),
            ],
            options={
            },
            bases=('garhdony_app.character',),
        ),
        migrations.CreateModel(
            name='PlayerProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('gender', models.CharField(default=b'M', max_length=1, choices=[(b'M', b'M'), (b'F', b'F')])),
                ('picture', models.ImageField(storage=garhdony_app.storage.DogmasFileSystemStorage(), upload_to=garhdony_app.models.models.getuploadpath, blank=True)),
                ('email', models.CharField(max_length=100, verbose_name=b'What email address can we give to other players for contacting you?', blank=True)),
                ('pregame_party_rsvp', models.NullBooleanField(verbose_name=b'Will you be attending?')),
                ('snail_mail_address', models.CharField(max_length=300, verbose_name=b'If not, give us a snail mail address to send your packet to.', blank=True)),
                ('housing_comments', models.TextField(verbose_name=b"Do you have any dietary restrictions? Any other notes on food or housing? For example, 'I really want a bed to myself' or 'It's very important to me that I get my own room' (that last one is hard to accommodate in our setup).  Please note that most people will be sleeping on airbeds; if this is a problem, please elaborate.", blank=True)),
                ('dietary_restrictions', models.CharField(max_length=200, verbose_name=b'Do you have any dietary restrictions? Anything else we need to know to keep you happily fed for a weekend?', blank=True)),
                ('other_housing', models.TextField(verbose_name=b"Any other notes on food or housing? For example, 'I really want a bed to myself' or 'It's very important to me that I get my own room' (that last one is hard to accommodate in our setup).  Please note that most people will be sleeping on airbeds; if this is a problem, please elaborate.", blank=True)),
                ('character', models.OneToOneField(related_name='PlayerProfile', null=True, blank=True, to='garhdony_app.PlayerCharacter', on_delete=models.SET_NULL)),
                ('done_tasks', models.ManyToManyField(related_name='Players', null=True, to='garhdony_app.LogisticalTask', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sheet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', garhdony_app.LARPStrings.LARPTextField(verbose_name=b'Printed Name')),
                ('filename', models.CharField(max_length=300, verbose_name=b'Internal Name (unique)')),
                ('content_type', models.CharField(default=b'html', max_length=50, choices=[(b'html', b'html'), (b'application/pdf', b'pdf'), (b'image/png', b'png')])),
                ('file', models.FileField(storage=garhdony_app.storage.DogmasFileSystemStorage(), upload_to=garhdony_app.models.models.getuploadpath, blank=True)),
                ('hidden', models.BooleanField(default=True)),
                ('preview_description', garhdony_app.LARPStrings.LARPTextField(default=b'', blank=True)),
                ('last_printed', models.DateTimeField(default=datetime.datetime(2015, 4, 11, 11, 39, 29, 542862), null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model, djiki.models.Versioned),
        ),
        migrations.CreateModel(
            name='SheetColor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('color', models.CharField(max_length=6)),
                ('description', models.CharField(max_length=1000)),
                ('sort_order', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SheetRevision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('description', models.CharField(max_length=400, verbose_name='Description', blank=True)),
                ('content', garhdony_app.LARPStrings.LARPTextField(blank=True)),
                ('author', models.ForeignKey(verbose_name='Author', blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.RESTRICT)),
                ('sheet', models.ForeignKey(related_name='revisions', to='garhdony_app.Sheet', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-created',),
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SheetType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('description', models.CharField(max_length=1000)),
                ('sort_order', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TravelProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('phone', models.CharField(max_length=20, verbose_name=b'Cell Phone Number', blank=True)),
                ('departure_location', models.TextField(verbose_name=b'Where will you be on the morning of Friday, April 25?')),
                ('departure_time', models.TextField(verbose_name=b'What time will you be ready to leave on Friday? (Remember that you need to get to Otisfield, Maine by 6 PM).')),
                ('car_status', models.CharField(max_length=200, verbose_name=b'What is your car status?', choices=[(b'has car', b"I own a car and can help drive others up (we'll reimburse expenses + some wear and tear)"), (b'personal car', b'I own a car but will only drive myself'), (b'can rent', b"I don't own a car, but I am at least 25 and willing to rent a car (Dogmas will pay, of course)"), (b'can rent under 25', b"I don't own a car, but I am under 25 and willing to drive someone else's car"), (b"can't drive", b'I cannot or do not want to drive')])),
                ('dinner_status', models.CharField(max_length=200, verbose_name=b"Do you think you'll come to the wrap-up dinner on Sunday, or go straight home?", choices=[(b'going', b"I'll come to dinner to share stories!"), (b"can't", b'I need to be back early.')])),
                ('other', models.TextField(verbose_name=b'Any other travel information?', blank=True)),
                ('player_profile', models.OneToOneField(related_name='TravelProfile', to='garhdony_app.PlayerProfile', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='sheet',
            name='color',
            field=models.ForeignKey(related_name='sheets', to='garhdony_app.SheetColor', on_delete=models.RESTRICT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='sheet',
            name='game',
            field=models.ForeignKey(related_name='sheets', to='garhdony_app.GameInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='sheet',
            name='sheet_type',
            field=models.ForeignKey(related_name='sheets', blank=True, to='garhdony_app.SheetType', on_delete=models.RESTRICT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='playercharacter',
            name='sheets',
            field=models.ManyToManyField(related_name='characters', to='garhdony_app.Sheet', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='playercharacter',
            name='user',
            field=models.OneToOneField(related_name='character', null=True, default=None, to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='genderizedname',
            name='character',
            field=models.ForeignKey(related_name='genderized_names', to='garhdony_app.Character', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='editlock',
            name='base_revision',
            field=models.ForeignKey(related_name='branching_locks', to='garhdony_app.SheetRevision', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='editlock',
            name='sheet',
            field=models.ForeignKey(related_name='edit_locks', to='garhdony_app.Sheet', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contact',
            name='owner',
            field=models.ForeignKey(related_name='contacts', to='garhdony_app.Character', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contact',
            name='target',
            field=models.ForeignKey(related_name='contacters', to='garhdony_app.Character', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='characterstattype',
            name='game',
            field=models.ForeignKey(related_name='character_stat_types', to='garhdony_app.GameInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='characterstat',
            name='character',
            field=models.ForeignKey(related_name='stats', to='garhdony_app.Character', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='characterstat',
            name='stat_type',
            field=models.ForeignKey(to='garhdony_app.CharacterStatType', on_delete=models.RESTRICT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='character',
            name='first_name_obj',
            field=models.OneToOneField(related_name='first_name_of_character', null=True, blank=True, to='garhdony_app.GenderizedName', on_delete=models.SET_NULL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='character',
            name='game',
            field=models.ForeignKey(related_name='characters', to='garhdony_app.GameInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='character',
            name='title_obj',
            field=models.ForeignKey(related_name='title_of', verbose_name=b'Title', blank=True, to='garhdony_app.GenderizedKeyword', null=True, on_delete=models.SET_NULL),
            preserve_default=True,
        ),
    ]
