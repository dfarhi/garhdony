from django import forms

from garhdony_app.models.timelines import MONTHS, Timeline, TimelineEvent, TimelineEventDescription, TimelineViewer
from garhdony_app.views_editable_pages import EditingFieldFormClassGeneric


class MasterTimelineEventFormDate(forms.ModelForm):
    year = forms.IntegerField(widget=forms.NumberInput(attrs={'style': 'width: 4em;'}))
    month = forms.ChoiceField(choices = [(None, "--")] + [(i, month) for i, month in enumerate(MONTHS, 1)],  required=False)
    day = forms.ChoiceField(choices = [(None, "--")] + [(i, i) for i in range(1, 32)], required=False)
    class Meta:
        model = TimelineEvent
        fields = ['year', 'month', 'day']

    def clean(self):
        cleaned_data = super().clean()
        # replace '' with None
        cleaned_data['day'] = cleaned_data['day'] if cleaned_data['day'] else None
        cleaned_data['month'] = cleaned_data['month'] if cleaned_data['month'] else None
        return cleaned_data

class MasterTimelineEventDescriptionForm(forms.ModelForm):
    class Meta:
        model = TimelineEventDescription
        fields = ['description', 'viewer']

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event')
        super().__init__(*args, **kwargs)
        self.fields['viewer'].queryset = TimelineViewer.objects.filter(timeline=self.event.timeline)
        self.fields['viewer'].empty_label = "[Add to sheet]"
        self.fields['description'].set_game(self.event.timeline.game)

        if self.instance and self.instance.pk:
            self.fields['viewer'].widget.attrs['disabled'] = True

MasterTimelineEventDescriptionFormSet = forms.inlineformset_factory(
    TimelineEvent,
    TimelineEventDescription,
    form=MasterTimelineEventDescriptionForm,
    fields=('description', 'viewer'),
    extra=5,
    can_delete=True,
    can_delete_extra=False,
)

def make_master_timeline_event_form(request, field_name, data, files, timeline: Timeline):
    # field_name is "event-{id}-{date/name}"
    _, id, field_name = field_name.split('-')
    timeline_event = timeline.events.get(pk=id)
    if field_name == 'date':
        return MasterTimelineEventFormDate(data, files, instance=timeline_event)
    elif field_name == 'internal_name':
        return EditingFieldFormClassGeneric(TimelineEvent, field_name='internal_name')(data, files, instance=timeline_event)
    elif field_name == 'descriptions':
        return MasterTimelineEventDescriptionFormSet(data, files, instance=timeline_event, form_kwargs={'event': timeline_event})
    else:
        raise Exception(f"Invalid field name {field_name}")
    

class TimelineEventDescriptionForm(MasterTimelineEventFormDate):
    """
    Inherits from MasterTimelineEventFormDate to share the formatting of date fields
    But it's otherwise different.
    """
    internal_name = forms.CharField(max_length=300, required=False)    
    class Meta:
        model = TimelineEventDescription
        fields = ['description', 'year', 'month', 'day', 'viewer', 'event']

    class Media:
        js = ('garhdony_app/timeline.js',)

    def __init__(self, *args, **kwargs):
        self.viewer = kwargs.pop('viewer')
        super().__init__(*args, **kwargs)
        # Make event optional
        self.fields['event'].required = False

        self.editable_event = True
        if self.instance and self.instance.pk and self.instance.event:  # if there is an event instance related to the description
            # set the initial value of event_date
            self.fields['year'].initial = self.instance.event.year  
            self.fields['month'].initial = self.instance.event.month
            self.fields['day'].initial = self.instance.event.day
            self.fields['internal_name'].initial = self.instance.event.internal_name
        
            self.fields['event'].widget = forms.HiddenInput()
            # Can't change event / internal name on an existing one which has other characters viewing it
            if self.instance.event.descriptions.count() > 1:
                self.fields['internal_name'].widget = forms.HiddenInput()
                self.fields['year'].widget = forms.HiddenInput()
                self.fields['month'].widget = forms.HiddenInput()
                self.fields['day'].widget = forms.HiddenInput()
                self.editable_event = False

        else:
            self.fields['event'].queryset = self.viewer.timeline.events.all().order_by('year', 'month', 'day')
            self.fields['event'].empty_label = "[New Event]"
        self.fields['description'].set_game(self.viewer.timeline.game)
        self.fields['internal_name'].widget.attrs['placeholder'] = '[Internal Name]'
        # Add classes so the js can find them
        self.fields['event'].widget.attrs['class'] = 'event-select'
        self.fields['internal_name'].widget.attrs['class'] = 'event-name'
        self.fields['year'].widget.attrs['class'] = 'event-year'
        self.fields['month'].widget.attrs['class'] = 'event-month'
        self.fields['day'].widget.attrs['class'] = 'event-day'


    def clean(self):
        # Need to verify that even is None xor internal_name field is None, or they match
        cleaned_data = super().clean()
        event = cleaned_data.get("event")
        internal_name = cleaned_data.get("internal_name")
        if event and internal_name and event.internal_name != internal_name:
            raise forms.ValidationError(
                "You must either select an existing event or enter a new event name, not both."
            )
        if not event and not internal_name:
            raise forms.ValidationError(
                "You must either select an existing event or enter a new event name."
            )
        
        # Check for duplicate event names on new events
        if internal_name and not event:
            if self.viewer.timeline.events.filter(internal_name=internal_name).exists():
                raise forms.ValidationError(
                    "An event with this name already exists."
                )
        return cleaned_data


    def save(self, *args, **kwargs):
        # Three cases:
        # 1. This is an existing description for an existing event
        # 2. This is a new description for an existing event
        # 3. This is a new description for a new event


        # Case 1: This is an existing description for an existing event
        if self.instance.pk and self.instance.event:
            self.instance.event.year = self.cleaned_data['year']
            self.instance.event.month = self.cleaned_data['month']
            self.instance.event.day = self.cleaned_data['day']
            self.instance.event.internal_name = self.cleaned_data['internal_name']
            self.instance.event.save()

        # Case 2: This is a new description for an existing event
        elif not self.instance.pk and self.cleaned_data['event']:
            self.instance.event = self.cleaned_data['event']

        # Case 3: This is a new description for a new event
        elif not self.instance.pk and self.cleaned_data['event'] is None:
            year = self.cleaned_data['year']
            month = self.cleaned_data['month']
            day = self.cleaned_data['day']
            internal_name = self.cleaned_data['internal_name']
            self.instance.event = TimelineEvent.objects.create(year=year, month=month, day=day, timeline=self.viewer.timeline, internal_name=internal_name)
            self.instance.event.save()

        else:
            raise Exception("This should never happen")

        return super().save(*args, **kwargs)


TimelineEventDescriptionFormSet = forms.inlineformset_factory(
    TimelineViewer,
    TimelineEventDescription,
    form=TimelineEventDescriptionForm,
    fields=('description', 'year', 'month', 'day', 'event'),
    extra=5,
    can_delete=True,
    can_delete_extra=False,
)