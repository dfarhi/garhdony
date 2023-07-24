from django import forms
from django.contrib.auth.forms import UserCreationForm
import auth
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms.widgets import PasswordInput, TextInput
from garhdony_app.models import GameInstance
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm

class DogmasAuthenticationForm(AuthenticationForm):
    """The main login form"""
    username = forms.CharField(label="Username", max_length=50,
                               widget=TextInput(attrs={'class': 'login_widget', 'placeholder': 'username'}))
    password = forms.CharField(label="Password", max_length=50,
                               widget=PasswordInput(attrs={'class': 'login_widget', 'placeholder': 'password'}))

    def confirm_login_allowed(self, user):
        """
        This is where you're supposed to put extra rules for who can log in.
        We want to check to see that the character has been cast; don't allow login if not.
        """
        if not user.has_perm('garhdony_app.writer') and not user.character.player_cast:
            raise forms.ValidationError(
                    "Something strange has happened - our system thinks that character is not cast.")


class NewWriterForm(UserCreationForm):
    """
    For making a new writer user on the site.
    It's like the built in UserCreationForm but it also assigns them some games.
    """
    games = forms.ModelMultipleChoiceField(queryset=GameInstance.objects.all(), # Allows all games as options
                                           widget=FilteredSelectMultiple("", is_stacked=False), # Uses the fancy chooser
                                           label="Games",
                                           required=False)

    class Media:
        # You need this whenever your forms have FilteredSelectMultiple.
        css = {
            'all': ['admin/css/widgets.css'],
        }

    def save(self, *args, **kwargs):
        """
        Do normal saving, then assign the writer permissions as a writer in general and on the selected games.
        """
        user = super(NewWriterForm, self).save(*args, **kwargs)
        g = Group.objects.get(name='Writers')
        g.user_set.add(user)
        for game in self.cleaned_data['games']:
            auth.assign_writer_game(user, game)
        return user


class WriterChangeForm(forms.ModelForm):
    # For letting writers edit their data.
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

def writer_home_form_getter(request, edit_field, data, files, user):
    """
    The function required by render_editable_page that returns the appropriate Form depending on the edit_field.
    This page has only one editable field, namely Metadata, which uses the WriterChangeForm.
    """
    if edit_field == "Metadata":
        return WriterChangeForm(data=data, instance=user)
    else:
        raise ValueError("No such field: " + edit_field)