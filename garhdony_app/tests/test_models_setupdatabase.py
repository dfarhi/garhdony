from django.test import TestCase
from garhdony_app.models import SheetColor, SheetType, setup_database

class TestSetupDatabase(TestCase):
    def setUp(self):
        setup_database()

    def test_sheet_colors(self):
        available_colors = SheetColor.objects.all()
        self.assertEqual(set(c.name for c in available_colors), {'Bluesheet', 'Yellowsheet', 'Greensheet', 'In-game Document'})

    def test_sheet_types(self):
        available_types = SheetType.objects.all()
        self.assertEqual(set(t.name for t in available_types), {'Story', 'Details', 'Supplement'})

