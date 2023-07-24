"""
This is not commented because I want to revamp the entire players/logistics system.
"""

from django import forms
from garhdony_app.models import PlayerProfile, TravelProfile

def LogisticalTaskFormClass(task):
    subclass_dict = {'confirmation': LogisticalTaskConfirmationForm, 'photo': LogisticalTaskPhotoForm,
                     'pregame_party': LogisticalTaskPregamePartyForm, 'travel_survey': LogisticalTaskTravelForm,
                     'housing_survey': LogisticalTaskHousingForm}
    ft = task.form_type
    if ft != '':
        return subclass_dict[ft]
    else:
        return None


class LogisticalTaskConfirmationForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = []


class LogisticalTaskPhotoForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = ['email', 'picture']
        widgets = {'picture': forms.FileInput}


class LogisticalTaskPregamePartyForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = ['pregame_party_rsvp']
        widgets = {'pregame_party_rsvp': forms.Select(choices=((True, "Yes"), (False, "No")))}

class LogisticalTaskTravelForm(forms.ModelForm):
    class Meta:
        model = TravelProfile
        exclude = ['dinner_status', 'departure_time']

    def __init__(self, post=None, files=None, instance=None):
        tp = TravelProfile.objects.filter(player_profile=instance)
        if post is None and files is None:
            if len(tp) > 0:
                super(LogisticalTaskTravelForm, self).__init__(instance=tp[0])
            else:
                super(LogisticalTaskTravelForm, self).__init__()
        else:
            if len(tp) > 0:
                super(LogisticalTaskTravelForm, self).__init__(post, files, instance=tp[0])
            else:
                super(LogisticalTaskTravelForm, self).__init__(post, files)
        self.fields['player_profile'].widget = forms.HiddenInput()
        self.fields['player_profile'].initial = instance
        self.fields['other'].required = False


class LogisticalTaskHousingForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = ['dietary_restrictions']
