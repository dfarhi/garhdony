    # Untested urls.py:
    # url(r'^writing/([^/]+)/timeline/$', garhdony_app.views_game_design.writing_game_timeline,
    #     name='game_writer_timeline'),
    # url(r'^writing/([^/]+)/sheetsgrid/modify/$', garhdony_app.views_game_design.sheets_grid_modify,
    #     name='sheets_grid_modify'),
    # url(r'^writing/([^/]+)/character/new/$', garhdony_app.views_game_design.new_character, name='new_character'),
    # url(r'^writing/([^/]+)/character/delete/$', garhdony_app.views_game_design.delete_character, name='delete_character'),
    # url(r'^writing/([^/]+)/sheet/([^/]+)/$', garhdony_app.views_game_design.writer_sheet, name='writer_sheet'),
    # url(r'^([^/]+)/character/([^/]+)/contacts/delete$', garhdony_app.views_game_design.character_contacts_delete,
    #     name='character_contacts_delete'),
    # url(r'^add/title_obj/$', garhdony_app.views_game_design.add_title, name='add_title'),
    # url(r'^writing/([^/]+)/search/$', garhdony_app.views_game_design.search, name='search'),
    # url(r'^writing/([^/]+)/recent_changes/$', garhdony_app.views_game_design.recent_changes, name='recent_changes'),

from io import BytesIO
import os
import shutil

import tempfile
from django.conf import settings
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from garhdony_app import models
from garhdony_app.assign_writer_game import assign_writer_game
from garhdony_app.tests.setup_test_db import setup_test_db
from django.contrib.auth.models import User, Group

def inline_edit_buttom_html(field):
    return f"""<form action="" method="get" style="display:inline"><input type="hidden" name="Edit" value="{field}"><input class="edit_button" type="submit" value=Edit></form>"""

class GameDesignNotLoggedInTest(TestCase):
    def test_not_logged_in(self):
        response = self.client.get("/writing/")
        self.assertRedirects(response, "/login/?next=/writing/")

class GameDesignViewsTestCase(TestCase):
    def setUp(self) -> None:
        settings.MEDIA_ROOT=tempfile.mkdtemp()
        setup_test_db()
        self.game = models.GameInstance.objects.get(name="TestGame")
        # Add a writer on the game.
        self.writer = User.objects.create_user(username="writer", password="writer")
        Group.objects.get(name='Writers').user_set.add(self.writer)
        assign_writer_game(self.writer, self.game)

        self.client.login(username="writer", password="writer")

    def assert_writer_game_leftbar(self, response):
        self.assertContains(response, "Game Homepage")
        self.assertContains(response, "Big Sheets Grid")
        self.assertContains(response, "Characters Grid")
        self.assertContains(response, "Logistics Table")
        self.assertContains(response, "Recent Changes")
        self.assertContains(response, "Game Search")
        self.assertContains(response, "Website Bugs")

class NongameDesignViewsTest(GameDesignViewsTestCase):
    def test_writing_home(self):
        response = self.client.get("/writing/")
        self.assertContains(response, "TestGame", status_code=200)

    def test_writing_new_game(self):
        response = self.client.get("/writing/new")
        self.assertEqual(response.status_code, 200)
        # Check the form is there.
        self.assertContains(response, "id_name")
    
        response = self.client.post("/writing/new", 
                                    {"Create": "True", 
                                     "name": "TestGameNew", 
                                     "template": models.GameTemplate.objects.get(name="TestGameTemplate").id, 
                                     "usernamesuffix": "T", 
                                     "writers": self.writer.id})
        self.assertRedirects(response, "/writing/TestGameNew/")
        # Check the game was created.
        game = models.GameInstance.objects.get(name="TestGameNew")
        self.assertEqual(game.name, "TestGameNew")
        self.assertEqual(game.template.name, "TestGameTemplate")
        self.assertEqual(game.usernamesuffix, "T")
        # chech media path was created.
        self.assertTrue(os.path.exists(game.abs_media_directory))
        self.assertTrue(os.path.exists(game.abs_sheets_directory))
        self.assertTrue(os.path.exists(game.abs_photo_directory))

    def test_writing_clone_game(self):
        original_game = models.GameInstance.objects.get(name="TestGame")
        # Add a non-first-name generizedname
        some_character = original_game.characters.all()[0]
        some_name = models.GenderizedName(male="M", female="F", character=some_character)
        some_name.save()

        response = self.client.post("/writing/new",
                                    {"Clone": "True", 
                                     "source": original_game.id,
                                     "new_name": "TestGameNew", 
                                     "username_suffix": "T"})
        self.assertRedirects(response, "/writing/TestGameNew/")
        # Check the game was created.
        new_game = models.GameInstance.objects.get(name="TestGameNew")
        self.assertEqual(new_game.name, "TestGameNew")
        self.assertEqual(new_game.usernamesuffix, "T")
        # Check the new_game has the same sheets as the clone source.
        self.assertEqual(new_game.sheets.count(), original_game.sheets.count())
        for sheet in original_game.sheets.all():
            clone = new_game.sheets.get(filename=sheet.filename)
            # Check they are disconnected
            self.assertNotEqual(clone.id, sheet.id)

        # Check the new_game has the same characters as the clone source.
        self.assertEqual(new_game.characters.count(), original_game.characters.count())
        for character in original_game.characters.all():
            clone = new_game.characters.get(last_name=character.last_name)
            self.assertEqual(clone.name(), character.name())
            self.assertEqual(clone.genderized_names.count(), character.genderized_names.count())

            # Check references are right.
            self.assertEqual(clone.first_name_obj.character, clone)

            # Check they are disconnected
            self.assertNotEqual(clone.id, character.id)
            self.assertNotEqual(clone.first_name_obj, character.first_name_obj)
            
            # find our friend with the non-firstname generizedname
            if character == some_character:
                some_characters_clone = clone

        # Check a non-firstname genderized name
        self.assertEqual(some_characters_clone.genderized_names.filter(male="M").count(), 1)
        some_name.male = "M2"
        some_name.save()
        self.assertEqual(some_character.genderized_names.filter(male="M").count(), 0)
        self.assertEqual(some_characters_clone.genderized_names.filter(male="M").count(), 1)
        
# Make sure to use a separate media root for each test case function call.
class GameDesignViewsTest(GameDesignViewsTestCase):
    def test_writing_game_home(self):
        response = self.client.get(f"/writing/{self.game.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.game.name)

        #Check all characters listed
        for character in models.Character.objects.filter(game=self.game):
            self.assertContains(response, character.name())
        for sheet in models.Sheet.objects.filter(game=self.game):
            self.assertContains(response, sheet.filename)

        # check sidebar
        self.assert_writer_game_leftbar(response)

    def test_writing_game_home_no_game(self):
        response = self.client.get("/writing/NonExistantGame/")
        self.assertEqual(response.status_code, 404)
    
    def test_writing_game_home_no_access(self):
        # Create a new game, but don't add the writer to it.
        new_game = models.GameInstance(name="TestGameNew", template=models.GameTemplate.objects.get(name="TestGameTemplate"))
        new_game.save()
        response = self.client.get("/writing/TestGameNew/")
        self.assertEqual(response.status_code, 404)

    def test_writing_sheets_grid(self):
        response = self.client.get(f"/writing/{self.game.name}/sheetsgrid/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.game.name)
        for sheet in models.Sheet.objects.filter(game=self.game):
            self.assertContains(response, sheet.filename)
        for character in models.PlayerCharacter.objects.filter(game=self.game):
            self.assertContains(response, character.first_name())

        # check sidebar
        self.assert_writer_game_leftbar(response)
    
    def test_writing_characters_grid(self):
        response = self.client.get(f"/writing/{self.game.name}/characters/table/")
        self.assertEqual(response.status_code, 200)
        # check sidebar
        self.assert_writer_game_leftbar(response)

        self.assertContains(response, self.game.name)
        for character in models.PlayerCharacter.objects.filter(game=self.game):
            self.assertContains(response, character.first_name())
            self.assertContains(response, character.last_name)

class NPCEditingTest(GameDesignViewsTestCase):
    def test_writing_npc_page_loads(self):
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        response = self.client.get(f"/writing/{self.game.name}/NPC/{character.id}/")
        self.assertEqual(response.status_code, 200)
        # check sidebar
        self.assert_writer_game_leftbar(response)

        self.assertContains(response, character.first_name())
        self.assertContains(response, character.last_name)
        self.assertContains(response, character.notes)

        # edit forms
        self.assertContains(response, inline_edit_buttom_html("notes"), html=True)
        self.assertContains(response, inline_edit_buttom_html("photo"), html=True)
        self.assertContains(response, inline_edit_buttom_html("Metadata"), html=True)

    def test_writing_npc_page_edit_notes(self):
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        # Check the edit form loads
        response = self.client.get(f"/writing/{self.game.name}/NPC/{character.id}/", {"Edit": "notes"})
        self.assertEqual(response.status_code, 200)
        # check sidebar
        self.assert_writer_game_leftbar(response)

        # Check there's a form with a field for notes
        self.assertContains(response, "id_notes")

        # submit a change
        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", {"Save": "notes", "notes": "New Notes"})
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.notes.render(), "New Notes")

    def test_writing_npc_page_edit_photo(self):
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        # Check the edit form loads
        response = self.client.get(f"/writing/{self.game.name}/NPC/{character.id}/", {"Edit": "photo"})
        self.assertEqual(response.status_code, 200)
        # Check there's a form with a field for photo
        self.assertContains(response, "id_photo")

        # submit a change
        f = BytesIO()
        from PIL import Image
        image = Image.new("RGB", (100, 100))
        image.save(f, 'png')
        f.seek(0)
        photo = SimpleUploadedFile("test.png", f.read(), content_type="image/png")
        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", {"Save": "photo", "photo": photo})

        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.photo.open().read(), photo.open().read())

        # check redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/writing/{self.game.name}/NPC/{character.id}/")

    def test_writing_npc_page_edit_metadata_name(self):
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        # Check the edit form loads
        response = self.client.get(f"/writing/{self.game.name}/NPC/{character.id}/", {"Edit": "Metadata"})
        self.assertEqual(response.status_code, 200)
        # check sidebar
        self.assert_writer_game_leftbar(response)

        # Check the form fields
        self.assertContains(response, "id_first_male")
        self.assertContains(response, "id_first_female")
        self.assertContains(response, "id_last_name")
        self.assertContains(response, "id_title")
        # button to add new title. Not sure how to check if clicking it does anything.
        self.assertTrue("plus.jpeg" in response.content.decode('utf-8'))

        # submit a change
        new_title = models.GenderizedKeyword.objects.filter(category="title").first()
        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", 
                                    {"Save": "Metadata",
                                     "first_male": "NewFirstMale",
                                     "first_female": "NewFirstFemale",
                                     "last_name": "NewLastName",
                                     "gender_field": "F",
                                     "title_obj": new_title.id
                                     })
        self.assertEqual(response.status_code, 302)
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.first_name_obj.male, "NewFirstMale")
        self.assertEqual(character.first_name_obj.female, "NewFirstFemale")
        self.assertEqual(character.last_name, "NewLastName")
        self.assertEqual(character.gender(), "F")
        self.assertEqual(character.title_obj, new_title)
        self.assertEqual(character.first_name(), "NewFirstFemale")

    def post_dict(self, gender_field, gender_linked_pc = None):
        result = {"Save": "Metadata",
            "first_male": "NewFirstMale",
            "first_female": "NewFirstFemale",
            "last_name": "NewLastName",
            "gender_field": gender_field,
            "title_obj": "",  # no title
        }
        if gender_linked_pc:
            result['gender_linked_pc'] = gender_linked_pc.id
        return result

    def test_writing_npc_page_genders_invalid_MF(self):
        """ Test setting gender to M or F while also setting gender_linked_pc"""
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        old_first_name = character.first_name()
        other_character = models.PlayerCharacter.objects.filter(game=self.game).first()

        for g in ["M", "F"]:
            response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict(g, gender_linked_pc=other_character))
            # Check that it didn't crash
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "For fixed gender, set blank PC")
            # Check that it didn't save
            character = models.NonPlayerCharacter.objects.get(id=character.id)
            self.assertEqual(character.first_name(), old_first_name)

    def test_writing_npc_page_genders_invalid_OPEQ(self):
        """ Test setting gender to OP or EQ while not setting gender_linked_pc"""
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        old_first_name = character.first_name()
        for g in ["OP", "EQ"]:
            response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict(g, gender_linked_pc=None))
            # Check that it didn't crash
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Choose a PC")
            # Check that it didn't save
            character = models.NonPlayerCharacter.objects.get(id=character.id)
            self.assertEqual(character.first_name(), old_first_name)

    def test_writing_npc_page_genders_valid_MF(self):
        """ Test setting gender to M or F correctly"""
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()

        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict("F"))
        self.assertEqual(response.status_code, 302)
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "F")
        self.assertEqual(character.first_name(), "NewFirstFemale")

        self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict("M"))
        self.assertEqual(response.status_code, 302)
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "M")
        self.assertEqual(character.first_name(), "NewFirstMale")

    def test_writing_npc_page_genders_valid_EQ(self):
        """ Test setting gender to EQ"""
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        other_character = models.PlayerCharacter.objects.filter(game=self.game).first()

        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict("EQ", gender_linked_pc=other_character))
        self.assertEqual(response.status_code, 302)
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        other_character.default_gender = "M"
        other_character.save()
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "M")
        other_character.default_gender = "F"
        other_character.save()
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "F")
                         
    def test_writing_npc_page_genders_valid_OP(self):
        """ Test setting gender to OP"""
        character = models.NonPlayerCharacter.objects.filter(game=self.game).first()
        other_character = models.PlayerCharacter.objects.filter(game=self.game).first()

        response = self.client.post(f"/writing/{self.game.name}/NPC/{character.id}/", self.post_dict("OP", gender_linked_pc=other_character))
        self.assertEqual(response.status_code, 302)
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        other_character.default_gender = "F"
        other_character.save()
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "M")
        other_character.default_gender = "M"
        other_character.save()
        character = models.NonPlayerCharacter.objects.get(id=character.id)
        self.assertEqual(character.gender(), "F")

class SheetsTest(GameDesignViewsTestCase):
    def test_sheet_create_delete(self):
        """ Test that we can create and delete a sheet """
        for content_type in ["html", "image/png", "application/pdf"]:
            # Load sheet creation form
            response = self.client.get(f"/writing/{self.game.name}/sheet/new/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Create Sheet")
            self.assertContains(response, "Sheet type")
            self.assertContains(response, "id_sheet_type")
            self.assertContains(response, "Sheet status")
            self.assertContains(response, "id_sheet_status")
            self.assertContains(response, "Color")
            self.assertContains(response, "id_color")
            self.assertContains(response, "Name")
            self.assertContains(response, "id_name")
            self.assertContains(response, "id_filename")

            # Create sheet
            type = models.SheetType.objects.first()
            response = self.client.post(f"/writing/{self.game.name}/sheet/new/", {
                "name": "Test Sheet", 
                "sheet_type": type.id,
                "sheet_status": models.SheetStatus.objects.first().id,
                "color": models.SheetColor.objects.first().id,
                "filename": "Test Sheet",
                "content_type": content_type,
            })
            self.assertEqual(response.status_code, 302)
            sheet = models.Sheet.objects.get(game=self.game, name="Test Sheet")
            self.assertEqual(sheet.sheet_type, type)

            response = self.client.get(f"/writing/{self.game.name}/sheet/delete/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Delete Sheet")
            self.assertContains(response, "cannot be undone!")
            self.assertContains(response, "id_sheet")

            # Delete sheet
            sheet_path = sheet.full_path
            #create dummy file there to test deletion
            with open(sheet_path, "w") as f:
                f.write("test")

            response = self.client.post(f"/writing/{self.game.name}/sheet/delete/", {"sheet": sheet.id})
            self.assertEqual(response.status_code, 302)
            self.assertFalse(models.Sheet.objects.filter(game=self.game, name="Test Sheet").exists())

            # check file was deleted
            self.assertFalse(os.path.exists(sheet_path))
    
    def test_sheet_view(self):
        """ Test that we can view a sheet's page """
        for sheet in models.Sheet.objects.filter(game=self.game):
            response = self.client.get(f"/writing/{self.game.name}/sheet/{sheet.filename}/")
            self.assertEqual(response.status_code, 200)
            
            # check  sidebar
            self.assert_writer_game_leftbar(response)

            self.assertContains(response, sheet.name.render())
            self.assertContains(response, sheet.sheet_type.name)
            self.assertContains(response, sheet.color.name)
            if sheet.sheet_status:
                self.assertContains(response, sheet.sheet_status.name)

            self.assertContains(response, inline_edit_buttom_html("Metadata"), html=True)
            self.assertContains(response, inline_edit_buttom_html("characters"), html=True)
            self.assertContains(response, "Write")
            self.assertContains(response, "History")

            for char in sheet.characters.all():
                self.assertContains(response, char.name())

    def test_sheet_edit_characters(self):
        """ Test that we can edit a sheet's characters """
        sheet = models.Sheet.objects.filter(game=self.game).first()
        response = self.client.get(f"/writing/{self.game.name}/sheet/{sheet.filename}/", {'Edit': 'characters'})
        self.assertEqual(response.status_code, 200)
        for char in models.PlayerCharacter.objects.filter(game=self.game):
            self.assertContains(response, char.name())
            self.assertContains(response, f'value="{char.id}"')

        char = models.PlayerCharacter.objects.filter(game=self.game).first()
        response = self.client.post(f"/writing/{self.game.name}/sheet/{sheet.filename}/", {
            "Save": "characters",
            "characters": [char.id],
        })
        self.assertEqual(response.status_code, 302)
        sheet = models.Sheet.objects.get(game=self.game, filename=sheet.filename)
        self.assertEqual(sheet.characters.count(), 1)
        self.assertEqual(sheet.characters.first(), char)

        response = self.client.post(f"/writing/{self.game.name}/sheet/{sheet.filename}/", {
            "Save": "characters",
            "characters": [],
        })
        self.assertEqual(response.status_code, 302)
        sheet = models.Sheet.objects.get(game=self.game, filename=sheet.filename)
        self.assertEqual(sheet.characters.count(), 0)

    def test_sheet_edit_metadata(self):
        """ Test that we can edit a sheet's metadata """
        sheet = models.Sheet.objects.filter(game=self.game).first()
        response = self.client.get(f"/writing/{self.game.name}/sheet/{sheet.filename}/", {'Edit': 'Metadata'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Name")
        self.assertContains(response, "id_name")
        self.assertContains(response, "Sheet type")
        self.assertContains(response, "id_sheet_type")
        self.assertContains(response, "Sheet status")
        self.assertContains(response, "id_sheet_status")
        self.assertContains(response, "Color")
        self.assertContains(response, "id_color")
        self.assertContains(response, "unique")
        self.assertContains(response, "id_filename")
        self.assertContains(response, "Hidden")
        self.assertContains(response, "id_hidden")
        self.assertContains(response, "Preview description")
        self.assertContains(response, "id_preview_description")
        

        new_color = models.SheetColor.objects.exclude(id=sheet.color.id).first()
        new_type = models.SheetType.objects.exclude(id=sheet.sheet_type.id).first()
        # no need to exclude sheet status, as it's None to start with
        new_status = models.SheetStatus.objects.first()
        response = self.client.post(f"/writing/{self.game.name}/sheet/{sheet.filename}/", {
            "Save": "Metadata",
            "name": "Test Sheet",
            "sheet_type": new_type.id,
            "sheet_status": new_status.id,
            "color": new_color.id,
            "filename": "Test Sheet",
            "hidden": False,
            "preview_description": "Test description new",
        })
        self.assertEqual(response.status_code, 302)
        sheet = models.Sheet.objects.get(game=self.game, filename="Test Sheet")
        self.assertEqual(sheet.name.render(), "Test Sheet")
        self.assertEqual(sheet.sheet_type, new_type)
        self.assertEqual(sheet.sheet_status, new_status)
        self.assertEqual(sheet.color, new_color)
        self.assertFalse(sheet.hidden)
        self.assertEqual(sheet.preview_description.render(), "Test description new")