"""
This file defines the LARPTextField which models use to store strings
that have gender-switched text and other LARP markup.

It also defines LARPTextFormField and LARPTextWidget, so that if you have one of these and generate a ModelForm,
django will automatically make an instance of the javascript editor for use in editing it.

BUT THAT DOESN"T WORK YET: I haven't managed to get the default formfield for a LARPTextField to be a LARPTextFormField
So all our forms need to set it manually, by having something like this in __init__:
    self.fields['name'] = LARPTextFormField(self.instance.game)
"""

from django.db import models
from django import forms
from django.utils.html import format_html
from django.utils.encoding import force_str
from django.forms.utils import flatatt
from django.utils.safestring import mark_safe
from six import python_2_unicode_compatible
from garhdony_app.span_parser import span_parse
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

@python_2_unicode_compatible
class LARPstring():
    """
    A class for holding a string with LARP related markup.

    self.tree is a span_parser.RootSpanNode which is the root of the larp-markup-spans-only html tree of the string
    self._broken is a boolean of whether or not it has unresolved keywords.
        This is updated only when needed, so is sometimes None

    You can get the text out in many formats:
    self.raw(): the raw string, with all the markup in there. This is what the editor wants.
    self.render_for_user(writer): renders the markup according to the boolean 'writer'
        which indicates if the user is a writer (and thus how to display stnotes etc).
    """
    def __init__(self, raw, check_keywords=True):
        """
        raw is a raw string with the markup. span_parse parses it for html span tags, which are how the markup works.
        """
        # TODO: remove the check_keywords argument which seems not to be used? 4/15

        if len(raw)>100: logger.debug(str(datetime.now())+": Creating new LARPString from: '"+raw[0:500]+"'")
        self.tree, self.syntax_problems = span_parse(raw)
        self._broken = None

    def inline(self):
        # renders and strips off outside <p> tags
        # for displaying short LARPStrings inline.
        text = mark_safe(self.render_for_user().strip())
        if text[0:3]=="<p>" and text[-4:]=="</p>":
            text = mark_safe(text[3:-5])
        return text

    def __str__(self):
        return self.render()

    def render(self):
        # Deprecated; use render_for_user()
        return self.render_for_user()

    def render_for_user(self, writer=False):
        return mark_safe(self.tree.render(writer))

    def raw(self):
        return mark_safe(self.tree.raw())

    def cleanup_temporary_markup(self):
        start_time = datetime.now()
        logger.debug(str(start_time)+": Cleaning up temp markup")
        self.tree.cleanup_temporary_markup()

        # Removed this because it's always short.
        # time = (datetime.now()-start_time).total_seconds()*1000
        # if time>1 : logger.debug(str(datetime.now())+": Cleaning done: " + str(time) + " milliseconds.")

    def mark_unresolved_keywords(self, game):
        # This is called when the form does clean() and also when it does prepare_value().
        # Lots of extra code here to avoid traversing the tree several times twice. Probably it's not necessary.
        if self._broken is not None:
            # If we know whether or not it's broken, don't search again; just return the result from last time.
            return self._broken
        else:
            # tree.mark_unresolved_keywords adds tags to the tree where it notices thing that need to be fixed,
            # and returns True if there were any.
            start_time = datetime.now()
            logger.debug(str(start_time)+": Starting m_u_k")
            b = self.tree.mark_unresolved_keywords(game.relevant_genderized_keywords())

            time = (datetime.now() - start_time).total_seconds()*1000
            if time > 0.01: logger.debug(str(datetime.now())+": Done m_u_k: " + str(time) + " milliseconds.")
            self._broken = b
            return b

    def regex_replace(self, regex, replacement):
        """
        Untested and unused 10/10/2015, but might be good for global find-replace
        Uses re.sub, so any syntax from there is allowed.
        """
        self.tree.regex_replace(regex, replacement)

def larpstring_to_python(value, check_keywords=True):
    """
    For taking a string, LARPstring, or None, and robustly making a LARPstring out of it.
    django often wants this sort of thing.
    """
    if isinstance(value, LARPstring):
        return value
    elif value is None:
        return value
    else:
        if len(value)>100: logger.debug(str(datetime.now()) + "Initializing new long LARPstring")
        return LARPstring(value, check_keywords)
class LARPTextField(models.TextField):
    """
    Model field for storing LARPstrings.
    The .raw() string is what's actually stored in the database.
    """

    # in the old version of django, this was handled by __metaclass__ = models.SubfieldBase
    def from_db_value(self, value, expression, connection):
        """ For getting out of the database."""
        return larpstring_to_python(value, check_keywords=False)

    def to_python(self, value):
        """ For getting out of the database."""
        return larpstring_to_python(value, check_keywords=False)

    def get_prep_value(self, value):
        """
        For putting into the database.
        Clean up any temporary markup that's there, then put raw string in database.

        According to django, this also needs to be able to handle string inputs which have already been prepped,
            so if it's a string just return it.
        """
        if isinstance(value, LARPstring):
            value.cleanup_temporary_markup()
            return value.raw()
        else:
            return value

    def value_from_object(self, obj):
        """
        For returning the value of the field from a particular sheet/character/whatever instance.
        Dear past-David: what does the above comment mean?
        """
        val = super(LARPTextField, self).value_from_object(obj)
        return val.raw()

    def formfield(self, **kwargs):
        """
        For making a formfield for this field.
        This is where we tell it to use a LARPTextFormField.

        The tricky bit is that LARPTextFormField needs to take game as an init arg.
        That is done by the form, which has to set it manually.
        """
        defaults = {'form_class': LARPTextFormField, 'widget': LARPTextWidget}
        defaults.update(kwargs)
        return super(LARPTextField, self).formfield(**defaults)

class LARPTextWidget(forms.Widget):
    """
    The widget for editing these things.
    """
    def __init__(self, attrs=None):
        super(LARPTextWidget, self).__init__(attrs)
        self.game = None

    def set_game(self, game):
        """
        This must be called before the widget is used, to tell it what game it's in.
        """
        self.game = game

    class Media:
        # There are complicated shenanigans with which media is loaded here and
        # which had to be hard-coded into the templates, because it has to be loaded in the right order.
        # I don't remember the details right now; put them in this comment if you figure it out.
        css = {
            'all': ('garhdony_app/pronoun_editor_style.css','garhdony_app/pronoun_editor_notebook_style.css',"http://netdna.bootstrapcdn.com/font-awesome/4.0.3/css/font-awesome.css")
        }
        js = ('garhdony_app/jquery.wysiwyg-resize.nonifrm.js','garhdony_app/pronoun_editor_notebook.js','garhdony_app/pronoun_editor_main.js')

    def render(self, name, value, attrs=None, renderer=None):
        """
        render is what it puts in the html. value is the text currently in the field, name is the name of the field.

        Partially copied from the forms.Textarea source.

        The html has 3 parts, which the javascript will recognize, contained in the big outside div called the ditor-bag:
            1. The editor, which contains the text, including the editor.
            2. The editor-shadow, which is a textarea. Forms can only actually save from textareas,
                so there's an invisible textarea to which the content is copied right before saving.
            3. A list of characters in the current game, for populating the gender-correction dropdown menus.
        
        Note that we are bypassing django's fancy (read: enormous stack of pasthrough functions) rednering technology here.
        Maybe that's bad?
        """

        assert self.game is not None, "LARPTextWidget must have its set_game method called before it is used."
        if value is None:
            value = ''
        characters = self.game.characters.all()
        characters_list = ['<span class="character" name="%s" gender="%s" id="%s"></span>'%(c.full_name(), c.gender(), str(c.id)) for c in characters]
        characters_html = '<span style="display:None" id="characters-list">\n  ' + '\n  '.join(characters_list) + '\n</span>'

        # get the final attrs, making sure to include self.attrs
        final_attrs = self.build_attrs(attrs, {'name':name})
        final_attrs.update(self.attrs)

        html = format_html('''
        <div class="editor-bag" {0}>
           <div class="editor">
             {1}
           </div>
           <textarea class="editor-shadow" name="{2}" style="width:100%%">
           </textarea>
           %s
        </div>'''%characters_html,
                            flatatt(final_attrs),
                            # If you put force_text here, then it doesn't work with unicode on digitalocean (raises encoding erros).
                            # If you put force_str, then on both digitalocean and locally, the whole format_html call returns ''.
                            # Hopefully those weren't doing anything important.
                            value,
                            name)
        return html

class LARPTextFormField(forms.CharField):
    """
    The field for forms.
    """
    def __init__(self, *args, **kwargs):
        # Then init and set the game.
        super(LARPTextFormField, self).__init__(*args, **kwargs)
        self.set_game(None)

        # All LarpTextFormFields keep a self.complete value, which decides whether this field needs gender correction.
        # If the form has WithComplete, then it will search these for False's, and if any are False, redisplay
        self.complete = False
        self._remembered_cleaned_data = None

    def set_game(self, game):
        self._game = game
        self.widget.set_game(game)

    @property
    def game(self):
        assert self._game is not None, "LARPTextFormField must have its set_game method called before it is used."
        return self._game
    
    def to_python(self, value):
        """ For converting the form string into python. """
        return larpstring_to_python(value, check_keywords=True)

    def prepare_value(self, value):
        """
        prepare_value gets called to determine what data to actually display given either the initial value (if the form
        is not bound) or the bound data value (if it is).

        initial: We pass the LARPstring object as initial data if it's unbound,
        So this should mark_unresolved_keywords (i.e. look for he and she and names and stuff), in case things have changed
        since the sheet was last saved.

        bound: It can be bound if the form needs to be redisplayed, usually because of gendered words that need fixing.
        In that case this will automatically get the string in the widget's data; we can't control that. To avoid
        scanning the string a second time, we have the clean method store the LARPstring object, and we just get it back
        out here. (Of course the form might be redisplaying for some other reason, in which case we are not sure what's
        going on; we just make a LARPstring out of the input data).
        """
        if value is None:
            return value
        if isinstance(value, LARPstring):
            # This happens for unbound forms, where this just gets passed the content.
            ls = value
            ls.mark_unresolved_keywords(self.game)
        else:
            # This happens for bound forms, where it gets passed the data.
            # Hopefully we remembered the scanned LARPstring computed in self.clean.
            if self._remembered_cleaned_data is not None:
                ls = self._remembered_cleaned_data
            else:
                logger.debug(str(datetime.now()) + "prepare_value needed to generate its own LARPstring.")
                ls = LARPstring(value)
        r = ls.raw()
        return mark_safe(r)

    def clean(self, value):
        # The clean method is where you are supposed to put validators.
        # mark_unresolved_keywords isn't quite a validator, because it marks them but we still want to save the form
        # if they are there. But we put it here anyway. At this point it also decides if it's complete (if its not
        # broken) which the form will use to decide whether to redisplay.

        logger.debug(str(datetime.now()) + ": Starting LARPTextFormField.clean on type: " + str(type(value)))
        value = super(LARPTextFormField, self).clean(value)

        # Next line removed to make IGNORE FOR NOW gender tag work. It might have been necessary for merge view stuff...
        # value.cleanup_temporary_markup()

        broken = value.mark_unresolved_keywords(self.game)
        self._remembered_cleaned_data = value
        self.complete = not broken
        logger.debug(str(datetime.now())+": Done clean")
        return value

    def forget_cache(self):
        self._remembered_cleaned_data = None
