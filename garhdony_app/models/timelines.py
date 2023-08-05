from typing import Any
from garhdony_app.LARPStrings import LARPTextField
from django.db import models

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", 
                        "October", "November", "December"]

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
    name = models.CharField(max_length=100)


class TimelineEvent(models.Model):
    """
    An event in the timeline
    """
    class Meta:
        ordering = ["timeline", "year", "month", "day"]
        unique_together = ("timeline", "internal_name")

    timeline = models.ForeignKey(Timeline, related_name="events", on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField(null=True)
    day = models.IntegerField(null=True)
    internal_name = models.TextField()

    def __str__(self):
        return self.internal_name

    def date(self):
        """
        Return the date of the event as a string.
        """
        if self.month is None:
            # e.g. 1276
            return str(self.year)
        month_str = MONTHS[self.month - 1]
        if self.day is None:
            # e.g. April 1276 (note that self.month is an int, so we need to convert it to a string e.g 1-> "January")
            return f"{month_str} {self.year}"
        return f"{self.day} {month_str} {self.year}"  # e.g. 12 April 1276


class TimelineEventDescription(models.Model):
    """
    An instance of one viewer seeing one event.
    """
    class Meta:
        unique_together = ("event", "viewer")
        ordering = ["event__timeline", "event__year", "event__month", "event__day"]

    event = models.ForeignKey(TimelineEvent, related_name="descriptions", on_delete=models.CASCADE)
    viewer = models.ForeignKey(TimelineViewer, related_name="descriptions", on_delete=models.CASCADE)
    description = LARPTextField()

    def __str__(self):
        return str(self.event) + " (" + self.viewer.name + ")"
    
