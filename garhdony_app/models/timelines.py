from garhdony_app.LARPStrings import LARPTextField
from django.db import models


class Timeline(models.Model):
    """
    An entire timeline with all the events in the world.
    There should be one of these per game.
    """
    name = models.CharField(max_length=100)
    def __str__(self):
        return f"{self.name} [Timeline]"


class TimelineViewer(models.Model):
    """
    One subset of the events with particular descriptions.
    Will be held by a single sheet.
    """
    timeline = models.ForeignKey(Timeline, related_name="viewers", on_delete=models.CASCADE)


class TimelineEvent(models.Model):
    """
    An event in the timeline
    """
    timeline = models.ForeignKey(Timeline, related_name="events", on_delete=models.CASCADE)
    date = models.DateField()
    default_description = LARPTextField()
    viewers = models.ManyToManyField(TimelineViewer, through="TimelineEventDescription")

    def __str__(self):
        return self.default_description.render()


class TimelineEventDescription(models.Model):
    """
    An instance of one viewer seeing one event.
    """
    class Meta:
        unique_together = ("event", "viewer")

    event = models.ForeignKey(TimelineEvent, related_name="descriptions", on_delete=models.CASCADE)
    viewer = models.ForeignKey(TimelineViewer, related_name="descriptions", on_delete=models.CASCADE)
    unique_description = LARPTextField()

    def __str__(self):
        return str(self.event) + " (" + self.sheet.filename + ")"

    @property
    def description(self):
        if self.unique_description == "":
            return self.event.default_description
        else:
            return self.unique_description