"""
This is divided into sections.
Most of the sections correspond to the different forms that a game writer sees on a given page.

For pages that use render_editable_age (which is almost all of them), this means that there are a bunch of form classes,
then at the end of the section a function for selecting which form class to use from which named Edit button was clicked

That function always looks like this:
form_getter(request, field_name, data, files, *extra_args_for_this_page)

This could perhaps be abstracted a bit, since many of them are pretty similar in structure?
"""

from django import forms
import garhdony_app.assign_writer_game
from django.forms.widgets import TextInput
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.template.loader import render_to_string
from garhdony_app.models import EmbeddedImage, Character, GameInstance, Contact, GenderizedKeyword, GenderizedName, CharacterStat, PlayerCharacter, NonPlayerCharacter, Sheet, SheetColor, SheetType, CharacterStatType, GameInfoLink
from django.contrib.auth.models import Group, User
from guardian.shortcuts import get_objects_for_user
from garhdony_app.LARPStrings import LARPTextFormField, LARPTextField, LARPstring
import os

#######################################################
###################### Utilities ######################
#######################################################

class WithComplete():
    """
    This is a class you should make any form inherit from if it's going to use LARPTextFormFields.
    It adds a complete property, which asks whether all the fields are fully gender-ified
    for use in determining whether to redisplay the form after saving.

    This is different from redisplaying the form with errors; an incomplete form should be redisplay *after* saving.

    Maybe this kind of thing is what a MixIn is?
    """
    def complete(self):
        for name, field in self.fields.items():
            if hasattr(field, 'complete'):
                if not field.complete:
                    return False
        return True


def EditingFieldFormClassGeneric(model_class, field_name):
    """
    If render_editable_page is used and a particular writable_field is very generic,
    we can automatically generate the appropriate form.

    This works if the writable_field's name (which gets passed to edit_field in the view and then field_name here)
    is the name of a single field on the model.

    Many of the form_getters use this for some of the possible field_names, and use custom complex forms for others.
    """

    class HelperEditingFieldForm(WithComplete, forms.ModelForm):
        class Meta:
            model = model_class
            fields = [field_name]


    # Now check to see if it's a LARPTextField, because if so, due to the issues explained in LARPString.py, it doesn't
    # have the right default FormField.
    field = model_class._meta.get_field_by_name(field_name)[0]
    if not isinstance(field, LARPTextField):
        return HelperEditingFieldForm
    else:
        class LARPStringVersion(HelperEditingFieldForm):
            def __init__(self, *args, **kwargs):
                # Note: this assumes the thing it is passed has a ".game" attribute.
                # So if you have a model with a LARPTextField, you want to give it a .game property.
                super(LARPStringVersion, self).__init__(*args, **kwargs)
                self.fields[field_name] = LARPTextFormField(self.instance.game)
                self.fields[field_name].widget.attrs['style'] = "width:300;"

        return LARPStringVersion

class SelectWithPop(forms.Select):
    """
    This is a widget that is like a Select but also has a popup for adding more entries.
    It's used by CharacterMetadataForm. Probably we should use it more!

    It was copied form the internets and is poorly understood.
    """
    def __init__(self, field_name, *args, **kwargs):
        super(SelectWithPop, self).__init__(*args, **kwargs)
        self.field_name = field_name

    def render(self, name, value, attrs=None, choices=()):
        attrs.update({'id': 'id_' + self.field_name})
        html = super(SelectWithPop, self).render(name, value, attrs, choices)
        popupplus = render_to_string("garhdony_app/popupplus.html", {'field': self.field_name})
        return html + popupplus


#######################################################
############ Creating/Deleting Whole Games ############
#######################################################

class GameCreationForm(forms.ModelForm):
    """ For creating games from scratch. """
    class Meta:
        model = GameInstance
        exclude = ['preview_mode', 'complete']

    writers = forms.ModelMultipleChoiceField(queryset=Group.objects.get(name="Writers").user_set.all())

    def __init__(self, user, *args, **kwargs):
        super(GameCreationForm, self).__init__(*args, **kwargs)
        self.fields['writers'].initial = [user] # Default to the user being a writer.

    def save(self, *args, **kwargs):
        super(GameCreationForm, self).save(*args, **kwargs)
        for w in self.cleaned_data['writers']:
            # Assign writing permissions on the new game to the selected writers.
            garhdony_app.assign_writer_game.assign_writer_game(w, self.instance)


class GameCloneForm(forms.Form):
    """ For cloning games for subsequent runs. """
    source = forms.ModelChoiceField(queryset=GameInstance.objects.all()) # The game to clone from
    new_name = forms.CharField(max_length=50) # The new name
    username_suffix = forms.CharField(max_length=5) # The new username suffix # TODO: Check uniqueness of usernames

    def __init__(self, user, *args, **kwargs):
        super(GameCloneForm, self).__init__(*args, **kwargs)
        # TODO: re-add this functionality when it doesn't break game creation, i.e. when this bug is fixed:
        # https://github.com/django-guardian/django-guardian/issues/338
        # Set options to the games you are a writer on.
        # self.fields['source'].queryset = get_objects_for_user(user, 'garhdony_app.writer')

    def save(self, *args, **kwargs):
        return self.cleaned_data['source'].clone(self.cleaned_data['new_name'], self.cleaned_data['username_suffix'])

    @property
    def instance(self):
        """
        Get the new game after saving.
        This is for parallelism with GameCreationForm, which has this automatically as a ModelForm,
        so we can use the same view logic on both of them.
        """
        return GameInstance.objects.get(name=self.cleaned_data['new_name'])


#######################################################
################# Editing Whole Games #################
#######################################################



def GameEditingForm(request, edit_field, data, files, game):
    """
    This is the function needed by render_editable_page that chooses what form to use based on which portion
    of the game homepage is being edited.
    """
    if edit_field == "Metadata":
        return GameMetadataForm(data=data, instance=game)
    elif edit_field == "Writers":
        return GameAddWritersForm(data=data, instance=game)
    elif edit_field == "stats":
        StatTypeClass = stat_type_formset_maker(game=game)
        return StatTypeClass(data=data, queryset=game.character_stat_types.all())
    elif edit_field == "info_links":
        InfoLinkClass = info_link_formset_maker(game=game)
        return InfoLinkClass(data=data, queryset=game.info_links.all())
    else:
        raise ValueError("No such field: " + edit_field)


class GameMetadataForm(WithComplete, forms.ModelForm):
    """ Simple ModelForm, edits all the actual fields. """
    class Meta:
        model = GameInstance
        exclude = ["template"]

def stat_type_formset_maker(game):
    """
    A formset of several GameStatForms.
    This is a function which returns a formset class, like modelformset_factory.
    Formsets are like forms, basically; render_editable_page doesn't notice the difference.
    """
    return forms.models.modelformset_factory(CharacterStatType, extra=1, form=stat_type_form_class_maker(game), can_delete=True)

def stat_type_form_class_maker(game):
    """
    A function that returns the form for editing a single CharacterStatType on game game.
    Note that it's a function that returns a class. That's because we need to pass the game argument to that class, but
        the built-in formset_factory wants just a regular class with a pre-defined __init__ signature.
    The GameStatFormSet is a list of several of these using the built-in django formset technology.
    """
    class GameStatForm(WithComplete, forms.ModelForm):
        class Meta:
            model = CharacterStatType
            widgets = {'game': forms.HiddenInput} # Leave the game in there, as a hidden input, so that saving is simple

        def __init__(self, *args, **kwargs):
            super(GameStatForm, self).__init__(*args, **kwargs)
            self.fields['game'].initial = game # Set the game to the game argument provided to the function.

    return GameStatForm

def info_link_formset_maker(game):
    """
    As for CharacterStat
    """
    return forms.models.modelformset_factory(GameInfoLink, extra=1, form=info_link_form_class_maker(game), can_delete=True)

def info_link_form_class_maker(game):
    """
    As for CharacterStat
    """
    class InfoLinkForm(forms.ModelForm):
        class Meta:
            model = GameInfoLink
            widgets = {'game': forms.HiddenInput} # Leave the game in there, as a hidden input, so that saving is simple

        def __init__(self, *args, **kwargs):
            super(InfoLinkForm, self).__init__(*args, **kwargs)
            self.fields['game'].initial = game # Set the game to the game argument provided to the function.

    return InfoLinkForm


class GameAddWritersForm(WithComplete, forms.ModelForm):
    """
    The form for changing the writers.
    It's a ModelForm so that we can use the ModelForm's ties to the underlying model,
    But doesn't directly automatically edit the model's stuff.

    It only adds, does not remove.
    We don't let writers be removed in the normal course of business, lest weird things happen.
    Probably we could.
    """
    class Meta:
        model = GameInstance
        fields = []


    writers = forms.ModelMultipleChoiceField(queryset = Group.objects.get(name="Writers").user_set.all(),
                                             label="",
                                             required=False)

    def __init__(self, *args, **kwargs):
        super(GameAddWritersForm, self).__init__(*args, **kwargs)
        # Set the choices to only those not already writing.
        # choices is a list of pairs of (id, display)
        writers_not_already_writing = [(u.pk, u.username) for u in list(Group.objects.get(name="Writers").user_set.all()) if not u.has_perm('garhdony_app.writer', self.instance)]
        self.fields['writers'].choices = writers_not_already_writing


    def save(self, *args, **kwargs):
        for w in self.cleaned_data['writers']:
            garhdony_app.assign_writer_game.assign_writer_game(w, self.instance)
        return super(GameAddWritersForm, self).save(*args, **kwargs)


#######################################################
####### Creating/Deleting Sheets and Characters #######
#######################################################

class CharacterNewForm(forms.Form):
    """
    Form for making a new Character (either PC or NPC)
    Some things aren't set here and have to be set by editing later, to avoid clutter on this page and also
    to avoid needing different forms and logic for PCs and NPCs.

    This is not a ModelForm because it decides which class (PlayerCharacter or NonPlayerCharacter) to use on the fly.
    """
    first_male = forms.CharField(max_length=50, widget=TextInput(attrs={'placeholder': 'Male First Name'}))
    first_female = forms.CharField(max_length=50, widget=TextInput(attrs={'placeholder': 'Female First Name'}))
    last_name = forms.CharField(max_length=50, widget=TextInput(attrs={'placeholder': 'Last Name', 'size': 48}),
                                required=False)
    char_type = forms.ChoiceField(choices=(("PC", "PC"), ("NPC", "NPC"),))

    def save(self, game, *args):
        """Note the extra game argument. We don't want that in the form, so you have to pass it."""

        # Make a new first name object out of the cleaned_data
        first = GenderizedName(male=self.cleaned_data['first_male'], female=self.cleaned_data['first_female'])

        # Then make the subclass object.
        if self.cleaned_data['char_type'] == "PC":
            username = (first.male[0] + self.cleaned_data['last_name']).lower()
            if not User.objects.filter(username=username).exists():
                # If the username is taken, change it to the first name.
                username = self.cleaned_data['first_male']
            c = PlayerCharacter(game=game, first_name_obj=first, last_name=self.cleaned_data['last_name'],
                                username=username, password="DEFAULT")
            # Make them a sheet by default
            name_ls = LARPstring(c.first_name()+" "+c.last_name)
            #TODO: That doesn't catch the first_name keyword, because first_name isn't a saved keyword yet.
            character_sheet = Sheet(game=game, color=SheetColor.objects.get(name='Yellowsheet'),
                      sheet_type=SheetType.objects.get(name="Story"), name=name_ls,
                      filename=c.first_name()+" "+c.last_name, content_type='html')
            character_sheet.save(*args)
        elif self.cleaned_data['char_type'] == "NPC":
            c = NonPlayerCharacter(game=game, first_name_obj=first, last_name=self.cleaned_data['last_name'])

        # Set up the circular reference where the character's first_name, as a GenderizedName, needs to know about its character.
        first.character = c # Not sure we need this line?
        c.save(*args) # This automatically saves the first_name_obj also.
        if self.cleaned_data['char_type'] == "PC":
            c.sheets.add(character_sheet)
        return c


class CharacterDeleteForm(forms.Form):
    """Form for choosing which character to Delete."""
    def __init__(self, game, *args, **kwargs):
        super(CharacterDeleteForm, self).__init__(*args, **kwargs)
        self.fields['character'].queryset = game.characters.all() # Only allow options in this game.

    character = forms.ModelChoiceField(queryset=None)


class SheetNewForm(forms.ModelForm):
    """ModelForm for making a new sheet."""
    class Meta:
        model = Sheet
        exclude = ['game', 'content', 'preview_description', 'last_printed', 'hidden', 'file']

    def save(self, game, commit=True, *args, **kwargs):
        s = super(SheetNewForm, self).save(commit=False, *args, **kwargs)
        s.game = game
        if commit:
            # Sometimes django does dry runs of the save function.
            s.save()
        return s


class SheetDeleteForm(forms.Form):
    def __init__(self, game, *args, **kwargs):
        super(SheetDeleteForm, self).__init__(*args, **kwargs)
        self.fields['sheet'].queryset = game.sheets.all() # Only display this game's sheets as options.

    sheet = forms.ModelChoiceField(queryset=None)


########################################################
################## Editing Characters ##################
########################################################


class BaseCharacterMetadataForm(WithComplete, forms.ModelForm):
    class Meta:
        model = Character
        fields = ['title_obj', 'last_name']
        widgets = {'title_obj': SelectWithPop('title_obj'), # imported; defines the select widget with a button to make a new one.
                   'last_name': forms.TextInput(attrs={'placeholder': 'Last Name', 'size': 28}),
        }

    first_male = forms.CharField(label="First Name (Male)", widget=TextInput(
        attrs={'placeholder': 'Male First Name', 'size': 10, 'style': "background-color: #BCF"}))
    first_female = forms.CharField(label="First Name (Female)", widget=TextInput(
        attrs={'placeholder': 'Female First Name', 'size': 10, 'style': "background-color:#FFA"}))

    def __init__(self, data=None, *args, **kwargs):
        super(BaseCharacterMetadataForm, self).__init__(data=data, *args, **kwargs)
        self.fields['title_obj'].queryset = GenderizedKeyword.objects.filter(category='title')
        try:
            character = self.instance
        except:
            # You can only get here if you're editing an existing character, so it should always have an instance.
            raise ValueError("Problem with Metadata form being created without an instance")
        self.fields['first_male'].initial = character.first_name_obj.male
        self.fields['first_female'].initial = character.first_name_obj.female

    def save(self, commit=True):
        """
        Save the stuff with commit, then update first name, then save for reals.

        Use commit=False to avoid saving to the database twice.
        """
        character = super(BaseCharacterMetadataForm, self).save(commit=False)

        # Update the first name
        first = character.first_name_obj
        first.male = self.cleaned_data['first_male']
        first.female = self.cleaned_data['first_female']

        if commit:
            character.save()

        return character

class PlayerCharacterMetadataForm(BaseCharacterMetadataForm):
    """
    The form for the metadata edit_field on the character's homepage.

    It has four categories of fields:
        * The ones inherited from BaseCharacterMetadataForm (first_name, title)
        * The simplest ones (username, password) are generated automatically by the ModelForm
        * gender is add as a normal form field
        * There are two formsets which are attached to the form (names and stats).
            The fields in these aren't really normal fields on this form;
            They are just properties of the form instance, form.names_formset and form.stats_formset,
            So we have to make sure to manually save and manipulate them.
    """

    class Meta():
        model = PlayerCharacter
        fields = BaseCharacterMetadataForm.Meta.fields+['username', 'password']
        # First name is special because the field on the Character Model is a ForeignKey to a GenderizedName,
        # But we want to display the male/female versions of the genderized name directly.
        # So we make custom first_male and first_female forms.

        widgets = BaseCharacterMetadataForm.Meta.widgets
        widgets.update({
                   'username': forms.TextInput(attrs={'placeholder': 'username', 'size': 10}),
                   'password': forms.TextInput(attrs={'placeholder': 'password', 'size': 10}),
        })

    # Gender is displayed with the stats formset, but it's not a normal stat; it affects the character's default_gender.
    gender_field = forms.ChoiceField(choices=(("M", "Male"), ("F", "Female"),))

    # There are also the stats and names, but those are produced by __init__.

    def __init__(self, data=None, *args, **kwargs):
        super(PlayerCharacterMetadataForm, self).__init__(prefix="main_form", data=data, *args, **kwargs)

        character = self.instance

        self.fields['gender_field'].initial = character.gender()
        if character.player_cast:
            # Can't modify gender if they've been cast; that would confused users too much
            # (Although the code would understand -- this is the default_gender, for use if they ever get uncast)
            self.fields['gender_field'].widget = forms.HiddenInput()

        # Fill in the names and stats sections with a GenderizedNameFormSet and StatsFormSet.
        # These are formsets from django's built-in formset functionality.
        # queryset is the set of objects (names/stats) to generate entries for
        # prefix is a thing that is appended to the names of all the inputs in the formset, so we don't get it mixed up
            # with other bits of the form (especially important since there are two formsets here).
        # initial is the initial data to use in all the blank lines.
        if data:
            self.names_formset = GenderizedNameFormSet(data, prefix='other_names', queryset=character.nonfirst_names())
            self.stats_formset = StatsFormSet(data, prefix='stats', queryset=character.stats.all())
        else:
            self.names_formset = GenderizedNameFormSet(queryset=character.nonfirst_names(),
                                                       initial=[{'category': 'name', 'character': character}],
                                                       prefix='other_names')
            self.stats_formset = StatsFormSet(queryset=character.stats.all(), prefix='stats')


    def save(self, commit=True):
        # Save the normal bit
        # TODO: Could maybe move the super call to the end to avoid the dumb commit=False thing?
        # Might even need to do so to fix the bug where npc photos don't move when you change their name.
        character = super(PlayerCharacterMetadataForm, self).save(commit=False)

        # Save the formsets
        self.names_formset.save(commit)
        self.stats_formset.save(commit)

        # Update the gender
        character.default_gender = self.cleaned_data['gender_field']

        # Save the changes
        # character.save() automatically saves the first_name_obj also.
        if commit:
            character.save()

    def is_valid(self):
        # Check the main form and the internal formsets.
        return super(PlayerCharacterMetadataForm, self).is_valid() \
               and self.names_formset.is_valid() and self.stats_formset.is_valid()

    def clean_username(self, *args, **kwargs):
        """Make sure usernames stay unique."""
        new_username = self.cleaned_data['username']
        new_full = new_username+self.instance.game.usernamesuffix
        if User.objects.filter(username=new_full).exists():
            other_pc = User.objects.get(username=new_full).character
            if other_pc != self.instance:
                game = other_pc_game = other_pc.game
                if game == self.instance.game:
                    raise forms.ValidationError("Username '%(new)s' already exists (%(other_pc_name)s)",
                                        params={'new':new_username, 'other_pc_name':other_pc.name()})
                else:
                    raise forms.ValidationError("Full username '%(new)s' already exists (%(other_pc_name)s in game %(game)s)",
                                        params={'new':new_full,
                                                'other_pc_name':other_pc.name(),
                                                'game':other_pc.game.name
                                                })

        # super class probably doesn't have clean_username,
        # but if it does we should call this.
        # So we either go to the superclass or not, if it fails
        # TODO: Make this not a try/except since it's not really an error.
        try:
            return super(PlayerCharacterMetadataForm, self).clean_username(*args, **kwargs)
        except AttributeError:
            return self.cleaned_data['username']

class GenderizedNameForm(forms.ModelForm):
    """A form for GenderizedNames, for use in a formset in CharacterMetadataForm"""
    class Meta:
        model = GenderizedName
        fields = ('male', 'female', 'category', 'character', 'genderizedkeyword_ptr',)
        widgets = {
            'category': forms.HiddenInput,
            'character': forms.HiddenInput
        }

    def __init__(self, *args, **kwargs):
        super(GenderizedNameForm, self).__init__(*args, **kwargs)
        self.fields['category'].show_hidden_initial = True
        self.fields['character'].show_hidden_initial = True
        self.fields['male'].widget.attrs['size'] = 10
        self.fields['male'].widget.attrs['style'] = "background-color:#BCF"
        self.fields['female'].widget.attrs['size'] = 10
        self.fields['female'].widget.attrs['style'] = "background-color:#FFA"

# The formset_factory for use in CharacterMetadataForm
GenderizedNameFormSet = forms.models.modelformset_factory(GenderizedName, extra=1, form=GenderizedNameForm,
                                                          can_delete=True, can_order=True)


class StatForm(forms.ModelForm):
    """A form for CharacterStats, for use in a formset in CharacterMetadataForm"""
    class Meta:
        model = CharacterStat
        fields = ['value']

    def __init__(self, *args, **kwargs):
        super(StatForm, self).__init__(*args, **kwargs)
        self.fields['value'].label = self.instance.stat_type.name

# The formset_factory for use in CharacterMetadataForm
StatsFormSet = forms.models.modelformset_factory(CharacterStat, extra=0, form=StatForm)




def character_sheets_form_class_maker(sheet_types=None, sheet_colors=None):
    """
    This function returns a Form class for selecting the sheets of a certain type/color.
    sheet_types and sheet_colors are each lists of SheetType and SheetColor objects (respectively) to match against.

    It's a function that returns a class, rather than just a class with a custom __init__,
    because CharacterEditingFieldForm wants to handle all the classes the same way.
    """

    class CharacterSheetsForm(WithComplete, forms.ModelForm):
        class Meta:
            model = PlayerCharacter
            fields = ["sheets"]
            widgets = {'sheets': FilteredSelectMultiple("Sheets", is_stacked=False)}

        def __init__(self, *args, **kwargs):
            # Need to put the right things in the queryset (the property that sets the set of things that can be selected or not selected).
            super(CharacterSheetsForm, self).__init__(*args, **kwargs)
            qs = Sheet.objects.filter(game=self.instance.game)
            if sheet_types is not None:
                qs = qs.filter(sheet_type__in=sheet_types)
            if sheet_colors is not None:
                qs = qs.filter(color__in=sheet_colors)

            self.fields['sheets'].queryset = qs
            self.fields['sheets'].help_text = ""
            self.fields['sheets'].label = ""

        def save(self, *args, **kwargs):
            # Need to find the character's sheets, and replace the ones that match sheet_types and sheet_colors
            # With the new set.

            # Can this mess be simplified a lot using set()?

            # old_sheets is going to be the list of all the sheets they used to have that don't match the given properties
            # So new_sheets is old_sheets + selected_sheets
            old_sheets = self.instance.sheets.all()
            if sheet_types is not None and sheet_colors is None:
                old_sheets = old_sheets.exclude(sheet_type__in=sheet_types)
            if sheet_colors is not None and sheet_types is None:
                old_sheets = old_sheets.exclude(color__in=sheet_colors)
            if sheet_colors is not None and sheet_types is not None:
                old_sheets = old_sheets.exclude(color__in=sheet_colors, sheet_type__in=sheet_types)
            new_sheets = list(old_sheets) + list(self.cleaned_data['sheets'])

            # Then pretend that the user selected all those sheets for the sheets property of the ModelForm, then save.
            self.cleaned_data['sheets'] = new_sheets
            super(CharacterSheetsForm, self).save(*args, **kwargs)

        class Media:
            # Need this for FilteredSelectMultiple
            css = {
                'all': ['admin/css/widgets.css'],
            }

    return CharacterSheetsForm


character_editing_form_classes = {
    "Metadata": PlayerCharacterMetadataForm,
    "public_sheets": character_sheets_form_class_maker(sheet_types=[SheetType.objects.get(name="Public Sheet")]),
    "private_sheets": character_sheets_form_class_maker(
        sheet_types=SheetType.objects.filter(name__in=['Story', 'Details', 'Supplement'])),
    "in-game_documents": character_sheets_form_class_maker(sheet_types=SheetType.objects.filter(name__in=['In-Game Document']))
}


def CharacterEditingFieldForm(request, field_name, data, files, character):
    """
    This is the function needed by render_editable_page that chooses what form to use based on which portion
    of the character's homepage is being edited.
    """

    # First get the right form class
    if field_name in character_editing_form_classes.keys():
        # This is the above dictionary of edit_fields to form classes.
        form_class = character_editing_form_classes[field_name]
    else:
        # If it's one that's simpler than those, use the Generic form class.
        # This is currently just Costuming Hint.
        form_class = EditingFieldFormClassGeneric(PlayerCharacter, field_name)

    # Then initialize it with the passed data and files, and tie it to the right character.
    return form_class(data=data, files=files, instance=character)


class NPCMetadataForm(BaseCharacterMetadataForm):
    """
    BaseCharacterMetadataForm form does first name and title
    This does gender stuff
    """


    class Meta(BaseCharacterMetadataForm.Meta):
        model = NonPlayerCharacter
        fields = BaseCharacterMetadataForm.Meta.fields +['gender_field', 'gender_linked_pc']

    def __init__(self, *args, **kwargs):
        super(NPCMetadataForm, self).__init__(*args, **kwargs)
        self.fields['gender_linked_pc'].queryset = PlayerCharacter.objects.filter(game=self.instance.game)

    def clean_gender_linked_pc(self, *args, **kwargs):
        if self.cleaned_data['gender_field'] in ["M", "F"]:
            if self.cleaned_data['gender_linked_pc'] is not None:
                raise forms.ValidationError("For fixed gender, set blank PC")
        else:
            if self.cleaned_data['gender_linked_pc'] is None:
                raise forms.ValidationError("Choose a PC")
        return self.cleaned_data['gender_linked_pc']



npc_editing_form_classes = {
    "Metadata": NPCMetadataForm
}

def NPCEditingForm(request, field_name, data, files, character):
    """
    This is the function needed by render_editable_page that chooses what form to use based on which portion
    of the NPC's page is being edited.
    """

    if field_name in npc_editing_form_classes.keys():
        # Only metadata is weird; it uses the NPCMetadataForm as per the above dictionary.
        # But you could add more to the dictionary if some other field needed its own form.
        form_class = npc_editing_form_classes[field_name]
    else:
        # All the others just use the generic formclass
        form_class = EditingFieldFormClassGeneric(NonPlayerCharacter, field_name)
    return form_class(data=data, files=files, instance=character)


#########################################################
#################### Editing Sheets #####################
#########################################################



class SheetMetadataForm(WithComplete, forms.ModelForm):
    """For editing sheet metadata. WithComplete lets us use LARPTextFormFields."""
    class Meta:
        model = Sheet
        fields = ['name', 'filename', 'color', 'sheet_type', 'hidden', 'sheet_status', 'preview_description']

    def __init__(self, *args, **kwargs):
        """
        We need this because of the issue described in LARPStrings.py where I can't get
        LARPTextFormField to be the default form field for LARPTextFields in the model.
        """
        super(SheetMetadataForm, self).__init__(*args, **kwargs)
        self.fields['preview_description'] = LARPTextFormField(self.instance.game)
        self.fields['name'] = LARPTextFormField(self.instance.game)

    def clean(self, *args, **kwargs):
        # TODO: Use clean() to check that there's a preview description for unhidden sheets if game's in preview mode.
        super(SheetMetadataForm, self).clean(*args, **kwargs)
        if (not self.cleaned_data['hidden']) and self.instance.game.preview_mode and self.cleaned_data[
            'preview_description'] == "":
            ##This doesn't work; maybe it has to do with the fact that there's <p class='placeholder'> things around.
            raise forms.ValidationError("Put a preview description to show this sheet while in preview mode.")
        return self.cleaned_data


class SheetCharactersForm(WithComplete, forms.ModelForm):
    """For selecting which characters should have this sheet."""
    class Meta:
        model = Sheet
        fields = []

    characters = forms.ModelMultipleChoiceField(queryset=PlayerCharacter.objects.all(),
                                                widget=FilteredSelectMultiple("", is_stacked=False), label="",
                                                required=False)

    class Media:
        # Need this for FilteredSelectMultiple
        css = {'all': ['admin/css/widgets.css'],}

    def __init__(self, instance, data=None, files=None):
        super(SheetCharactersForm, self).__init__(data)
        self.instance = instance
        self.fields['characters'].queryset = instance.game.pcs()
        self.fields['characters'].initial = instance.characters.all()

    def save(self):
        """
        This has to jump through some hoops because we're editing it in a very backwards way from the point of view of
        the database, which stores sheets per character, not characters per sheet.
        """
        old_characters = set(self.instance.characters.all())
        new_characters = set(self.cleaned_data['characters'])
        removed_characters = old_characters - new_characters
        added_characters = new_characters - old_characters
        for c in removed_characters:
            c.sheets.remove(self.instance)
            c.save()
        for c in added_characters:
            c.sheets.add(self.instance)
            c.save()

sheet_editing_form_classes = {
    "Metadata": SheetMetadataForm,
    "characters": SheetCharactersForm
}


def SheetEditingFieldForm(request, field_name, data, files, sheet):
    """The thing that render_editable_page uses to pick which Form to use"""
    if field_name in sheet_editing_form_classes.keys():
        # Metadata and characters have special forms.
        form_class = sheet_editing_form_classes[field_name]
    else:
        # Currently nothing on the sheet has a generic form, but it's nice to be safe.
        form_class = EditingFieldFormClassGeneric(Sheet, field_name)
    return form_class(data=data, files=files, instance=sheet)


########################################################
####################### Contacts #######################
########################################################

class NewContactForm(WithComplete, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['owner', 'target', 'display_name', 'description']
        widgets = {'owner': forms.HiddenInput} # Hidden since it's infered from the page you're on.
        labels = {'target': "New Target"}

    def __init__(self, owner, *args, **kwargs):
        # owner is passed from the view which knows what page you're on.
        super(NewContactForm, self).__init__(*args, **kwargs)
        self.fields['owner'].initial = owner
        self.fields['description'] = LARPTextFormField(owner.game)
        self.fields['target'].queryset = owner.game.characters
        self.fields['display_name'] = LARPTextFormField(owner.game)


class ContactForm(WithComplete, forms.ModelForm):
    class Meta:
        model = Contact
        exclude = ["owner", "target", "order_number"]

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        self.fields['description'] = LARPTextFormField(self.instance.game)
        self.fields['display_name'] = LARPTextFormField(self.instance.game)

# For re-ordering, we want a formset that only touches the order_number.
# Maybe can_delete should be False? That controls whether you can delete contacts from the re-ordering form.
ContactReorderFormSet = forms.models.modelformset_factory(Contact, fields=["order_number"], extra=0, can_delete=True)


def ContactEditingFieldFormClass(request, field_name, data, files, character):
    """The form-chooser function for render_editable_page"""
    if field_name == "batch_edit":
        # batch_edit is a terrible name. It means "the re-order form."
        fs = ContactReorderFormSet(queryset=character.contacts.order_by('order_number'), data=data,
                                   initial=[{"owner": character}])
        return fs
    elif field_name == "add":
        return NewContactForm(owner=character, data=data, files=files)
    else:
        # If we're editing a particular one, the field_name is the primary key of that one.
        contact = Contact.objects.get(pk=field_name)
        return ContactForm(instance=contact, data=data, files=files)

########################################################
################# Editing Other Things #################
########################################################

class NewTitleForm(forms.ModelForm):
    """This is for the popup that appears when you click the little plus next to title while editing a character."""
    class Meta:
        model = GenderizedKeyword
        fields = ["male", "female", "category"]
        widgets = {"category": forms.HiddenInput}

    def __init__(self, *args, **kwargs):
        super(NewTitleForm, self).__init__(*args, **kwargs)
        self.fields['category'].initial = "title" # Always make titles.

class NewEmbeddedImageForm(forms.ModelForm):
    class Meta:
        model = EmbeddedImage
        exclude = ["filename"]
        widgets = {"game": forms.HiddenInput}
    obfuscate_name = forms.BooleanField(initial=False, required=False)

    def __init__(self, game, sheet, *args, **kwargs):
        super(NewEmbeddedImageForm, self).__init__(*args, **kwargs)
        self.fields['game'].initial = game
        #self.fields['sheets'].initial = [sheet]

    def save(self, commit=True):
        original_name = self.files['file'].name
        split_name = original_name.split('.')
        if self.cleaned_data['obfuscate_name']:
            split_name = ['image', split_name[-1]]

        self.instance.filename = original_name
        # Adds a number to the filename to make it unique.
        n = 0
        while os.path.exists(self.instance.absolute_path):
            n+=1
            self.instance.filename = split_name[0] +'__'+str(n)+'.'+split_name[-1]
        super(NewEmbeddedImageForm, self).save(commit)


########################################################
######################## Search ########################
########################################################

class SearchForm(forms.Form):
    query = forms.CharField(label="", required=False)
    raw = forms.BooleanField(label="Search markup", initial=False, required=False)
    wholewords = forms.BooleanField(label="Whole Words", initial=True, required=False)
    matchcase = forms.BooleanField(label="Match Case", initial=False, required=False)
    #Todo: allow searching of non-sheet-content fields
    #sheet_text = forms.BooleanField(label="Search Sheet Text", initial=True, required=False)
    #character_metadata = forms.BooleanField(label="Search Character Metadata", initial=True, required=False)
