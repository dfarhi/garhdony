from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
import garhdony_app.auth as auth
from garhdony_app.forms_game_design import ContactEditingFieldFormClass, CharacterEditingFieldForm, SheetEditingFieldForm
from garhdony_app.models import SheetColor
from garhdony_app.views_editable_pages import editable_page_update_args, render_editable_page
from django.utils.safestring import mark_safe
from sendfile import sendfile
from django.core.exceptions import ObjectDoesNotExist
import logging
logger = logging.getLogger(__name__)
import os
import urllib

def character_home(request, run_name, username):
    """
    The character's homepage, viewed either by a player
    or by a writer (who can edit stuff).

    This uses the editable_page abstraction from views_editable_pages.py.
    """
    def render_character_home(game, writer, character):
        """
        This is a little confusing because it's breaking an abstraction barrier.
        Normally editable_pages use the render_editable_page function, which magically deals with
        making fields editable by writers.

        This is almost render_editable_page(request, 'garhdony_app/character_home.html', render_character_homepage args, etc)

        But it wants to deal with preview mode, which is more complicated.
        """
        # TODO: Use the render_editable_page abstraction correctly.
        new_args = editable_page_update_args(request, writer, CharacterEditingFieldForm, character)

        if writer and request.method == 'GET' and 'override_preview' in request.GET:
            override_preview = request.GET['override_preview']=="True"
        else:
            override_preview=True
        if new_args == "SAVED":
            return HttpResponseRedirect(reverse("character_home", args=[game.name, character.username]))
        else:
            return render_character_homepage(request, game, character, writer=writer, extra_args={},override_preview = override_preview).add(new_args) #Something really weird happens when you leave the extra_args={} out. You'd think it wouldn't matter, since that's the default value, but somehow it does.

    return auth.authenticate_resolve_and_callback(request, render_character_home, run_name, username)


def render_character_homepage(request, game, character, writer=False, extra_args={}, override_preview=True):
    warnings = []
    if writer:
        all_sheets = character.sheets.all()
    else:
        all_sheets = character.sheets.exclude(hidden=True)
    if game.preview_mode:
        if writer:
            if override_preview:
                warnings += [mark_safe("This game is in preview mode. You are viewing what the player will see when preview mode is turned off. View what they currently see <a href="+character.homepage_url()+"?override_preview=False"+">here</a>.")]
            else:
                warnings += [mark_safe("This game is in preview mode. You can see the player's homepage when preview mode is turned off <a href="+character.homepage_url()+"?override_preview=True"+">here</a>.")]
        if not writer or not override_preview:
            return auth.callback_package('garhdony_app/character_home_preview.html', {'sheets':all_sheets, 'here':'Character Sheets', 'warnings':warnings})
    all_sheets = all_sheets
    args = splitup_sheets(all_sheets)
    args['here'] = 'Character Sheets' # here is the arg that tells the tabs at the top which is selected.
    if not 'warnings' in extra_args:
        extra_args['warnings'] = []
    extra_args['warnings'] += warnings
    args.update(extra_args)
    return auth.callback_package('garhdony_app/character_home.html', args)

def splitup_sheets(sheets):
    """
    Splits a list of sheets by type.
    :param sheets: A list of sheets (probably that a particular character has)
    :return: A dictionary of sheets by type, for passing to a template.
    """
    ps = sorted(sheets.filter(sheet_type__name='Public Sheet'), key=lambda x: x.name.render_for_user(writer=False))
    igds = sorted(sheets.filter(sheet_type__name='In-Game Document'), key=lambda x: x.name.render_for_user(writer=False))
    s = sheets.exclude(sheet_type__name='Public Sheet').exclude(sheet_type__name="In-Game Document").order_by('sheet_type')
    all_colors = sorted(SheetColor.objects.all(), key=lambda x: x.sort_order)
    return {'sheets':s, 'public_sheets':ps, 'all_colors':all_colors, 'in_game_documents':igds}

def character_contacts(request, run_name, username):
    def render_contacts(game, writer, character):
        return render_editable_page(request, 'garhdony_app/character_contacts.html', {'here':'Contacts'}, (lambda: reverse("character_contacts", args=[game.name, character.username])), writer, ContactEditingFieldFormClass, character)
    return auth.authenticate_resolve_and_callback(request, render_contacts, run_name, username)

def past_player_all_sheets(request, run_name, username):
    """
    Shows past players all sheets if game.complete is True.
    """
    def render_all_sheets(game):
        allsheets = game.sheets.all()
        args = splitup_sheets(allsheets)
        args['here'] = 'All Sheets' # here is the arg that tells the tabs at the top which is selected.
        return auth.callback_package('garhdony_app/all_sheets.html', args)

    def deny_all_sheets(game):
        #For if people try to go here before the game is done.
        return auth.callback_package('garhdony_app/deny_all_sheets.html', {'here':'All Sheets'})

    def player_all_sheets(game, writer, character):
        if game.complete:
            return render_all_sheets(game)
        else:
            return deny_all_sheets(game)
    return auth.authenticate_resolve_and_callback(request, player_all_sheets, run_name, username)

def character_sheet(request, run_name, username, sheet_name):
    """
    View of a sheet from a character's point of view.
    Can be seen by writers or players.

    Calls the general view_sheet method for the actual view, since that's the same whoever views it.
    """
    def serve_sheet(game, writer, character):
        # TODO This could use the 'sheet' argument to authenticate_resolve_and_callback?
        # Check that this character has this sheet, and if so view it.
        visible_sheets = list(character.sheets.all())
        sheets = [sheet for sheet in visible_sheets if sheet.name.render()==sheet_name]
        assert(len(sheets)==1)
        sheet = sheets.pop()
        redir = lambda: reverse("character_sheet", args=[game.name, character.username, sheet.name])
        return view_sheet(request, sheet, writer, redir)
    return auth.authenticate_resolve_and_callback(request, serve_sheet, run_name, username)

def past_player_sheet(request, run_name, username, sheet_filename):
    """
    View of a sheet as a past player.
    The sheet had better belong to the game.

    Calls the general view_sheet method for the actual view, since that's the same whoever views it.
    """
    def serve_sheet(game, writer, character):
        # TODO This could use the 'sheet' argument to authenticate_resolve_and_callback?
        if game.complete:
            visible_sheets = game.sheets.all()
            sheet = visible_sheets.get(filename=sheet_filename)
            return view_sheet(request, sheet, writer, (lambda: reverse("past_player_sheet", args=[game.name, character.username, sheet.filename])))
        else:
            raise Http404
    return auth.authenticate_resolve_and_callback(request, serve_sheet, run_name, username)

def view_sheet(request, sheet, writer, redirect, revision_pk=None, more_args={}):
    """
    The actual view of a sheet.

    Checks to se what the format argument is, and renders it in that format.
    :param sheet: A Sheet object
    :param writer: boolean is the user a writer?
    :param redirect:
    :param revision_pk: For writers, if this is not None it will render that revision. (Default is to always render the last_revision, of course.)
    """
    logger.debug("Starting view_sheet")

    # Figure out what revision to display.
    if revision_pk:
        revision = sheet.revisions.get(pk=revision_pk)
    else:
        revision = sheet.current_revision

    # Figure out the format.
    if request.method=="GET" and 'format' in request.GET:
        format = request.GET['format']
    else:
        # For writers, default to html so they can edit the sidebar. For non-writers, if the sheet is pdf or png, default to file download.
        # TODO: Let players get kindle version?
        if sheet.get_content_type_display()=='html' or (writer and sheet.current_revision==revision):
            format = "html"
        else:
            format = "file"
    # Make sure there's a real sheet there.
    if not sheet:
        raise Http404

    if format=="html":
        # Render the usual html view.

        warnings = []
        if sheet.current_lock() and sheet.current_lock().author == request.user:
            warnings += ["You have this sheet locked for editing in another tab. Click the lock icon in the corner to release your lock."]

        args = {'sheet':sheet, 'revision':revision, 'warnings':warnings}
        args.update(more_args)
        return render_editable_page(request, 'garhdony_app/sheet.html', args, redirect, writer, SheetEditingFieldForm, sheet)

    elif format=="file":
        if sheet.content_type=='html':
            # Send the PDF
            # This uses sendfile, which is a thingamajig we downloaded, to send it using Apache rather than django.
            # The file must already have been generated, which happens whenever the sheets print_to_file method is called.
            location = sheet.full_path
        else:
            #Getting the file for a file-based sheet.
            if revision is not None:
                # revision is None if the sheet has no revisions.
                # This should only happen for old sheets that predate revisions on file-sheets.
                location = revision.fullfilepath
            else:
                location = sheet.full_path
        if not os.path.exists(location):
            # Try seeing if its an old file which is stored not in a revision, or
            # Try seeing if it didn't have the .pdf part.
            no_extension_location = sheet.full_path.split('.')[0]
            old_location = sheet.full_path
            if os.path.exists(old_location):
                location = old_location
            elif os.path.exists(no_extension_location):
                location = no_extension_location
            else:
                raise ValueError("Can't find file!")
        response = sendfile(request, location)
        return response

    elif format == "plain":
        # Render the plain html version.
        return auth.callback_package('garhdony_app/sheet_plain.html', {'revision':revision})

    else:
        raise ValueError("Invalid format: " + str(format))
