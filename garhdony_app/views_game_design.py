from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse, JsonResponse
from garhdony_app.views_editable_pages import render_editable_page
from garhdony_app.models import GameInstance, SheetRevision, NonPlayerCharacter, Contact, Sheet, PlayerCharacter
from garhdony_app.forms_users import writer_home_form_getter
from garhdony_app.forms_game_design import NPCEditingForm, CharacterNewForm, CharacterDeleteForm, SheetNewForm, SheetDeleteForm,  NewTitleForm, GameCreationForm, GameCloneForm, GameEditingForm, SearchForm
import garhdony_app.utils as utils
import garhdony_app.auth as auth
from django.core.exceptions import ObjectDoesNotExist
from garhdony_app.views_characters import view_sheet
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.utils.html import escape
import logging
import re
from datetime import datetime
from django.utils.safestring import mark_safe
logger = logging.getLogger(__name__)

#######################################################
########### Stuff That's Not Game-Specific ###########
#######################################################

def writing_home(request):
    def render_home():
        all_games = GameInstance.objects.all()
        if request.user.is_staff:
            my_games = all_games
        else:
            my_games = [g for g in all_games if request.user.has_perm("garhdony_app.writer", g)]

        # List the 5 most recent sheets I've edited.
        # Maybe it would be better to list most recent sheets anyone has edited?
        my_revisions = list(SheetRevision.objects.filter(author=request.user).order_by("-created")[:100]) # Only take 100 for speed. If you've edited the same sheet 100 times, too bad.
        recent_sheets = utils.remove_duplicates(my_revisions, 5, lambda r: r.sheet)
        return render_editable_page(request, 'garhdony_app/writing_home.html', {'games':my_games, 'writer':True, 'recent_sheets':recent_sheets},
                                    lambda: reverse("writer_home"), True, writer_home_form_getter, request.user)
    return auth.authenticate_and_callback(request, render_home, requires_writer=True)


def writing_new_game(request):
    """
    Lets users make a new game.
    The page has two different forms:
        A CloneForm (see models.GameInstance.clone() for the philosophy)
        A CreationForm (normal game creation)
    It detects which was POSTed and saves that one.
    """
    def render_writing_new():
        if request.method == 'POST':
            if "Create" in request.POST:
                form = GameCreationForm(request.user, data=request.POST)
            elif "Clone" in request.POST:
                form = GameCloneForm(request.user, data=request.POST)
            else:
                raise ValueError("Invalid submit")
            if form.is_valid():
                form.save()
                name = form.instance.name
                return HttpResponseRedirect(reverse("game_writer_home", args=[name]))
            else:
                raise ValueError("Invalid Form. TODO: Make this handle errors the normal way.")
        else:
            new_form = GameCreationForm(request.user)
            clone_form = GameCloneForm(request.user)
            return auth.callback_package('garhdony_app/writing_new_game.html',{'new_form':new_form, 'clone_form':clone_form, 'writer':True})
    return auth.authenticate_and_callback(request, render_writing_new, requires_writer=True)

#######################################################
######### Things on the writer's left sidebar #########
#######################################################

def writing_game_home(request, game_name):
    """
    Game writing homepage, with a list of characters and a list of sheets.
    """
    def render_writing_game_home(game, writer):
        return render_editable_page(request, 'garhdony_app/writing_game_home.html', {'sheets':game.sheets.all(),'characters':game.characters.all()}, lambda: reverse("game_writer_home", args=[game.name]), writer, GameEditingForm, game)
    return auth.authenticate_resolve_and_callback(request, render_writing_game_home, game_name, requires_writer = True)


def writing_game_sheets_grid(request, game_name):
    """
    The grid of characters and sheets.
    """
    def render_writing_game_sheets_grid(game, writer):
        logger.debug(str(datetime.now())+": Loading Sheets Grid!")
        return auth.callback_package('garhdony_app/writing_game_sheets.html', {'characters':list(game.pcs()), 'sheets':game.sheets.all()})
    return auth.authenticate_resolve_and_callback(request, render_writing_game_sheets_grid, game_name, requires_writer = True)

def sheets_grid_modify(request, game):
    """
    AJAX for modifying a sheet-character matching.
    """
    def render_sheets_grid_modify(game, writer):
        if request.method == 'POST':
            sheetID = request.POST.get('sheet')
            characterID = request.POST.get('character')
            sheet = Sheet.objects.get(pk=sheetID)
            character = PlayerCharacter.objects.get(pk=characterID)
            if sheet in character.sheets.all():
                character.sheets.remove(sheet)
            else:
                character.sheets.add(sheet)
            character.save()
            logger.debug(str(datetime.now())+": Modified!")
            return JsonResponse({})
        else:
            return JsonResponse({})
    return auth.authenticate_resolve_and_callback(request, render_sheets_grid_modify, game, requires_writer = True)

def writing_characters_table(request, run_name):
    # A sortable table of all the characters
    # Uses a javascript thing from the internet for a sortable table.
    def render_table(game, writer):
        # The template needs a list-of-lists with one row per character and one entry per stat.
        special_stats = ['Title','First','Last','Gender','Player']
        def specials_list(character):
            """
            Get the irregular stats of a character
            (the regular ones are things like Age and MP which are defined by CharacterStat objects)
            """
            gender = character.gender()
            if character.char_type == "NPC":
                player = "[NPC]"
            else:
                try:
                    player = character.cast().PlayerProfile.name
                except ObjectDoesNotExist:
                    player = "[uncast]"
            name_link = mark_safe("<a href=%(link)s>%(name)s</a>"%{'name':character.first_name(), 'link':character.homepage_url()})
            return [character.title(),name_link,character.last_name,gender,player]
        character_objects = game.characters.all()
        stats = list(game.character_stat_types.all())
        stats_names = special_stats + [s.name for s in stats]

        # Assemble the list-of-lists
        # if stats_names is like ['Title', 'First', 'Last','Gender','Player','Age','MP']
        # then character_lists will wind up being like:
        #   [['Sir', 'Nicalao', 'Gazpahr', 'M', 'Paul Hlebowitsch', '68', ''],
        #    ['Archmage', 'Adorran', 'Salom', 'M', 'Jayson Lynch', '55', '16'],
        #    ...]
        character_lists = []
        for character in character_objects:
            stats_dict = character.stats_dict(exclude_blank_optional=False)
            character_lists.append(specials_list(character)+[stats_dict[s.name] for s in stats])

        return auth.callback_package('garhdony_app/characters_table.html', {'listized_characters':character_lists, 'stats':stats_names})
    return auth.authenticate_resolve_and_callback(request, render_table, run_name, requires_writer = True)


def recent_changes(request, run_name):
    # A list of previous changes. Based on the history view but somehow global.
    def render_recent_changes(game, writer):
        if 'page' in request.GET:
            page = int(request.GET['page'])
        else:
            page = 0
        count_per_page = 20
        history = SheetRevision.objects.filter(sheet__game=game).order_by('-created')[page*count_per_page:(page+1)*count_per_page]
        page_max = len(SheetRevision.objects.filter(sheet__game=game))
        attrs = {'history': history, 'game': game}
        if page < page_max:
            attrs['has_next'] = True
            attrs['next'] = page+1
        if page > 0:
            attrs['has_prev'] = True
            attrs['prev'] = page-1
        return auth.callback_package('garhdony_app/game_history.html', attrs)
    return auth.authenticate_resolve_and_callback(request, render_recent_changes, run_name, requires_writer = True)
                
def writing_game_timeline(request, game_name):
    """
    The grid of events and characters.
    """
    def render_writing_game_timeline(game, writer):
        logger.debug(str(datetime.now())+": Loading Timelins")
        return auth.callback_package('garhdony_app/writing_game_timeline.html', {'characters':list(game.pcs()), 'events':game.timeline_events.all()})
    return auth.authenticate_resolve_and_callback(request, render_writing_game_timeline, game_name, requires_writer = True)


#######################################################
####### Creating/Deleting Sheets and Characters #######
#######################################################

# TODO: These could probably be significantly simplified with django's new generic views: DeleteView and CreateView
def writer_new_sheet(request, run_name):
    def render_new_sheet(game, writer):
        if request.method == 'POST':
            form = SheetNewForm(request.POST)
            if form.is_valid():
                s = form.save(game)
                return HttpResponseRedirect(reverse("writer_sheet", args=[game.name, s.filename]))
            else:
                return auth.callback_package('garhdony_app/writing_new_sheet.html', {'form':form})

        else:
            f = SheetNewForm()
            return auth.callback_package('garhdony_app/writing_new_sheet.html', {'form':f})

    return auth.authenticate_resolve_and_callback(request,render_new_sheet, run_name, requires_writer = True)


def delete_sheet(request, run_name):
    def render_del_sheet(game, writer):
        if request.method == 'POST':
            form = SheetDeleteForm(game, data=request.POST)
            if form.is_valid():
                s = form.cleaned_data['sheet']
                s.delete()
                return HttpResponseRedirect(reverse("game_writer_home", args=[game.name]))
        else:
            form = SheetDeleteForm(game)
        return auth.callback_package('garhdony_app/delete_sheet.html', {'form':form})
    return auth.authenticate_resolve_and_callback(request, render_del_sheet, run_name, requires_writer = True)


def new_character(request, run_name):
    def render_new_character(game, writer):
        if request.method == 'POST':
            form = CharacterNewForm(request.POST)
            if form.is_valid():
                char = form.save(game)
                if char.char_type=="PC":
                    redir = reverse("character_home", args=[game.name, char.username])
                else:
                    redir = reverse("writing_npc", args=[game.name, char.id])
                return HttpResponseRedirect(redir)
            else:
                return auth.callback_package('garhdony_app/writing_new_character.html', {'form':form})

        else:
            f = CharacterNewForm()
            return auth.callback_package('garhdony_app/writing_new_character.html', {'form':f})
    return auth.authenticate_resolve_and_callback(request, render_new_character, run_name, requires_writer = True)


def delete_character(request, run_name):
    def render_del_char(game, writer):
        if request.method == 'POST':
            form = CharacterDeleteForm(game, data=request.POST)
            if form.is_valid():
                c = form.cleaned_data['character'].cast()
                c.delete()
                return HttpResponseRedirect(reverse("game_writer_home", args=[game.name]))
        else:
            form = CharacterDeleteForm(game)
        return auth.callback_package('garhdony_app/delete_character.html', {'form':form})
    return auth.authenticate_resolve_and_callback(request, render_del_char, run_name, requires_writer = True)

#######################################################
################### Viewing/Editing ###################
#######################################################

# character_home is in views_characters, since that can be viewed by both.


def writer_sheet(request, run_name, filename, revision_pk=None):
    """
    Viewing the sheet in 'Read' Mode
    """
    def render_writing_sheet(game, writer, sheet):
        game = sheet.game.name
        filename = sheet.filename
        return view_sheet(request, sheet, writer, (lambda: reverse("writer_sheet", args=[game, sheet.filename])), revision_pk, {'here':'Read'})
    return auth.authenticate_resolve_and_callback(request, render_writing_sheet, run_name, sheet=filename, requires_writer=True)


def writing_npc(request, game_name, npc_id):
    def render_writing_npc(game, writer):
        character =  NonPlayerCharacter.objects.get(id=npc_id)
        return render_editable_page(request, 'garhdony_app/writing_npc.html', {'character': character}, lambda: reverse("writing_npc", args=[game_name, npc_id]), writer, NPCEditingForm, character)
    return auth.authenticate_resolve_and_callback(request, render_writing_npc, game_name, requires_writer = True)


def character_contacts_delete(request, run_name, username):
    def render_delete(game, writer, character):
        if request.method != "POST":
            raise Http404 #Shouldn't ever get here.
        contact_id = request.POST['contact_id']
        contact = Contact.objects.get(id=contact_id)
        contact.delete()
        return HttpResponseRedirect(reverse('character_contacts', args=[run_name, username]))
    return auth.authenticate_resolve_and_callback(request, render_delete, run_name, username)



#######################################################
################# Adding Stuff Pop-up #################
#######################################################
# Should we use this more?

def handlePopAdd(request, addForm, field):
    # For popup adding of titles in character editing. Also abstractable to other analogous things.
    if request.method == "POST":
        form = addForm(request.POST)
        if form.is_valid():
            try:
                new_object = form.save()
            except ValidationError:
                new_object = None
            if new_object:
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' %(escape(new_object._get_pk_val()), escape(new_object)))
    else:
        form = addForm()

    page_context = {'form': form, 'field': field}
    return render(request, "garhdony_app/add_popup.html", page_context)


def add_title(request):
    return handlePopAdd(request, NewTitleForm, 'title_obj')

######################################################
####################### Search #######################
######################################################

def search(request, run_name):
    def render_search(game, writer):
        results = [];
        if request.method == "POST":
            form = SearchForm(request.POST)
            if form.is_valid():
                results = find_results(game, form)
        else:
            form = SearchForm()
        return auth.callback_package('garhdony_app/writing_game_search.html', {'form':form, 'hit_sheets':results})
    return auth.authenticate_resolve_and_callback(request, render_search, run_name, requires_writer = True)


def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

def find_results(game, form):#query, raw=False, matchcase=False, wholewords=True):
    terms = normalize_query(form.cleaned_data['query'])
    hits = []
    for sheet in game.sheets.filter(content_type='html'):
        if form.cleaned_data['raw']:
            text = sheet.current_revision.content.raw()
        else:
            text = sheet.current_revision.content.render()

        match = True
        for term in terms:
            if form.cleaned_data['wholewords']:
                regex = (r"\b"+term+r"\b")
            else:
                regex = term
            if form.cleaned_data['matchcase']:
                didnt_match = re.search(regex, text) is None
            else:
                didnt_match = re.search(regex, text, re.I) is None
            if didnt_match:
                match = False
                break
        if match:
            hits+=[sheet]
    return hits