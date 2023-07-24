"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from garhdony_app.models import GameInstance,Character,PlayerProfile,Sheet

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

class SyncTests(TestCase):
    def test_sheet_character_sync(self):
        """
        Tests that every sheet belongs to the same game as its character.
        """
        for char in Character.objects.all():
            g = character.game
            for s in char.sheets():
                assertEqual(s.game, g)
