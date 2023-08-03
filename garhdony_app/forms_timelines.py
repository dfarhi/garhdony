from django import forms

from garhdony_app.models.timelines import TimelineViewer


class EditTimelineViewerForm(forms.ModelForm):
    class Meta:
        model = TimelineViewer
        fields = ["events"]
        