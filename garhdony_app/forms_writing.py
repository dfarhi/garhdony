from diff_match_patch import diff_match_patch
from django import forms
from garhdony_app.models import SheetRevision, EditLock
from garhdony_app.forms_game_design import WithComplete
from garhdony_app.LARPStrings import LARPTextFormField, LARPstring
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


class SheetContentForm(WithComplete, forms.ModelForm):
    """
    The main form for editing a sheet's contents.
    It is a ModelForm on SheetRevision, because fundamentally it creates a SheetRevision object.

    It also knows who its user (author) is and what sheet it belongs to, which the view tell it by passing to __init__.
    It knows what EditLock it is tied to, as a hidden field.

    Each EditLock should only ever be tied to one instance of these forms in the universe.
    Whenever someone re-opens the page, we give them a new form with a new editlock.

    The form can also have a recovered_edit_lock. This is used by the client side javascript,
    if it decides that it wants to try to recover an old lock. Supplying this basically means
    'Pretend my edits were based from this previous lock instead of my real lock,
    for purposes of detecting edit conflicts.' This should only be used on a 'Save' action,
    not anything more complicated.
    """
    edit_lock = forms.ModelChoiceField(
        queryset=EditLock.objects.all(),
        widget=forms.HiddenInput()
    )

    recovered_edit_lock = forms.ModelChoiceField(
        queryset=EditLock.objects.all(),
        widget=forms.HiddenInput(),
        required=False,
    )

    # If there was an edit conflict, we want to store the original content the user tried to save.
    # So it goes here.
    edit_conflict_my_content = forms.CharField(required=False, widget=forms.Textarea(attrs={'style':'display:none'}))

    class Meta:
        model = SheetRevision
        fields = ['content', 'description']
        # We don't use description (the analog of commit messages). Should we? It's a hassle for the users.

    def __init__(self, sheet, user, *args, **kwargs):
        self.sheet = sheet
        self.user = user
        super(SheetContentForm, self).__init__(*args, **kwargs)

        # Set up the main field:
        logger.debug(str(datetime.now())+": Making SheetContentForm")
        # Make it a LARPField (not automatic due to the problem described in LARPString.py)
        self.fields['content'] = LARPTextFormField(self.sheet.game)

        if 'data' not in kwargs:
            # Set its initial contents to the previous revision's contents
            # But only do it if the form isn't bound
            # (i.e. if we're not immediately going to replace the initial value with the user's input value)
            # Since it takes a long time.
            self.fields['content'].initial = self.sheet.current_revision.content#.raw()

        # Make it big, and make the control-panel visible
        # (big/small is an option because every other editor is small and in-line, and doesn't want a control panel).
        self.fields['content'].widget.attrs['style'] = "min-height:600;padding:100;background-color:#FFF;"
        self.fields['content'].widget.attrs['data-control-panel'] = "true"

        # We don't set the EditLock field now; that is passed in by the view. There's no particular reason for that.

    def set_bound_content(self, new_content):
        """
        The content field is a LARPStringWidget, which caches its data.
        So when we set its value we need to clear its cache too.
        """
        self.data['content'] = new_content
        self.fields['content'].forget_cache()

    def prepare_for_merge(self):
        # Need to remember what we tried to submit
        # Before replacing the content field with the diff markup.
        self.data['edit_conflict_my_content'] = self.cleaned_data['content'].raw()
        self.cleaned_data['edit_conflict_my_content'] = self.data['edit_conflict_my_content']

    def _rebase(self, base, latest, our):
        """
        Just a tool for use in merge_rebase.
        Takes a change base-> our and applies it to latest instead.
        """
        dmp = diff_match_patch()
        diff = dmp.patch_make(base, our)
        return dmp.patch_apply(diff, latest)

    def merge_rebase(self, commit=True):
        """
        Rebase by automatically applying this edit to the sheet's last_revision.
        Returns True/False depending on whether it worked.

        If commit is true, actually replace the content of the form with the rebased version.
        (commit=False is an option so we can do dry runs to see if it's successful)
        """

        our_content = LARPstring(self.cleaned_data['edit_conflict_my_content'])
        new_content, successes = self._rebase(self.cleaned_data['edit_lock'].base_revision.content.raw(),
                                              self.sheet.current_revision.content.raw(),
                                              our_content.raw())

        if False in successes:
            return False
        else:
            if commit:
                self.cleaned_data['content'] = LARPstring(new_content)
            return True

    def save(self, *args, **kwargs):
        # Set the author and sheet of the SheetRevision we're creating.
        self.instance.sheet = self.sheet
        self.instance.author = self.user

        # Not sure why we need this next line. Maybe has to do with us doing what should really be "clean" in the view.
        # Maybe refactor that at some point?
        self.instance.content = self.cleaned_data['content']

        # Mark our editlock as having been saved.
        lock = self.cleaned_data['edit_lock']
        lock.saved = True
        lock.commit()

        super(SheetContentForm, self).save(*args, **kwargs)

        logger.debug(str(datetime.now())+": Saved")

class SheetUploadForm(forms.ModelForm):
    def __init__(self, sheet, user, *args, **kwargs):
        self.sheet = sheet
        self.user = user
        super(SheetUploadForm, self).__init__(*args, **kwargs)
    class Meta:
        model = SheetRevision
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data.get("file", False)
        if file and not file.name.endswith("."+self.sheet.get_content_type_display()):
            raise forms.ValidationError("File is not %s."%self.sheet.get_content_type_display())
        return file

    def save(self, *args, **kwargs):
        # Set the author and sheet of the SheetRevision we're creating.
        self.instance.sheet = self.sheet
        self.instance.author = self.user

        super(SheetUploadForm, self).save(*args, **kwargs)