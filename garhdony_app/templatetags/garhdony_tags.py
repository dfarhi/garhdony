"""
tags are things you can use in templates.

Put {% load garhdony_tags %} at the top of the template or they won't work.

There are three sections in this file:
1. Filters: These are functions that we can all use in all our templates and
    they will be super-helpful and we should write more of them.
2. Inclusion tags: These are tags that automatically include another small html file.
    Each of these is not so useful outside of the context for which it was written, I think?
3. The writable_field tag, which is useful for letting writers edit everything in the universe.
    Basically every writer page should be full of these.
"""

from django import template
from garhdony_app.models import GameInstance, EditLock
from garhdony_app.forms_users import DogmasAuthenticationForm
from django.urls import reverse
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# This is just some thing you're supposed to do at the top of your tags.py file.
register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

############################################################
###################### Simple Filters ######################
############################################################
# Filters are basically functions. You put "argument1|filtername:argument2".
# Don't ask me why. I think they want to discourage binary operations in filters?

def render_larpstring(ls, writer):
    # Renders a larpstring, resolving its gender-switches.
    return ls.render_for_user(writer)
register.filter("render_larpstring", render_larpstring)


@register.filter
def concat(arg1, arg2):
    return str(arg1) + str(arg2)

def edit_locks(user):
    # Lists all of a user's edit_locks.
    if not user.has_perm("garhdony_app.writer"):
        return []
    else:
        return EditLock.objects.filter(author=user, saved=False, broken=False)
register.filter("edit_locks", edit_locks)

def sheets_url(character):
    """ The URL for the character's main sheets page. """
    return reverse("character_home", args=(character.game.name,character.username,))
register.filter("sheets_url", sheets_url)

def logistics_url(character):
    """ The URL for the character's logistics page. """
    return reverse("character_logistics", args=(character.game.name,character.username,))
register.filter("logistics_url", logistics_url)

def contacts_url(character):
    """ The URL for the character's logistics page. """
    return reverse("character_contacts", args=(character.game.name,character.username,))
register.filter("contacts_url", contacts_url)

def all_sheets_url(character):
    """ The URL for a past player's view of all sheets in game. """
    return reverse("past_player_all_sheets", args=(character.game.name,character.username,))
register.filter("all_sheets_url", all_sheets_url)

def view_url(sheet):
    """ The URL for viewing this sheet as a writer. """
    return reverse("writer_sheet", args=(sheet.game.name,sheet.filename,))
register.filter("view_url", view_url)

def edit_url(sheet):
    """ The URL for editing this sheet as a writer. """
    return reverse("writer_sheet_edit", args=(sheet.game.name,sheet.filename,))
register.filter("edit_url", edit_url)

def history_url(sheet):
    """ The URL for this sheet's history as a writer. """
    return reverse("sheet_history", args=(sheet.game.name,sheet.filename,))
register.filter("history_url", history_url)

def game_blurb_url(game):
    return reverse("game_blurb", args=(game.name,))
register.filter("game_blurb_url", game_blurb_url)

def game_about_url(game):
    return reverse("game_about", args=(game.name,))
register.filter("game_about_url", game_about_url)

def game_how_to_app_url(game):
    return reverse("game_how_to_app", args=(game.name,))
register.filter("game_how_to_app_url", game_how_to_app_url)

#############################################################
################### Simple Inclusion Tags ###################
#############################################################
# inclusion_tags just include the snippet of html defined in the file, with the arguments returned by the function.

@register.inclusion_tag('logged_in_sidebar.html', takes_context=True)
def logged_in_sidebar(context):
    return {'user':context['user']}

@register.inclusion_tag('login_sidebar.html')
def login_sidebar(next):
    f = DogmasAuthenticationForm()
    return {'form': f, 'next':next}

@register.inclusion_tag('navbar.html', takes_context = True)
def navbar(context, here, *entries_and_urls):
    mapping = [(entries_and_urls[2*i], entries_and_urls[2*i+1]) for i in range(int(len(entries_and_urls)/2))]
    return {'entry_list':mapping, 'here':here, 'user':context['user']}

@register.inclusion_tag('garhdony_app/admin-sidebar.html')
def admin_sidebar(game):
    return {'game':game}

@register.inclusion_tag('garhdony_app/sheet_link.html')
def sheet_link(character, sheet, writer):
    return {'character':character, 'sheet': sheet, 'writer':writer}

@register.inclusion_tag('garhdony_app/sheet_list.html')
def sheet_list(character, sheets, writer):
    return {'character':character, 'sheets': sheets, 'writer':writer}


############################################################
###################### Writable_field ######################
############################################################

"""
This defines the writable_field tag. See almost any template that writers use for an example.

You use it like this:

    {% writable_field 'in-game_documents' %}
        [Header html that is always displayed
         Somewhere in here is {% edit_button "Edit me!" %} which displays the "Edit me!" button for writers to click.]
    {% display %}
        [Stuff that is displayed when we're not editing this field]
    {% edit %} <---optional
        [stuff to display when we are editing this field
         When editing this field there will be a 'edit_form' variable in the templates context.
         You can assume that the <form></form> and save-button stuff is already there;
         you just need to do things like "{{field1.label}}" with no preamble or postamble.
         If this is not present, it just displays the form.]
    {% end_writable_field %}

It needs one argument which is a string which names this field. This argument will be passed to the form constructor in
views_editable_pages.render_editable_page, letting it make an appropriate form.

Then it will listen to the following variables in the template:
    'editable_page'=True and 'writer'=True: enables the edit button.
    'editing' isn't present, then it will display the display mode.
    'editing'=[name], then it will display the edit view, assuming 'edit_form' is the form.
    'editing'=[something else], then some other writable_field is being edited, so the edit_button for this field
        is suppressed since we don't want to you editing this before you save your other edits.

"""


@register.tag(name="writable_field")
def do_writable_field(parser, token):
    """
    This is the parser that looks at the template and constructs a WritableFieldNode
    :param parser: A weird django thing. You use it by asking for
        parser.next_token() --- gives the next tag.
        parser.parse(stop_at_list) --- parses until it gets to somebody from stop_at_list
            it goes up until right before the match; the next_token() is then the one that caused the stop.
    :param token: the contents of the {% writable_field %} tag itself
    """


    # Get out the arguments that were given to the tag:
    bits = token.split_contents()
    name = bits[1] # This is the field name argument that we care about
    args = bits[2:] # These are ignored.

    logger.debug(str(datetime.now())+": Scanning Writable Field: " + name)

    # The stuff before the edit button is preamble_pre_edit
    preamble_pre_edit = parser.parse(("edit_button",))

    # edit_button_name is the name of the edit button, either supplied as an argument or defaulted to 'Edit'
    edit_token = parser.next_token()
    edit_token_contents = edit_token.split_contents()
    if len(edit_token_contents) > 1:
        edit_button_name = edit_token_contents[1]
    else:
        edit_button_name = "Edit"

    # The stuff between the edit button and the display tag is preamble_post_edit
    preamble_post_edit = parser.parse(("display",))

    # Get the display tag out of the way
    parser.delete_first_token()

    # display to edit is display_nodelist
    display_nodelist = parser.parse(("edit","end_writable_field",))

    # Figure out if we ended because of edit or end_writable_field
    token = parser.next_token()
    if token.contents=="edit":
        # If it was edit, edit_nodelist is the stuff for displaying while editing.
        edit_nodelist = parser.parse(("end_writable_field",))
        parser.delete_first_token()
    else:
        edit_nodelist = None    

    # Construct a WritableFieldNote out of all the pieces.
    return WritableFieldNode(preamble_pre_edit, preamble_post_edit,display_nodelist, edit_nodelist,name,edit_button_name)

class WritableFieldNode(template.Node):
    """
    This is constructed by do_writable_field.
    The goal of this class is the render() function, which decides what to display.

    If the template has been passed 'editable_page'=True and 'writer'=True, then it will display edit stuff
        Otherwise it will not to anything
    If 'editing'=[name], then it will display the edit view.
    If 'editing'=[something else], then some other writable_field is being edited, so the edit_button for this field
        is suppressed since we don't want to you editing this before you save your other edits.
    """
    def __init__(self, preamble_pre_edit, preamble_post_edit, display_nodelist, edit_nodelist, name,edit_button_name):
        self.preamble_pre_edit=preamble_pre_edit # header before edit button (always displays)
        self.preamble_post_edit=preamble_post_edit # header after edit button (always displays)
        self.display_nodelist = display_nodelist # display while not editing
        self.edit_nodelist = edit_nodelist # display while editing
        self.unresolved_name=name # The name, but it might have unevaluated variables; it might be "{{character}}"
        self.edit_button_name = edit_button_name # text for the edit button.
    def name(self, context):
        # Since unresolved_name might be "{{character}}", we want to resolve it to "Marika"
        # That's what this does.
        return template.Variable(self.unresolved_name).resolve(context)
    def edit_button(self, context):
        # The html of the edit button itself.
        # The hidden input tells the render_editable_page view what field was edited
        field_name = self.name(context)
        return f'<form action="#edit-{field_name}" id="edit-{field_name}" method="get" style="display:inline">' \
                    f'<input type="hidden" name="Edit" value="{field_name}">' \
                    f'<input class="edit_button" type="submit" value={self.edit_button_name}>' \
                f'</form>'
    def writer(self, context):
        # This looks in the templates context and decides if the user is a writer
            # (and thus we should display edit buttons).
        # If there's no variable editable_page=True, then we turn off editable_fields no matter what.
        editable_page = "editable_page" in context and  template.Variable("editable_page").resolve(context)
        writer_user =  template.Variable("writer").resolve(context)
        return editable_page and writer_user
    def editing(self, context):
        # Determines whether or not this field is being edited
        # This is set by the 'editing' value (if it's equal to this field's name, then we're editing).
        return "editing" in context and template.Variable("editing").resolve(context)==str(self.name(context))
    def render_edit_nodelist(self, context):
        # In edit mode, first put the universal <form> tag, the csrf thing, and the save/cancel buttons.
        if 'edit_form' in context:
            field_name = self.name(context)
            default_form_tag =  f'<form action="#edit-{field_name}" method="post" id="edit-{field_name}" enctype="multipart/form-data">'
            csrf = template.defaulttags.CsrfTokenNode().render(context)
            default_start = default_form_tag + csrf
            default_end = f'<table class="editable-field-save"><tr><td><input type="hidden" name="Save" value="{field_name}"><input type="submit" value="Save"></td><td><a href="?#edit-{field_name}"><button type="button">Cancel</button></a></td></tr></table></form> {template.Variable("edit_form.media").resolve(context)}'

            # Then either use the default (edit_form.as_table) or the given nodelist.
            if self.edit_nodelist is None:
                form_html =  '<table>'+template.Variable("edit_form.as_table").resolve(context)+'</table>'
            else:
                form_html = self.edit_nodelist.render(context)

            return default_start+form_html+default_end
        else:
            raise ValueError("No edit form!")
    def render(self, context):
        # render the preamble pre_edit button
        preamble_pre_edit = self.preamble_pre_edit.render(context)

        # render the edit_button if we're not editing something else:
        if self.writer(context) and not "editing" in context:
            edit_button = self.edit_button(context)
        else:
            edit_button = ""

        # render the preamble post edit
        preamble_post_edit = self.preamble_post_edit.render(context)

        # if we're editing, render the edit_nodelist
        # otherise the display_nodelist
        if self.writer(context) and self.editing(context):
                main = self.render_edit_nodelist(context)
        else:
                main = self.display_nodelist.render(context)

        #string them all together and return it.
        return preamble_pre_edit+edit_button+preamble_post_edit+main

