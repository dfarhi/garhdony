from django.test import TestCase
from garhdony_app.forms_game_design import CharacterDeleteForm, CharacterNewForm, SheetDeleteForm, SheetNewForm
from garhdony_app.models import GameInstance, GenderizedName, NonPlayerCharacter, PlayerCharacter, Sheet, SheetColor, SheetType
from garhdony_app.tests.setup_test_db import setup_test_db
from django.contrib.auth.models import User

class TestFormsGameDesign(TestCase):
    def setUp(self):
        setup_test_db()

    def test_new_sheet_valid(self):
        game = GameInstance.objects.get(name="Test Game")
        form = SheetNewForm(game, 
                            {'name': 'Test Sheet', 
                             'sheet_type': SheetType.objects.get(name="Story").pk, 
                             'color': SheetColor.objects.get(name="Bluesheet").pk,
                             'filename': 'test_sheet.txt',
                             'content_type': 'html',
                             })
        self.assertTrue(form.is_valid(), form.errors)
        form.save(game)

        # Check we have a sheet with the simple values we expect
        sheet: Sheet = Sheet.objects.get(name="Test Sheet")
        self.assertEqual(sheet.sheet_type.name, "Story")
        self.assertEqual(sheet.color.name, "Bluesheet")
        self.assertEqual(sheet.filename, "test_sheet.txt")
        self.assertEqual(sheet.content_type, "html")
        self.assertEqual(sheet.game, game)

        # Check trickier values
        self.assertTrue(sheet.hidden)
        self.assertFalse(sheet.ever_printed)
        self.assertIsNone(sheet.current_lock())

    def test_delete_sheet_valid(self):
        game = GameInstance.objects.get(name="Test Game")
        sheet: Sheet = Sheet.objects.get(name="Bluesheet Story 1")
        form = SheetDeleteForm(game, {'sheet': sheet.pk})
        self.assertTrue(form.is_valid(), form.errors)
        form.save(game)

        # Check the sheet is gone
        self.assertEqual(Sheet.objects.filter(name="Bluesheet Story 1").count(), 0)

        # Check other sheets are still there
        self.assertEqual(Sheet.objects.filter(name="Bluesheet Story 2").count(), 1)

    def test_new_npc_valid(self):
        game = GameInstance.objects.get(name="Test Game")
        form = CharacterNewForm({
            'first_male': 'Test First Male',
            'first_female': 'Test First Female',
            'last_name':  'Test Last Name',
            'char_type': 'NPC'})
        self.assertTrue(form.is_valid(), form.errors)
        form.save(game)

        # Check we have a character with the simple values we expect
        char = NonPlayerCharacter.objects.get(last_name="Test Last Name")
        self.assertEqual(char.last_name, "Test Last Name")

        # Set their gender and check first name
        char.gender_field = "F"
        self.assertEqual(char.name(), "Test First Female Test Last Name")

    def test_new_pc_valid(self):
        game = GameInstance.objects.get(name="Test Game")
        form = CharacterNewForm({
            'first_male': 'Test First Male',
            'first_female': 'Test First Female',
            'last_name':  'Test Last Name',
            'char_type': 'PC'})
        self.assertTrue(form.is_valid(), form.errors)
        form.save(game)

        # Check we have a character with the simple values we expect
        char = PlayerCharacter.objects.get(last_name="Test Last Name")
        self.assertEqual(char.last_name, "Test Last Name")

        # Set their gender and check first name
        char.default_gender = "F"
        char.save()
        self.assertEqual(char.name(), "Test First Female Test Last Name")        

        # Check consistency of their first name obj
        self.assertEqual(char.first_name_obj.character.pk, char.pk)

        # Check they have a sheet
        self.assertEqual(char.sheets.count(), 1)
        sheet = char.sheets.first()
        self.assertEqual(sheet.name.render(), char.name())
        self.assertEqual(sheet.sheet_type.name, "Story")
        self.assertEqual(sheet.color.name, "Yellowsheet")

        # Check they have a user
        User.objects.get(username=char.username)

    def test_delete_character_npc(self):
        npc = NonPlayerCharacter.objects.get(last_name="NPC1-Last")
        first_name_male = npc.first_name_obj.male
        self.assertEqual(GenderizedName.objects.filter(male=first_name_male).count(), 1)
        game = GameInstance.objects.get(name="Test Game")
        form = CharacterDeleteForm(game, {'character': npc.pk})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        # Check the character is gone
        self.assertEqual(NonPlayerCharacter.objects.filter(last_name="NPC1-Last").count(), 0)
        # Check the first name is gone.
        self.assertEqual(GenderizedName.objects.filter(male=first_name_male).count(), 0)
        # TODO: contacts

    def test_delete_character_pc(self):
        pc = PlayerCharacter.objects.get(last_name="PC1-Last")
        first_name_male = pc.first_name_obj.male
        game = GameInstance.objects.get(name="Test Game")
        form = CharacterDeleteForm(game, {'character': pc.pk})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        # Check the character is gone
        self.assertEqual(PlayerCharacter.objects.filter(last_name="PC1-Last").count(), 0)
        # But not another character
        self.assertEqual(PlayerCharacter.objects.filter(last_name="PC2-Last").count(), 1)
        # Check the first name is gone
        self.assertEqual(GenderizedName.objects.filter(male=first_name_male).count(), 0)
        # Check the user is gone
        self.assertEqual(User.objects.filter(username=pc.username).count(), 0)
        # TODO: contacts? timeline entries?