from typing import List
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
import os
import shutil
import pdfkit
import re
from datetime import datetime
from diff_match_patch import diff_match_patch
from django.utils import timezone
from garhdony_app.storage import DogmasFileSystemStorage
import garhdony_app.utils as utils
from garhdony_app.LARPStrings import LARPTextField, larpstring_to_python
from djiki.models import Versioned, Revision
from django.shortcuts import render
from .assign_writer_game import assign_writer_game
import logging
import random

logger = logging.getLogger(__name__)  # TODO: Organize logging.


def getuploadpath(a, b): pass  # For historic reasons, migrations believe this function exists.


class QuizSubmission(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=20)

    def __str__(self):
        return self.result + "  (" + self.created_at.ctime() + ")"


class WebsiteAboutPage(models.Model):
    """
    This is a single-instance class that represents the website's about page text. We want it editable through the admin
    interface so we need to break databases like this. Sorry!
    """
    content = models.TextField()


class GameTemplate(models.Model):
    """
    A thing that a GameInstance is an instance of
    """

    class Meta:
        # This lets writers have permissions on each game.
        # You can check it with [User].has_perm('garhdony_app.writer', game)
        permissions = (
            ('writer', 'Writer'),
        )

    name = models.CharField("Name", max_length=50)
    short_desc = models.TextField()
    blurb = models.TextField()
    about = models.TextField()
    how_to_app = models.TextField()

    app = models.TextField()
    interest = models.TextField()

    is_accepting_apps = models.BooleanField()

    def __str__(self):
        return self.name

    @property
    def is_upcoming(self):
        return self.instances.filter(complete=False).count() > 0


class GameInstance(models.Model):
    """
    A GameInstance is ... an instance of a game. It's like Dogmas 2014.
    Basically every other object points to a GameInstance.
    """

    class Meta:
        # This lets writers have permissions on each game.
        # You can check it with [User].has_perm('garhdony_app.writer', game)
        permissions = (
            ('writer', 'Writer'),
        )

    name = models.CharField("Name", max_length=50)

    template = models.ForeignKey(GameTemplate, related_name="instances", null=True, on_delete=models.SET_NULL)

    # usernamesuffix is appended to the characters' usernames to get the actual login usernames
    # Like rrihul14. This is so that different runs of the same game can have rrihul14 and rrihul15.
    usernamesuffix = models.CharField("Username Suffix", max_length=50)

    # preview_mode determines whether people can log in and see everything, or just see sheets where hidden=False
    preview_mode = models.BooleanField(default=True)

    # complete determines whether players can see all sheets.
    complete = models.BooleanField("Game Complete", default=False)

    def __str__(self):
        return self.name

    def writers(self):
        all_writers = Group.objects.get(name="Writers").user_set.all()
        my_writers = [w for w in all_writers if w.has_perm("garhdony_app.writer", self)]
        return my_writers

    def pcs(self):
        return PlayerCharacter.objects.filter(game=self)

    def npcs(self):
        return NonPlayerCharacter.objects.filter(game=self)

    @property
    def media_directory(self):
        # All the stuff is stored in subfolders of media_directory
        return self.name

    @property
    def abs_media_directory(self):
        return settings.MEDIA_ROOT + self.media_directory

    @property
    def sheets_directory(self):
        # Sheets PDFs go here.
        return self.media_directory + '/sheets/'

    @property
    def abs_sheets_directory(self):
        return self.abs_media_directory + '/sheets/'

    @property
    def photos_directory(self):
        # player photos (and npc photos) go here.
        return self.media_directory + '/player_photos/'

    @property
    def abs_photo_directory(self):
        return self.abs_media_directory + '/player_photos/'

    def delete(self, *args, **kwargs):
        # Deleting a game can only be done through the admin interface when logged in as admin.
        # THis is intentional; don't do this by accident!

        # Delete the media
        if os.path.exists(self.abs_media_directory):
            shutil.rmtree(self.abs_media_directory)

        # Delete the PlayerProfiles attached to the PCs
        # And the PCs themselves.
        for pc in self.pcs():
            try:
                pc.PlayerProfile.delete(*args, **kwargs)
            except ObjectDoesNotExist:
                pass
            pc.delete(*args, **kwargs)

        # Delete the NPCs
        for npc in self.npcs():
            npc.delete(*args, **kwargs)

        # Delete the sheets.
        for sheet in self.sheets.all():
            sheet.delete(*args, **kwargs)

        # TODO: Do we forget to delete Contacts? CharacterStats?
        super(GameInstance, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # this gets called whether its new or modified, so first figure out which it is:
        if self.pk:  # get the old data to compare to.
            change = True
            old_game = GameInstance.objects.get(id=self.id)
        else:
            change = False

        # Do the normal stuff
        super(GameInstance, self).save(*args, **kwargs)
        if change:
            if old_game.usernamesuffix != self.usernamesuffix:
                # If usernamesuffix changed, we have to change the django User objects
                # tied to the characters to reflect the new usernames.
                for char in self.pcs():
                    char.save()
            if old_game.abs_media_directory != self.abs_media_directory:
                # If media_directory changed, we need to move files over
                shutil.move(old_game.abs_media_directory, self.abs_media_directory)
        else:
            # When creating a game we need to mae tha appropriate directories
            os.makedirs(self.abs_sheets_directory)
            os.makedirs(self.abs_photo_directory)

    def clone(self, new_name, new_suffix):
        """
        Makes a clone of the entire game, including all characters and sheets.
        The idea is that after Dogmas 14, if we want to run Dogmas 15, we just clone it.
        """
        # TODO: Might miss contacts? character stats?
        new_game = GameInstance(name=new_name, usernamesuffix=new_suffix)
        new_game.save()

        for cst in self.character_stat_types.all():
            new_cst = CharacterStatType(game=new_game, name=cst.name)
            new_cst.save()


        # Copy all sheets, keeping a mapping dictionary for later use in assigning characters
        sheet_mapping = {}
        for sheet in self.sheets.all():
            new_sheet = sheet.clone(new_game)
            sheet_mapping[sheet] = new_sheet

        # Clone all the characters. Character cloning doesn't copy sheets,
        # so we don't need to remove old sheets.
        for character in self.pcs():
            new_character = character.clone(new_game)
            for s in character.sheets.all():
                new_character.sheets.add(sheet_mapping[s])
            new_character.save()
            new_character.set_stats_from_dict(character.stats_dict())
        for character in self.npcs():
            character.clone(new_game)

        for w in self.writers():
            assign_writer_game(w, new_game)

        return new_game

    def relevant_genderized_keywords(self) -> List["GenderizedKeyword"]:
        # These are all the words that might need to be tied to a person's gender
        # This include he/she, Baron/baroness, and Nicalao/Nikol. The pronouns and titles
        # Are universal across all games, but names is just the ones from this game.
        pronouns = GenderizedKeyword.objects.filter(category='pronoun')
        titles = GenderizedKeyword.objects.filter(category='title')
        names = GenderizedName.objects.filter(character__game=self)
        return list(pronouns) + list(titles) + list(names)

    def print_all_sheets(self):
        # This exports all sheets to pdfs.
        # TODO: IT's not currently callable by the users. 4/14
        for s in self.sheets:
            s.print_sheet_pdf()


def embeddedImageUploadTo(embeddedimage, filename=''):
    return os.path.join(embeddedimage.game.sheets_directory, "embedded_images/", embeddedimage.filename)


class EmbeddedImage(models.Model):
    # name = models.CharField(max_length=200)
    filename = models.CharField(max_length=210, unique=True)
    game = models.ForeignKey(GameInstance, related_name="EmbeddedImages", on_delete=models.CASCADE)
    file = models.FileField(upload_to=embeddedImageUploadTo)
    # sheets = models.ManyToManyField(Sheet, related_name="EmbeddedImages")
    timestamp = models.DateTimeField(auto_now_add=True, blank=True)


    def delete(self, using=None):
        os.remove(self.absolute_path)
        super(EmbeddedImage, self).delete(using)

    @property
    def absolute_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.game.sheets_directory, "embedded_images/", self.filename)

    @property
    def url(self):
        return reverse('embedded_image', args=[self.game.name, self.filename])

    @classmethod
    def current_images_sheets_dict(cls, game):
        all_images = EmbeddedImage.objects.filter(game=game)
        through = SheetRevision.embeddedImages.through
        dic = {image.id: set() for image in all_images}
        for sheet in game.sheets.all():
            for link in through.objects.filter(sheetrevision_id=sheet.current_revision.id):
                dic[link.embeddedimage_id].add(sheet)
        return dic

    @property
    def sheets(self):
        result = []
        for rev in self.sheetrevisions.all():
            result.append(rev.sheet)
        return set(result)



class SheetColor(models.Model):
    # A sheetcolor is like "bluesheet" or "yellowsheet."
    # These are universal across games.
    # These are not currently editable by writers -- maybe that should change?

    # 'Bluesheet'
    name = models.CharField(max_length=30)

    # Hex color, like FFFFFF.  Maybe get some sort of colorField thing for this?
    color = models.CharField(max_length=6)

    # E.g. "A bluesheet is a sheet everyone gets" (displays on character home pages).
    description = models.CharField(max_length=1000)

    # Order it appears in players' lists.
    sort_order = models.IntegerField()

    def __str__(self):
        return self.name


class SheetType(models.Model):
    # Analogous to sheetcolor.

    name = models.CharField(max_length=30)
    description = models.CharField(max_length=1000)
    sort_order = models.IntegerField()

    def __str__(self):
        return self.name


class SheetStatus(models.Model):
    # What is the status of the sheet?

    name = models.CharField(max_length=30)
    description = models.CharField(max_length=1000)
    sort_order = models.IntegerField()
    game = models.ForeignKey(GameInstance, related_name='sheet_status', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


def sheetuploadpath(sheet, filename=''):
    # The path to the pdf version of a sheet.

    # This morally belongs in the Sheet class, but apparently it can't be there because of something about migrations.

    ext = sheet.get_content_type_display()
    if ext == "html": ext = "pdf"  # html-type files still download pdfs from pdfs.
    return os.path.join(sheet.game.sheets_directory, sheet.filename + "." + ext)


def infinite_past_func(): pass  # Migrations think this function has to exist. It doesn't do anything.


class Sheet(models.Model, Versioned):
    # A Sheet represents like "History of Ambrus" from Dogmas 2014.
    # It is tied to a GameInstance; different runs of the same game will have different Sheet objects
    # So that history is preserved.

    # It has metadata (color, sheet_type, game, etc)

    # and it's a Versioned, which is a class from djiki that makes it have revisions.
    # The contents are contained in sheet.last_revision (the most recent revision)

    class Meta:
        # This tells django what to do whenever someone wants to sort sheets.
        ordering = ['name']

    @property
    def full_path(self):
        # This is the path for the sheet's pdf.
        return os.path.join(settings.MEDIA_ROOT, sheetuploadpath(self))

    color = models.ForeignKey(SheetColor, related_name='sheets', on_delete=models.RESTRICT)
    sheet_type = models.ForeignKey(SheetType, related_name='sheets', on_delete=models.RESTRICT)
    sheet_status = models.ForeignKey(SheetStatus, related_name='sheets', null=True, blank=True, on_delete=models.SET_NULL)
    game = models.ForeignKey(GameInstance, related_name='sheets', on_delete=models.CASCADE)

    # filename is what the PDF is saved as, so it has to be unique. Of course Printed Names might be non-unique.
    name = LARPTextField(verbose_name="Printed Name")
    filename = models.CharField(max_length=300, verbose_name="Internal Name (unique)")

    # content_type is almost always html.
    # But if we want upload a png or pdf, we can do that
    # No one has used png or pdf in a while, so they might not work 4/14
    content_type_choices = (('html', 'html'), ('application/pdf', 'pdf'), ('image/png', 'png'),)
    content_type = models.CharField(max_length=50, default='html', choices=content_type_choices)

    # This field named "file" is probably unused? 4/14
    file = models.FileField(upload_to=sheetuploadpath, blank=True, storage=DogmasFileSystemStorage())

    # If hidden is true, it won't be displayed to players while the game is in preview mode (or ever? Not sure)
    hidden = models.BooleanField(default=True)

    # preview_description is the description the players get while the game is in preview mode. If hidden is true it doesn't matter.
    preview_description = LARPTextField(blank=True, default="")

    # last_printed is that timestamp of the last export to PDF
    infinite_past = timezone.make_aware(datetime(2000, 1, 1), timezone.utc)
    last_printed = models.DateTimeField(default=infinite_past, null=True)

    # last_revision is a property that holds the last_revision object, so we don't have to look it up over and over again.
    # So you should always look it up as current_revision; it just stores the value here.
    # This caching system is probably not actually saving us appreciable time, since finding the last revision should be
    # fast now that loading revisions into memory doesn't bring the content until it's needed.
    _last_revision = None

    @property
    def current_revision(self):

        if self._last_revision is None:
            logger.debug(str(datetime.now()) + ": Loading last_revision of sheet: %s" % self.filename)
            self._last_revision = super(Sheet, self).last_revision()
            return self._last_revision
        else:
            return self._last_revision


    def __str__(self):
        return self.filename

    @property
    def ever_printed(self):
        return self.last_printed != Sheet.infinite_past

    def needs_exporting(self):
        # Have there been changes since this was last exported to PDF?

        if self.current_revision == None:
            # Sheets created before SheetRevisions were a thing sometimes have no revisions.
            return False
        if self.last_printed == None:
            # I don't know what this means...
            return False  # ?
        if self.last_printed < self.current_revision.created:
            return True
        # TODO: check for genders changing somehow?
        return False

    def print_sheet_pdf(self):
        # Export the thml to pdf
        # This uses pdfkit, which requires wkhtmltopdf.

        # First generate the html, by pretending that we're going to render it from sheet_plain (the plain html template):
        # This used to be render_to_response in django 1.7; now it's just render.
        # Not sure we're using the new function quite right.
        http_response = render(None, 'garhdony_app/sheet_plain.html',
                                           {'revision': self.current_revision, 'sheet': self})
        html = http_response.content

        # Call pdfkit's pdf generator, remembering to put in the css.
        # If you change this css, change it in the sheet_plain.html template too.
        path = self.full_path
        css = os.path.join(settings.STATIC_ROOT, 'garhdony_app/basics.css')
        pdfkit.from_string(html.decode('UTF-8'), path, css=css, options={'encoding': 'UTF-8'})

        # Update last_printed.
        self.last_printed = timezone.now()
        self.save()

    def clone(self, new_game):
        """
        Makes a new version of the sheet in the database, tied to a new game
        For when games clone themselves.
        """
        new = Sheet(color=self.color, sheet_type=self.sheet_type, game=new_game, name=self.name,
                    content_type=self.content_type, filename=self.filename,
                    preview_description=self.preview_description)
        new.save()
        if self.ever_printed:
            src = self.full_path
            dest = new.full_path
            shutil.copy(src, dest)

        last_rev = self.current_revision

        new_rev = SheetRevision(sheet=new, description="cloned from previous game", content=last_rev.content if last_rev is not None else Sheet.new_sheet_content)
        new_rev.save()
        return new

    def save(self, *args, **kwargs):
        # save is called when it's updated or created
        # so first check which it is by seeing if it already exists (has a pk).
        if self.pk:
            change = True
            old_sheet = Sheet.objects.get(id=self.id)
        else:
            change = False

        super(Sheet, self).save(*args, **kwargs)

        # Move the file if we've changed the file path
        if change and self.ever_printed and old_sheet.full_path != self.full_path:
            shutil.move(old_sheet.full_path, self.full_path)
        # Make an initial revision if it's new. The or is for old sheets created before the revision system,
        # which may not have revisions.
        if not change or len(self.revisions.all()) == 0:
            first_revision = SheetRevision(description="Sheet Created", content=Sheet.new_sheet_content, sheet=self)
            first_revision.save()


    def url(self, viewing_character):
        # Returns the url for viewing this sheet. I believe this is never used 4/14
        # Does basically the same thing as the tag sheet|view_url ?
        if self.game.complete:
            label = self.filename
        else:
            label = self.name
        return reverse('character_sheet', args=[self.game.name, viewing_character.username, label])

    def current_lock(self):
        # The currently active edit lock.
        # Each sheet should only ever have one edit lock that has neither been saved nor broken.

        current_locks = self.edit_locks.filter(saved=False)
        unbroken_locks = list(current_locks.filter(broken=False))
        if len(unbroken_locks) > 1:
            raise ValueError('Multiple Valid Locks. WTF?' + str(unbroken_locks))
        elif len(unbroken_locks) == 0:
            return None
        else:
            return unbroken_locks[0]

    def break_lock(self):
        # Break the current edit lock.
        current = self.current_lock()
        if current is not None:
            current.break_lock()

    def steal_lock(self, new_lock):
        # break the current lock and unbreak new_lock.
        # This will make new_lock the current_lock
        # Don't feed in a saved new_lock, or else there will be no current_lock.
        self.break_lock()
        new_lock.broken = False
        new_lock.save()
        assert self.current_lock() == new_lock

    def delete(self, *args, **kwargs):
        # Remember to delete the PDF.
        if os.path.exists(self.full_path):
            os.remove(self.full_path)
        super(Sheet, self).delete(*args, **kwargs)

    new_sheet_content = larpstring_to_python('You\'ve made a sheet! Here it is. It has some words in it. ' \
                        'Probably you can think of better words to put in it. ' \
                        'I bet you\'ve already thought of lots of ways to improve these words. ' \
                        'Like deleting them all and putting some of your own.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp;You can do that! You have the power to change all these words. ' \
                        'First click on the "Write" tab at the top. Have you done that? Good. Now you can change the words ' \
                        'as much as you want. You can even delete the rest of these words before you even read them. ' \
                        'Don\'t worry, they quickly deteriorate into complete and utter unhelpfulness. ' \
                        'I recommend replacing them as soon as possible.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Why are these words still here? ' \
                        'They have nothing to do with your LARP. ' \
                        'Some of them aren\'t even sentences. Like these ones here. ' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Some of them words have <i>simple</i> htm<b>l ta</b>gs, which you can control with the normal ' \
                        'Cmd/Ctrl-B/I/U buttons. Others have even ' \
                        '<span data-larp-action="stnote" class="writers-bubble stnote" contenteditable="false">' \
                        '<span contenteditable="true">stranger tags</span>' \
                        '<span data-larp-action="writers-bubble-inner" class="writers-bubble-inner" style="-webkit-transform: matrix(1, 0, 0, 1, -262.5, -116); transform: matrix(1, 0, 0, 1, -262.5, -116);">' \
                        '<table class="stnote triangle-pointer" contenteditable="true">' \
                        '<tr><th colspan="2">Storyteller Note</th><th class="button-cell" style="text-align:right"></th></tr>' \
                        '<tr><td colspan="3" class="writers-bubble-content">This is a storyteller note. You can make your own, and do lots of other things, by highlighting text and selecting an option from the black bubble.</td></tr>' \
                        '<tr><th>david</th><th width="40"></th><th style="text-align:right">Thu Apr 16 2015</th></tr></table>' \
                        '</span>' \
                        '</span>' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Apparently you think these words are still interesting and not confusing enough, ' \
                        'because they seem to still be present. I can tell because you are reading them. ' \
                        'If you want some words that are way more incomprehensible, allow me to recommend the Mode button in the top left. ' \
                        'That will show you the raw html, in all it\'s ugliness. You can edit that directly if you can stomach it.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; What? You want a less ugly Mode where you can actually hear yourself think? ' \
                        'Yeah, that\'s a good idea, maybe we\'ll make it at some point.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Do you want to know why the word ' \
                        '<span data-default-gender="M" contenteditable="false" data-larp-action="gender-static" class="gender-static">he</span> ' \
                        'in this sentence is <span data-larp-action="todo" class="writers-bubble todo" contenteditable="false"><span contenteditable="true">grey</span><span data-larp-action="writers-bubble-inner" class="writers-bubble-inner" style="-webkit-transform: matrix(1, 0, 0, 1, -228, -98); transform: matrix(1, 0, 0, 1, -228, -98);"><table class="todo triangle-pointer" contenteditable="true"><tr><th colspan="2">To Do</th><th class="button-cell" style="text-align:right"></th></tr><tr><td colspan="3" class="writers-bubble-content">Is it not grey? Have you not even clicked the "Write" tab? That was like, step 1. Keep up.</td></tr><tr><th>david</th><th width="40"></th><th style="text-align:right">Thu Apr 16 2015</th></tr></table></span></span>? ' \
                        'That\'s because it has gender markup! If you type a word like "<span data-default-gender="M" contenteditable="false" data-larp-action="broken-gender-switch" class="broken-gender-switch">he<span data-larp-action="alt-gender" class="alt-gender"><span data-keyword="121" data-larp-action="alt-possibility">she</span></span></span>" and save the page, ' \
                        'it will redirect you back to the edit page and ask you to resolve them! ' \
                        'You can click on the red words to resolve them; select the character they refer to (or STATIC) and then press enter.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Too lazy to actually do it? Don\'t worry, your edits were saved before you got redirected to the red text.' \
                        '<br>&nbsp;&nbsp;&nbsp;&nbsp; Ok, fine, I guess you were right to keep reading this; it did tell you stuff. ' \
                        'But the idea was that all the stuff would be so simple you could figure it out on your own. ' \
                        'Now we\'ll never know if it was simple enough! ' \
                        'Well, probably everyone else just deleted this text, so we can see if they figured out what to do.')


class SheetRevisionManager(models.Manager):
    """
    This ensures that we only load the content when it's actually needed,
    by making the default queryset use "defer(content'). So content is only pulled from the database when needed."
    """
    use_for_related_fields = True
    def get_queryset(self):
        return super(SheetRevisionManager, self).get_queryset().defer('content')


def sheetrevisionuploadpath(revision, filename=''):
    ext = revision.sheet.get_content_type_display()

    if not revision.pk:
        index = len(revision.sheet.revisions.all())
    else:
        index = list(revision.sheet.revisions.order_by('created').all()).index(revision)
    return os.path.join(revision.sheet.game.sheets_directory, revision.sheet.filename + str(index) + "." + ext)


class SheetRevision(Revision):
    # Revisions mostly just come from djiki's Revision.
    # They are versions of sheets. Each Revision of a sheet contains the entire sheet as of that moment, in content.
    # content is a LARPTextField, since it contains tons of stnotes and gender switches and stuff.
    # We use the manager above to avoid loading content when not needed, since it's a large html file.
    sheet = models.ForeignKey(Sheet, related_name='revisions', on_delete=models.CASCADE)
    content = LARPTextField(blank=True)
    objects = SheetRevisionManager()
    embeddedImages = models.ManyToManyField(EmbeddedImage, related_name='sheetrevisions', default=[])

    # For content_type=png or pdf sheets, instead of content we use file.
    file = models.FileField(upload_to=sheetrevisionuploadpath, blank=True)

    @property
    def fullfilepath(self): return os.path.join(settings.MEDIA_ROOT, sheetrevisionuploadpath(self))

    def save(self, *args, **kwargs):
        super(SheetRevision, self).save(*args, **kwargs)
        if self.content != '':
            starttime = datetime.now()
            imgregex = r"<img.*? data-id=['\"](^\s*)['\"] .*?>"
            imgregex = r"<img.*? data-id=['\"]([^\s]*)['\"] .*?>"
            matches = re.findall(imgregex, self.content.render_for_user(writer=True))
            images = {int(match_id) for match_id in matches}
            self.embeddedImages.set(images)
            # Django saves automatically upon changing m2m field; no need to call save explicitly.
            logger.debug(
                str(datetime.now()) + ": Image Search took " + str(datetime.now() - starttime) + " (Found " + str(
                    len(matches)) + ")")


class EditLock(models.Model):
    # Every time someone opens an edit tab, that edit tab gets an edit lock.
    # That edit lock is glued to that edit tab forever; don't take it for a different tag since
    # there will be problems if two people try to save a lock.

    # An edit lock stays tied to its tab, and has one of two fates:
    # it is saved, so the saved property becomes True
    # someone else wants to edit the sheet, and so breaks it (so broken becomes True)

    # Any unsaved EditLock can be saved; if it's unbroken then it just saves. If it's broken, then you have an edit conflict and try to merge.

    # EditLocks stay forever in the db, since space is cheap. If this becomes a problem, we could remove old ones at some point.

    # Most of the logic for actually using these things is in views.writer_sheet_edit

    sheet = models.ForeignKey(Sheet, related_name='edit_locks', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    broken = models.BooleanField(default=False)
    base_revision = models.ForeignKey(SheetRevision, related_name='branching_locks', on_delete=models.CASCADE)
    saved = models.BooleanField(default=False)
    author = models.ForeignKey(User, related_name='edit_locks', on_delete= models.RESTRICT)

    def __str__(self):
        return "Edit Lock by %(author)s at %(time)s" % {"author": self.author, "time": self.created}

    def break_lock(self):
        self.broken = True
        self.save()

    def retimestamp(self):
        self.created = timezone.now()
        self.save()

    def commit(self):
        """
        This gets called when the edit associated with this lock is saved.

        It retimestamps the lock to the current time, so that anyone who created a lock in the intervening time
        knows to conflict with it.
        """

        self.retimestamp()

    @property
    def status(self):
        """ Returns the status as a string (Active, Broken, or Saved), for displaying. """
        if self.broken:
            return "Broken"
        elif self.saved:
            return "Saved"
        else:
            return "Active"

    @property
    def created_display(self):
        """ The created time in pretty display format. """
        local_time = timezone.localtime(self.created)
        if local_time.date() < datetime.now().date():
            result = local_time.strftime("%b %d")
        else:
            result = local_time.strftime("%I:%M %p")
        return result


class GenderizedKeyword(models.Model):
    # A GenderizedKeyword is a thing with a male and female version, for use by LARPText things.
    # There are three kinds:
    # pronouns (universal English things),
    # titles (universal things which characters can have as their title)
    # names (tied to a character and thus a game). These are a subclass; every GenderizedKeyword whose category is "name" should be a GenderizedName
    # male and female names are required fields (don't have blank=True) because empty genderized keywords slow down the
    # website a lot.
    male = models.CharField(max_length=50)
    female = models.CharField(max_length=50)
    category_choices = (("title", "title"), ("name", "name"), ("pronoun", "pronoun"),)
    category = models.CharField(max_length=10, choices=category_choices, blank=True)

    class Meta:
        ordering = ['male']

    @property
    def is_name(self):
        return self.category == 'name'

    def resolve(self, gender):
        if gender == "M":
            return self.male
        elif gender == "F":
            return self.female
        elif gender is None:
            return self.__str__()

    @property
    def actually_genderized(self):
        return self.male != self.female

    def __str__(self):
        if self.actually_genderized:
            return "[" + self.male + "/" + self.female + "]"
        else:
            return self.male


    @property
    def regex_male(self):
        if not self.male in ['', '????']:
            return '\\b' + re.escape(self.male) + '\\b'
        else:
            return ''


    @property
    def regex_female(self):
        if self.female not in ['', '????']:
            return '\\b' + re.escape(self.female) + '\\b'
        else:
            return ''

    # regex returns the regex for searching strings to look for the corresponding version.
    # This is needed by LARPString technology to check for unresolved gendered pronouns.
    @property
    def regex(self):
        # We want to find names even if they are not genderized.
        # Since they might still change.

        if self.actually_genderized or self.category == 'name':
            return utils.regex_join([self.regex_male, self.regex_female])
        else:
            return ''

    def match(self, word):
        '''
        Check to see if a word could be an unresolved instance of this keyword.
        :param word: the word the check.
        :return: Dictionary {
                'gender': 'M'/'F',
                'alt': the other version of this keyword,
                'id': this keywords db id,
                'keyword': this keyword object}
        '''
        found = False
        if re.match(self.regex_male + '$', word, re.IGNORECASE):
            gender = 'M'
            alt = self.female
            found = True
        if re.match(self.regex_female + '$', word, re.IGNORECASE):
            gender = 'F'
            alt = self.male
            found = True
        if not found:
            return None

        # Make alt match the case of word.
        # This will match lowercase, Capitalized, and ALLCAPS.
        alt = utils.matchcase(word, alt)
        return {'gender': gender, 'alt': alt, 'id': self.id, 'keyword': self}


class GenderizedName(GenderizedKeyword):
    """
    A GenderizedKeyword tied to a character. This includes first names and nicknames;
    They are treated exactly the same.
    """
    character = models.ForeignKey("Character", related_name="genderized_names", on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        # Enforce that all GenderizedNames have category="name"
        super(GenderizedName, self).__init__(*args, **kwargs)
        self.category = "name"

    def auto_resolve(self):
        # Because they always refer to the same character, they can resolve without a gender input.
        return self.resolve(self.character.gender())

    def clone(self, new_character, commit=True):
        # For cloning games; make a new one of these tied to the new character.
        new = GenderizedName(character=new_character, male=self.male, female=self.female)
        if commit:
            new.save()
        return new


class Character(models.Model):
    """
    The Character Model.
    It's really more of an abstract class; every Character is either a PlayerCharacter or a NonPlayerCharacter
        (But the database doesn't entirely understand abstract classes, so it's not officially)
        (And in fact, if you get out a thing as a character, you might have to call character.cast() to turn it into a PC/NPC object as appropriate)
    """
    # TODO: Make the abstractness real with Meta.abstract=True?

    class Meta:
        # Sort by char_type (with PC before NPC) then by last name.
        ordering = ['-char_type', 'last_name']

    # title and first_name both point to GenderizedKeywords; last_name is just a text field. Don't genderize your last names please?
    # Because first_name is a Name which has a pointer to a character, these have a circular reference
    # This is good; you want to be able to go either way.
    # But if you are modifying them, it can be very confusing to keep them in sync
    # And you can get werid behavior if they get out of sync.
    title_obj = models.ForeignKey(GenderizedKeyword, related_name="title_of", blank=True, null=True,
                                  verbose_name="Title", on_delete=models.SET_NULL)
    first_name_obj = models.OneToOneField(GenderizedName, related_name="first_name_of_character", blank=True, null=True, on_delete=models.SET_NULL)
    last_name = models.CharField(max_length=50, default="", blank=True)
    game = models.ForeignKey(GameInstance, related_name='characters', on_delete=models.CASCADE)
    # char_type is either "PC" or "NPC"
    char_type = models.CharField(max_length=20)

    def __str__(self):
        return self.full_name()

    def nonfirst_names(self):
        '''
        :return: All my nicknames; names that are not my first name.
        '''
        return GenderizedName.objects.filter(character=self).exclude(pk=self.first_name_obj.pk)

    def first_name(self):
        """
        :return: My actual first name as a string.
        """
        if self.first_name_obj is not None:
            # This should be equivalent to self.first_name_obj.auto_resolve(), unless we're in a weird half-saved state.
            return self.first_name_obj.resolve(self.gender())
        else:
            return "NO FIRST NAME"

    def title(self):
        """
        :return: My actual title.
        """
        if self.title_obj is not None:
            return self.title_obj.resolve(self.gender())
        else:
            return ""

    def name(self):
        raw = self.first_name() + ' ' + self.last_name
        return raw.strip()

    def full_name(self):
        raw = self.title() + ' ' + self.first_name() + ' ' + self.last_name
        return raw.strip()

    def delete(self, *args, **kwargs):
        self.first_name_obj.delete()
        for name in self.genderized_names.all():
            name.delete()

        super(Character, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Note that on a new character, save() also creates a bunch of related objects, 
        like blank stats and first_name.
        """
        
        # save gets called for updates and for creations, so first lets check which it is:
        change = self.pk is not None

        if change:
            # This could maybe be improved with select_related.
            # Basically, we need to load the previous version for seeing what changed.
            old_char = Character.objects.get(id=self.id)

            # rename my photo if my name (and thus its path) has changed.
            if old_char.photo_path() != self.photo_path() and os.path.exists(old_char.photo_path()):
                shutil.move(old_char.photo_path(), self.photo_path())     

            super(Character, self).save(*args, **kwargs)

        else:
            # Set up a bunch of related objects that must be in sync
            # Supposedly this is bad practice (saving related objects within this model's save)
            # But it seems to me like this is the natural place for it, to ensure that all callers do it right without having to worry about it.

            # Complicated song and dance to save the circular reference between first_name and character.
            # 1. disconnect them, to avoid trying to save character with unsaved related object.
            first_name_obj = self.first_name_obj
            self.first_name_obj = None
            # 2. save the character, so that it has a pk.
            super(Character, self).save(*args, **kwargs)
            # 3. save the first_name_obj, so that it has a pk.
            first_name_obj.character = self
            first_name_obj.save(*args, **kwargs)
            # 4. reconnect the first_name_obj field.
            self.first_name_obj = first_name_obj
            self.save(*args, **kwargs)

            # Make blank stats for new characters.
            # Stats are changed through their own forms, so we don't need to save them when we modify the character.
            for cst in self.game.character_stat_types.all():
                new_stat = CharacterStat(character=self, stat_type=cst)
                new_stat.save()

    def stats_dict(self, exclude_blank_optional=True):
        """
        :param exclude_blank_optional: Include optional stats where my value is the empty string?
        :return: my stats as a dict. {'Age': '40', 'MP': '12'}
        """
        dic = {}
        stat_objs = self.stats.all()
        for s in stat_objs:
            if exclude_blank_optional and s.value == "" and s.stat_type.optional: continue
            dic[s.stat_type.name] = s.value
        return dic

    def set_stat(self, stat_name, value):
        """
        Set my stat by stat_name.
        stat_name had better be the name of a CharacterStat corresponding to this game.
        """
        stat_obj = CharacterStat.objects.get(character=self, stat_type__name=stat_name)
        stat_obj.value = value
        stat_obj.save()

    def set_stats_from_dict(self, dict):
        """
        Set my stats from a dictionary, like the output of self.stats_dict.
        Will have trouble if a stats name doesn't match.
        """
        for name in dict:
            self.set_stat(name, dict[name])

    def cast(self):
        """
        Note that there is an unfortunate confusion with the word 'cast.'
        This is the programming casting to subclass, not the LARP assigning a player.

        There are three tables in the database:
            Character, PlayerCharacter, and NonPlayerCharacter
        If you get out a Character from the Character table, you have only got a Character instance, not a PlayerCharacter or NonPlayerCharacter
        You have to manually call character.cast() to cast down to the subclass.

        """
        if self.char_type == "PC":
            return self.playercharacter
        elif self.char_type == "NPC":
            return self.nonplayercharacter
        else:
            raise ValueError("invalid type: " + self.char_type)

    # Here we define a bunch of methods that would be automatically overridden
    # Except for the problem described in the docstring of the Character.cast function
    def gender(self):
        return self.cast().gender()

    def photo_url(self):
        return self.cast().photo_url()

    def clone(self, new_game):
        return self.cast().clone(new_game)

    def homepage_url(self):
        return self.cast().homepage_url()

    def photo_path(self):
        if self.char_type == "PC":
            path = self.cast().getuploadpath()
        elif self.char_type == "NPC":
            path = npcuploadpath(self.cast())
        if path:
            return settings.MEDIA_ROOT + path
        else:
            return None


class PlayerCharacter(Character):
    # Remember that the user's actual username is username+game.usernamesuffix
    username = models.CharField(max_length=50, blank=True)
    password = models.CharField(max_length=50, blank=True)

    # LARPTextField lets it include gender switches and stuff.
    costuming_hint = LARPTextField(blank=True, default="")

    # User is a django-defined Model for an actual user who logs into the website.
    # Every PlayerCharacter has one; it just has a username and password and can be authenticated.
    user = models.OneToOneField(User, related_name='character', default=None, null=True, on_delete=models.SET_NULL)
    sheets = models.ManyToManyField(Sheet, related_name='characters', blank=True)
    default_gender = models.CharField(max_length=2, choices=(("M", "Male"), ("F", "Female")), default="M")

    # Other things that are like fields that you should remember:
    # Character.contacts (the queryset of Contact objects that represent who this guy knows)
    # Character.stats (the queryset of CharacterStat objects that represent this guys' stats)


    @property
    def player_cast(self):
        """
        :return: (Boolean) Is there a player cast to this character?
        """
        try:
            p = self.PlayerProfile
            if p is not None:
                return True
        except ObjectDoesNotExist:
            return False

    def delete(self, *args, **kwargs):
        # Have to delete the user too.
        u = self.user
        super(PlayerCharacter, self).delete(*args, **kwargs)
        u.delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # If save got called because we made a new character, make a new user too.
        if self.user is None:
            self.user = self.make_new_user()

        # set the users username and password.
        u = self.user
        u.username = self.full_username
        u.set_password(self.password)
        u.first_name = self.first_name()
        u.last_name = self.last_name
        u.save()

        # I'm a PC!
        self.char_type = "PC"
        super(PlayerCharacter, self).save(*args, **kwargs)

    def clone(self, new_game):
        """
        For when GameInstances want to clone.
        This clones the character and attaches it to the new_game.
        I think it's saving more than it has to? Because character.save() saves a lot too.
        """
        new = PlayerCharacter(first_name_obj=None, title_obj=self.title_obj, last_name=self.last_name, game=new_game,
                              username=self.username, password=self.password, costuming_hint=self.costuming_hint,
                              default_gender=self.default_gender)
        new.save_new(self.first_name_obj.clone(new, commit=False))

        for name in self.nonfirst_names():
            name.clone(new)

        return new


    def getuploadpath(self):
        # The path to which my player_photo is uploaded.
        # Its a little weird that this calls playerprofile which then calls playerprofile.character.
        # That could be improved.
        if self.player_cast:
            return playerprofileuploadpath(self.PlayerProfile)
        else:
            return None

    def photo_url(self):
        """
        :return: The url to find my photo at, for use in links in templates.
        """
        if self.player_cast:
            return self.PlayerProfile.photo_url()
        else:
            return settings.STATIC_URL + 'garhdony_app/blank_photo.png'

    def homepage_url(self):
        return reverse('character_home', args=[self.game.name, self.username])

    def make_new_user(self):
        new_user = User.objects.create_user(self.full_username, None, self.password)
        return new_user

    @property
    def full_username(self):
        return self.username + self.game.usernamesuffix

    def gender(self):
        if self.player_cast:
            p = self.PlayerProfile
            return p.gender
        else:
            return self.default_gender


def npcuploadpath(npc, filename=''):
    # Where NPC player_photos get uploaded to.
    # This morally belongs in the NonPlayerCharacter class, but can't be there because of something about migrations.
    return npc.game.photos_directory + npc.first_name()

class NPCManager(models.Manager):
    """
    This ensures that we only load the content when it's actually needed,
    by making the default queryset use "defer(content'). So content is only pulled from the database when needed."
    """
    use_for_related_fields = True
    def get_queryset(self):
        return super(NPCManager, self).get_queryset().defer('notes')

class NonPlayerCharacter(Character):
    # Notes are for writers to keep notes.
    notes = LARPTextField(blank=True, default="")
    objects = NPCManager()
    photo = models.ImageField(upload_to=npcuploadpath, blank=True, null=True, storage=DogmasFileSystemStorage())
    gender_field = models.CharField(max_length=2,
                                    choices=(("M", "Male"), ("F", "Female"), ("OP", "Opposite of"), ("EQ", "Same as"),),
                                    default="M")
    gender_linked_pc = models.ForeignKey(PlayerCharacter, related_name="gender_linked_npcs", blank=True, null=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        self.char_type = 'NPC'
        super(NonPlayerCharacter, self).save(*args, **kwargs)

    def homepage_url(self):
        return reverse('writing_npc', args=[self.game.name, self.id])

    def gender(self):
        if self.gender_linked_pc is None:
            return self.gender_field
        else:
            linked = self.gender_linked_pc.gender()
            if self.gender_field == "EQ":
                return linked
            elif self.gender_field == "OP":
                return utils.other_gender(linked)
            else:
                # Really shouldn't get here if everything is going smoothly;
                # if gender_field is M or F, then gender_linked_pc should be None.
                return self.gender_field

    def clone(self, new_game):
        """Makes a new copy. A lot of this code is repeated from the PC class and could be abstracted."""
        new = NonPlayerCharacter(first_name_obj=None, title_obj=self.title_obj, last_name=self.last_name, game=new_game,
                                 notes=self.notes, gender_field=self.gender_field, photo=self.photo)
        new.save_new(first_name_obj=self.first_name_obj.clone(new, commit=False))
        for name in self.nonfirst_names():
            name.clone(new)
        if os.path.exists(self.photo_path()):
            shutil.copy(self.photo_path(), new.photo_path())
        return new

    def photo_url(self):
        if self.photo:
            return settings.MEDIA_URL + npcuploadpath(self)
        else:
            return settings.STATIC_URL + 'garhdony_app/blank_photo.png'


class CharacterStatType(models.Model):
    """A Game has a few of these, like 'Age' and 'Patron' and 'MP'"""

    class Meta:
        ordering = ['name']

    game = models.ForeignKey(GameInstance, related_name="character_stat_types", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    # optional=True means PCs don't need to have it.
    optional = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If we're making a new one, make a blank instance of it for all PCs.
        if self.pk:
            change = True
        else:
            change = False

        super(CharacterStatType, self).save(*args, **kwargs)

        if not change:
            for c in self.game.characters.all():
                new_stat = CharacterStat(stat_type=self, character=c)
                new_stat.save(*args, **kwargs)


class CharacterStat(models.Model):
    """
    A stat of a character, like Hajdu's patron is 'Zofiya'
    Has a stat_type (patron), character (Hajdu), and value (Zofiya)
    """

    class Meta:
        ordering = ['stat_type']

    stat_type = models.ForeignKey(CharacterStatType, on_delete=models.RESTRICT)
    character = models.ForeignKey(Character, related_name="stats", on_delete=models.CASCADE)
    value = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return self.stat_type.name + "(" + self.character.first_name() + ")"


class GameInfoLink(models.Model):
    """
    An external link for putting in the sidebar
    """
    game = models.ForeignKey(GameInstance, related_name="info_links", on_delete=models.CASCADE)
    label = models.CharField(max_length=50)
    link_url = models.CharField(max_length=200)

    def __str__(self) -> str:
        return f'{self.label} ({self.game.name})'


class LogisticalTask(models.Model):
    """
    To be honest i haven't touched logistics in a year. 4/14
    """
    forms_choices = (('confirmation', 'confirmation'), ('photo', 'photo'), ('pregame_party', 'pregame_party'),
                     ('travel_survey', 'travel_survey'), ('housing_survey', 'housing_survey'),)
    name = models.CharField(max_length=50)
    display_text = models.CharField(max_length=400, blank=True)
    deadline = models.DateField(blank=True)
    form_type = models.CharField(max_length=30, blank=True, choices=forms_choices)
    sort_order = models.IntegerField()
    page_text = models.TextField(blank=True)

    def __str__(self):
        return self.name


def playerprofileuploadpath(pp, filename=''):
    """
    Again, this shoud be inside PlayerProfile, but can't because of migrations something something.
    It's the path to which the player's photo gets uploaded.
    """
    return pp.character.game.photos_directory + pp.character.first_name()  # + '_'+filename


class PlayerProfile(models.Model):
    """
    A PlayerProfile is an actual player, like Matt Steele.
    It is tied inextricably to a particular character.
    In the distant future we might want to loosen that tie, so players can play multiple games.
    It has:
       name ('Matt Steele')
       gender ('M')
       character (Klars)
       picture
       various logistics stuff
    """
    name = models.CharField(max_length=50)
    gender_options = (('M', 'M',), ('F', 'F',),)
    # TODO: Do we want to handle non-gender-normativity in some acceptable way?
    gender = models.CharField(max_length=1, choices=gender_options, default='M')
    character = models.OneToOneField(PlayerCharacter, related_name='PlayerProfile', blank=True, null=True, on_delete=models.SET_NULL)
    done_tasks = models.ManyToManyField(LogisticalTask, related_name='Players', blank=True, null=True)  # null=True is totally unnecessary, but removing it once the database is set up breaks the database. Update: tried again in 2023, still critical Null
    picture = models.ImageField(upload_to=playerprofileuploadpath, blank=True, storage=DogmasFileSystemStorage())
    email = models.CharField(max_length=100, blank=True,
                             verbose_name=b"What email address can we give to other players for contacting you?")
    pregame_party_rsvp = models.BooleanField(verbose_name=b"Will you be attending?", null=True)
    snail_mail_address = models.CharField(max_length=300, blank=True,
                                          verbose_name=b"If not, give us a snail mail address to send your packet to.")
    housing_comments = models.TextField(blank=True,
                                        verbose_name=b"Do you have any dietary restrictions? Any other notes on food or housing? For example, 'I really want a bed to myself' or 'It's very important to me that I get my own room' (that last one is hard to accommodate in our setup).  Please note that most people will be sleeping on airbeds; if this is a problem, please elaborate.")
    dietary_restrictions = models.CharField(max_length=200, blank=True,
                                            verbose_name=b"Do you have any dietary restrictions? Any snack preferences?")
    other_housing = models.TextField(blank=True,
                                     verbose_name=b"Any other notes on food or housing? For example, 'I really want a bed to myself' or 'It's very important to me that I get my own room' (that last one is hard to accommodate in our setup).  Please note that most people will be sleeping on airbeds; if this is a problem, please elaborate.")

    def __str__(self):
        return self.name

    def confirmed(self):
        return LogisticalTask.objects.get(name='confirmed_playing') in self.done_tasks.all()

    def confirm_playing(self):
        self.done_tasks.add(LogisticalTask.objects.get(name='confirmed_playing'))
        self.save()

    def photo_url(self):
        if LogisticalTask.objects.get(name='photo') in self.done_tasks.all():
            return settings.MEDIA_URL + playerprofileuploadpath(self)
        else:
            return settings.STATIC_URL + 'garhdony_app/blank_photo.png'


class TravelProfile(models.Model):
    # Every PlayerProfile has a TravelProfile.
    # This will get improved when we revamp logistics.
    player_profile = models.OneToOneField(PlayerProfile, related_name='TravelProfile', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name=b"Cell Phone Number", blank=True)
    departure_location = models.TextField(verbose_name='Where will you be leaving from?')
    departure_time = models.TextField(verbose_name='What time will you be ready to leave?')
    car_choices = (
        ("has car", "I own a car and can help drive others up (we'll reimburse expenses + some wear and tear)"),
        ("personal car", "I own a car but will only drive myself"),
        ("can rent", "I don't own a car, but I am at least 25 and willing to rent a car (we will pay, of course)"),
        ("can rent under 25", "I don't own a car, but I am under 25 and willing to drive someone else's car"),
        ("can't drive", "I cannot or do not want to drive"),)
    car_status = models.CharField(max_length=200, choices=car_choices, verbose_name=b"What is your car status?")
    dinner_choices = (("going", "I'll come to dinner to share stories!"), ("can't", "I need to be back early."),)
    # Dinner Status might get removed.
    dinner_status = models.CharField(max_length=200, choices=dinner_choices,
                                     verbose_name=b"Do you think you'll come to the wrap-up dinner on Sunday, or go straight home?")
    other = models.TextField(verbose_name=b"Any other travel information?", blank=True)

    def __str__(self):
        return self.player_profile.name


class Contact(models.Model):
    # A contact contains the info associated with "Hajdu knows Berlo"
    owner = models.ForeignKey(Character, related_name="contacts", on_delete=models.CASCADE)
    target = models.ForeignKey(Character, related_name="contacters", on_delete=models.CASCADE)

    # description and display_name are the things the player sees.
    description = LARPTextField(blank=True)
    display_name = LARPTextField()

    # The owner's contacts are listed sorted by the order_number field.
    # Writers can edit this to optimize the semantic ordering.
    order_number = models.IntegerField(default=0)

    def __str__(self):
        return str(self.owner) + "  ->  " + str(self.display_name)

    @property
    def game(self):
        # We need one of these for render_editable_page to have the right automatic behavior;
        # see forms_game_design.EditingFieldFormClassGeneric
        return self.owner.game


class TimelineEvent(models.Model):
    # An event in the timeline
    game = models.ForeignKey(GameInstance, related_name="timeline_events", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    date = models.DateField()
    default_description = models.TextField()
    characters = models.ManyToManyField(PlayerCharacter, through="TimelineEventCharacterDescription")

    def __str__(self):
        return self.name


class TimelineEventCharacterDescription(models.Model):
    class Meta:
        unique_together = ("event", "character")

    event = models.ForeignKey(TimelineEvent, related_name="descriptions", on_delete=models.CASCADE)
    character = models.ForeignKey(PlayerCharacter, related_name="event_descriptions", on_delete=models.CASCADE)
    unique_description = models.TextField(blank=True)

    def __str__(self):
        return self.event.name + " (" + self.character.name() + ")"

    @property
    def description(self):
        if self.unique_description == "":
            return self.event.default_description
        else:
            return self.unique_description


def setup_database():
    """
    This is an old thing that we used at the very start,
    when we were so incompetent that we frequently destroyed
    and remade the database. It had better not be needed anymore.
    But I don't have the guts to remove it.
    """
    w = Group(name="Writers")
    w.save()

    cs = SheetColor(name="Yellowsheet", color='000000', sort_order=0,
                    description="A yellow sheet goes only to you.")
    cs.save()

    bs = SheetColor(name='Bluesheet', color='0000AA', sort_order=-10,
                    description="A bluesheet goes to every reasonably educated person.")
    bs.save()

    gs = SheetColor(name='Greensheet', color='00AA00', sort_order=10,
                    description="A greensheet goes to a group.")
    gs.save()

    story = SheetType(name='Story', sort_order=1,
                      description="A story sheet tells the main story.")
    story.save()

    details = SheetType(name='Details', sort_order=2,
                        description="A details sheet provides more details.")
    details.save()

    supplement = SheetType(name='Supplement', sort_order=3,
                           description="A Supplement Sheet is supplementary.")
    supplement.save()

    igd = SheetColor(name='In-game Document', color='000000', sort_order=30,
                     description="An in-game document is a piece of paper your character has.")
    igd.save()
