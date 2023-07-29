    # Untested urls.py:
    # url(r'^writing/([^/]+)/sheetsgrid/$', garhdony_app.views_game_design.writing_game_sheets_grid,
    #     name='game_writer_sheets_grid'),
    # url(r'^writing/([^/]+)/timeline/$', garhdony_app.views_game_design.writing_game_timeline,
    #     name='game_writer_timeline'),
    # url(r'^writing/([^/]+)/sheetsgrid/modify/$', garhdony_app.views_game_design.sheets_grid_modify,
    #     name='sheets_grid_modify'),
    # url(r'^writing/([^/]+)/characters/table/$', garhdony_app.views_game_design.writing_characters_table,
    #     name='game_writer_characters_table'),
    # url(r'^writing/([^/]+)/sheet/new/$', garhdony_app.views_game_design.writer_new_sheet, name='new_sheet'),
    # url(r'^writing/([^/]+)/sheet/delete/$', garhdony_app.views_game_design.delete_sheet, name='delete_sheet'),
    # url(r'^writing/([^/]+)/character/new/$', garhdony_app.views_game_design.new_character, name='new_character'),
    # url(r'^writing/([^/]+)/character/delete/$', garhdony_app.views_game_design.delete_character, name='delete_character'),
    # url(r'^writing/([^/]+)/NPC/([^/]+)/$', garhdony_app.views_game_design.writing_npc, name='writing_npc'),
    # url(r'^writing/([^/]+)/sheet/([^/]+)/$', garhdony_app.views_game_design.writer_sheet, name='writer_sheet'),
    # url(r'^([^/]+)/character/([^/]+)/contacts/delete$', garhdony_app.views_game_design.character_contacts_delete,
    #     name='character_contacts_delete'),
    # url(r'^add/title_obj/$', garhdony_app.views_game_design.add_title, name='add_title'),
    # url(r'^writing/([^/]+)/search/$', garhdony_app.views_game_design.search, name='search'),
    # url(r'^writing/([^/]+)/recent_changes/$', garhdony_app.views_game_design.recent_changes, name='recent_changes'),

import os
import shutil
from django.test import TestCase
from garhdony_app import models
from garhdony_app.assign_writer_game import assign_writer_game
from garhdony_app.tests.setup_test_db import setup_test_db
from django.contrib.auth.models import User, Group


class GameDesignNotLoggedInTest(TestCase):
    def test_not_logged_in(self):
        response = self.client.get("/writing/")
        self.assertRedirects(response, "/login/?next=/writing/")

class NongameDesignViewsTest(TestCase):
    def setUp(self):
        setup_test_db()
        game = models.GameInstance.objects.get(name="TestGame")
        # Add a writer on the game.
        self.writer = User.objects.create_user(username="writer", password="writer")
        Group.objects.get(name='Writers').user_set.add(self.writer)
        assign_writer_game(self.writer, game)

        self.client.login(username="writer", password="writer")

    def test_writing_home(self):
        response = self.client.get("/writing/")
        self.assertContains(response, "TestGame", status_code=200)

    def test_writing_new_game(self):
        response = self.client.get("/writing/new")
        self.assertEqual(response.status_code, 200)
        # Check the form is there.
        self.assertContains(response, "id_name")
    
        # TODO this file system access isn't the best thing.
        if os.path.exists("media/TestGameNew"):
            shutil.rmtree("media/TestGameNew")
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

    def test_writing_clone_game(self):
        original_game = models.GameInstance.objects.get(name="TestGame")
        # Add a non-first-name generizedname
        some_character = original_game.characters.all()[0]
        some_name = models.GenderizedName(male="M", female="F", character=some_character)
        some_name.save()

        # TODO this file system access isn't the best thing.
        if os.path.exists("media/TestGameNew"):
            shutil.rmtree("media/TestGameNew")
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
        
class GameDesignViewsTest(TestCase):
    def setUp(self) -> None:
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
        # TODO this file system access isn't the best thing.
        if os.path.exists("media/TestGameNew"):
            shutil.rmtree("media/TestGameNew")
        new_game = models.GameInstance(name="TestGameNew", template=models.GameTemplate.objects.get(name="TestGameTemplate"))
        new_game.save()
        response = self.client.get("/writing/TestGameNew/")
        self.assertEqual(response.status_code, 404)

    def test_writing_sheets_grid(self):
        response = self.client.get(f"/writing/{self.game.name}/sheets/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.game.name)
        for sheet in models.Sheet.objects.filter(game=self.game):
            self.assertContains(response, sheet.filename)
        for character in models.PlayerCharacter.objects.filter(game=self.game):
            self.assertContains(response, character.first_name())

        # check sidebar
        self.assert_writer_game_leftbar(response)
    
