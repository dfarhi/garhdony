    # Untested urls.py:
    # url(r'^writing/([^/]+)/timeline/$', garhdony_app.views_game_design.writing_game_timeline,
    #     name='game_writer_timeline'),
    # url(r'^writing/([^/]+)/recent_changes/$', garhdony_app.views_game_design.recent_changes, name='recent_changes'),
    # url(r'^writing/([^/]+)/sheetsgrid/modify/$', garhdony_app.views_game_design.sheets_grid_modify, name='sheets_grid_modify'),

    # sheets - actual content part of it. Upload files, History tabs, Generate PDF, locks, plain html, etc

from io import BytesIO
import os

import tempfile
from typing import List
from django.conf import settings
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from garhdony_app import models
from garhdony_app.LARPStrings import LARPstring
from garhdony_app.assign_writer_game import assign_writer_game
from garhdony_app.tests.setup_test_db import setup_test_db
from django.contrib.auth.models import User, Group

def inline_edit_button_html(field, button_text="Edit"):
    return f"""<form action="" method="get" style="display:inline"><input type="hidden" name="Edit" value="{field}"><input class="edit_button" type="submit" value={button_text}></form>"""

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

        # Check right sidebar
        for field, button_text in [("Metadata", "Edit"), ("stats", "Add/Edit"), ("info_links", "Add/Edit"), ("Writers", "Add")]:
            self.assertContains(response, inline_edit_button_html(field=field, button_text=button_text), html=True)

        stats = models.CharacterStatType.objects.filter(game=self.game)
        assert len(stats) > 0, "Test game has no stats, not really testing anything."
        for stat in stats:
            self.assertContains(response, stat.name)

        info_links = models.GameInfoLink.objects.filter(game=self.game)
        assert len(info_links) > 0, "Test game has no info links, not really testing anything."
        for info_link in info_links:
            self.assertContains(response, f"""<a href="{info_link.link_url}">{info_link.label}</a>""", html=True)

    def test_writing_game_home_no_game(self):
        response = self.client.get("/writing/NonExistantGame/")
        self.assertEqual(response.status_code, 404)
    
    def test_writing_game_home_no_access(self):
        # Create a new game, but don't add the writer to it.
        new_game = models.GameInstance(name="TestGameNew", template=models.GameTemplate.objects.get(name="TestGameTemplate"))
        new_game.save()
        response = self.client.get("/writing/TestGameNew/")
        self.assertEqual(response.status_code, 404)

    def test_writer_game_home_edit_metadata(self):
        url = reverse("game_writer_home", args=[self.game.name])
        response = self.client.get(url, {"Edit": "Metadata"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_name")
        self.assertContains(response, "id_usernamesuffix")
        self.assertContains(response, "id_preview_mode")
        self.assertContains(response, "id_complete")

        # check sidebar
        self.assert_writer_game_leftbar(response)

        # record original values
        old_name = self.game.name
        a_character = self.game.characters.filter(char_type="PC").first().cast()
        old_username = a_character.user.username
        old_media_dir = self.game.abs_media_directory

        #Post some data
        response = self.client.post(url, {
            "Save": "Metadata", 
            "name": "NewName", 
            "usernamesuffix": "New", 
            "preview_mode": "True",
            "complete": "True"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("game_writer_home", args=["NewName"]))

        # Check the game was updated.
        game = models.GameInstance.objects.get(name="NewName")
        self.assertEqual(game.name, "NewName")
        self.assertEqual(game.usernamesuffix, "New")
        self.assertEqual(game.preview_mode, True)
        self.assertEqual(game.complete, True)
        self.assertEqual(models.GameInstance.objects.filter(name=old_name).count(), 0)

        # Check the usernames changed
        a_character.refresh_from_db()
        self.assertNotEqual(a_character.user.username, old_username)
        self.assertEqual(models.User.objects.filter(username=old_username).count(), 0)
        self.assertEqual(models.User.objects.filter(username=a_character.user.username).count(), 1)

        # Check the media moved
        self.assertNotEqual(game.abs_media_directory, old_media_dir)
        self.assertTrue(os.path.exists(game.abs_media_directory))
        self.assertFalse(os.path.exists(old_media_dir))

    def test_writer_game_home_edit_stats(self):
        url = reverse("game_writer_home", args=[self.game.name])
        response = self.client.get(url, {"Edit": "stats"})
        self.assertEqual(response.status_code, 200)
        previous_stats = models.CharacterStatType.objects.filter(game=self.game)
        # check the form is there
        for i, stat in enumerate(previous_stats):
            self.assertContains(response, f"""<input type="text" name="form-{i}-name" value="{stat.name}" maxlength="50" id="id_form-{i}-name">""")
        # check spot for new stat
        n = len(previous_stats)
        self.assertContains(response, f"""<input type="text" name="form-{n}-name" maxlength="50" id="id_form-{n}-name">""")

        # submit some data
        assert n == 2, "This test kind of assumes test game has 2 stats."
        response = self.client.post(url, {
            "Save": "stats",
            "form-TOTAL_FORMS": n+1,
            "form-INITIAL_FORMS": n,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-game": self.game.id,  # this is a hidden field
            "form-0-id": previous_stats[0].id,  # this is a hidden field
            "form-0-name": "RenameStat",
            "form-0-optional": True,
            "form-0-DELETE": False,
            "form-1-game": self.game.id,  # this is a hidden field
            "form-1-id": previous_stats[1].id,  # this is a hidden field
            "form-1-name": previous_stats[1].name,
            "form-1-optional": False,
            "form-1-DELETE": True,  # delete ths one.
            "form-2-game": self.game.id,  # this is a hidden field
            "form-2-id": "",  # this is a hidden field
            "form-2-name": "NewStat2",
            "form-2-optional": False,
            "form-2-DELETE": False,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # check the stats were updated
        self.assertEqual(models.CharacterStatType.objects.filter(game=self.game).count(), 2)

        # First stat should be renamed
        self.assertEqual(models.CharacterStatType.objects.filter(game=self.game, name="RenameStat").count(), 1)
        self.assertEqual(models.CharacterStatType.objects.filter(game=self.game, name=previous_stats[0].name).count(), 0)
        self.assertEqual(models.CharacterStatType.objects.get(game=self.game, name="RenameStat").optional, True)

        # Second stat should be deleted
        self.assertEqual(models.CharacterStatType.objects.filter(game=self.game, name=previous_stats[1].name).count(), 0)
        # Along with all its values
        self.assertEqual(models.CharacterStat.objects.filter(stat_type=previous_stats[1]).count(), 0)

        # Third stat should be added
        self.assertEqual(models.CharacterStatType.objects.filter(game=self.game, name="NewStat2").count(), 1)
        # and have one instance per pc
        self.assertEqual(models.CharacterStat.objects.filter(stat_type__name="NewStat2").count(), models.Character.objects.filter(game=self.game).count())
    
    def test_writer_game_home_edit_links(self):
        url = reverse("game_writer_home", args=[self.game.name])
        response = self.client.get(url, {"Edit": "info_links"})
        self.assertEqual(response.status_code, 200)
        previous_links = models.GameInfoLink.objects.filter(game=self.game)
        # check the form is there
        for i, link in enumerate(previous_links):
            self.assertContains(response, f"""<input type="text" name="form-{i}-link_url" value="{link.link_url}" maxlength="200" id="id_form-{i}-link_url">""")
            self.assertContains(response, f"""<input type="text" name="form-{i}-label" value="{link.label}" maxlength="50" id="id_form-{i}-label">""")

        # check spot for new link
        n = len(previous_links)
        self.assertContains(response, f"""<input type="text" name="form-{n}-link_url" maxlength="200" id="id_form-{n}-link_url">""")
        self.assertContains(response, f"""<input type="text" name="form-{n}-label" maxlength="50" id="id_form-{n}-label">""")

        # submit some data
        assert n == 2, "This test kind of assumes test game has 2 links."
        response = self.client.post(url, {
            "Save": "info_links",
            "form-TOTAL_FORMS": n+1,
            "form-INITIAL_FORMS": n,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-game": self.game.id,  # this is a hidden field
            "form-0-id": previous_links[0].id,  # this is a hidden field
            "form-0-link_url": "http://newlink.com",
            "form-0-label": "New Link",
            "form-0-DELETE": False,
            "form-1-game": self.game.id,  # this is a hidden field
            "form-1-id": previous_links[1].id,  # this is a hidden field
            "form-1-link_url": previous_links[1].link_url,
            "form-1-label": previous_links[1].label,
            "form-1-DELETE": True,  # delete ths one.
            "form-2-game": self.game.id,  # this is a hidden field
            "form-2-id": "",  # this is a hidden field
            "form-2-link_url": "http://newlink2.com",
            "form-2-label": "New Link 2",
            "form-2-DELETE": False,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # check the links were updated
        self.assertEqual(models.GameInfoLink.objects.filter(game=self.game).count(), 2)
        
        # First link should be updated
        self.assertEqual(models.GameInfoLink.objects.filter(game=self.game, link_url="http://newlink.com").count(), 1)
        self.assertEqual(models.GameInfoLink.objects.filter(game=self.game, link_url=previous_links[0].link_url).count(), 0)

        # Second link should be deleted
        self.assertEqual(models.GameInfoLink.objects.filter(game=self.game, link_url=previous_links[1].link_url).count(), 0)

        # Third link should be added
        self.assertEqual(models.GameInfoLink.objects.filter(game=self.game, link_url="http://newlink2.com").count(), 1)

    def test_writer_game_home_edit_writers(self):
        url = reverse("game_writer_home", args=[self.game.name])
        # make some more writers
        this_game_writer2 = User.objects.create_user(username="this_game_writer2", password="writer")
        Group.objects.get(name='Writers').user_set.add(this_game_writer2)
        assign_writer_game(this_game_writer2, self.game)
                                              
        other_game_writer1 = User.objects.create_user(username="other_game_writer1", password="writer")
        Group.objects.get(name='Writers').user_set.add(other_game_writer1)
        other_game_writer2 = User.objects.create_user(username="other_game_writer2", password="writer")
        Group.objects.get(name='Writers').user_set.add(other_game_writer2)

        response = self.client.get(url, {"Edit": "Writers"})
        self.assertEqual(response.status_code, 200)
        # check we can add writers
        self.assertContains(response, "other_game_writer1")
        self.assertContains(response, "other_game_writer2")
        # but not existing writers
        self.assertNotContains(response, "this_game_writer2", msg_prefix=response.content.decode())

        # submit some data
        response = self.client.post(url, {
            "Save": "Writers",
            "writers": [other_game_writer1.id],
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)
        # check this writer has permission on this game
        self.assertTrue(other_game_writer1.has_perm("writer", self.game))
        # check other writers are in the right states still
        self.assertFalse(other_game_writer2.has_perm("writer", self.game))
        self.assertTrue(this_game_writer2.has_perm("writer", self.game))
        self.assertTrue(self.writer.has_perm("writer", self.game))

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

    def test_add_title(self):
        response = self.client.get(f"/add/title_obj/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Title")
        self.assertContains(response, "id_male")
        self.assertContains(response, 'id_female')
        self.assertContains(response, """<input type="hidden" name="category" value="title" id="id_category">""", html=True)

        response = self.client.post(f"/add/title_obj/", {
            'male': 'TestMaleTitle',
            'female': 'TestFemaleTitle',
            'category': 'title',
        })
        title = models.GenderizedKeyword.objects.get(male="TestMaleTitle")
        self.assertEqual(title.female, "TestFemaleTitle")
        self.assertEqual(title.category, "title")

    def test_add_title_duplicate(self):
        title = models.GenderizedKeyword.objects.filter(category="title").first()
        response = self.client.post(f"/add/title_obj/", {
            'male': title.male,
            'female': title.female,
            'category': 'title',
        })
        self.assertContains(response, "already exists")
        self.assertEqual(models.GenderizedKeyword.objects.filter(category="title", male=title.male, female=title.female).count(), 1)

class GameSearchViewsTest(GameDesignViewsTestCase):
    def assert_sheet_in_results(self, response, sheet, is_in=True, **kwargs):
        entry = f"""<a href="{reverse("writer_sheet", args=[self.game.name, sheet.filename])}"> {sheet.filename}</a>"""
        if is_in:
            self.assertContains(response, entry, html=True, **kwargs)
        else:
            self.assertNotContains(response, entry, html=True, **kwargs)

    def test_writing_search_form(self):
        response = self.client.get(f"/writing/{self.game.name}/search/")
        self.assertEqual(response.status_code, 200)
        # check sidebar
        self.assert_writer_game_leftbar(response)
        self.assertContains(response, self.game.name)
        self.assertContains(response, "Search")
        self.assertContains(response, "id_query")
        self.assertContains(response, "id_raw")
        self.assertContains(response, "id_wholewords")
        self.assertContains(response, "id_matchcase")

    def test_writing_search_simple(self):
        sheet1 = models.Sheet.objects.filter(game=self.game).first()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo bar baz.")).save()

        # Search for "foo"
        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "baz",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1)

    def test_writing_search_multiple(self):
        sheet1 = models.Sheet.objects.filter(game=self.game).first()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo bar.")).save()
        sheet2 = models.Sheet.objects.filter(game=self.game).last()
        models.SheetRevision(sheet=sheet2, content=LARPstring("foo baz.")).save()

        # Search for "foo"
        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "foo",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1)
        self.assert_sheet_in_results(response, sheet2)

        # search for bar
        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "bar",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1)
        self.assert_sheet_in_results(response, sheet2, is_in=False)

    def test_writing_search_matchcase(self):
        sheet1 = models.Sheet.objects.filter(game=self.game).first()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo.")).save()
        sheet2 = models.Sheet.objects.filter(game=self.game).last()
        models.SheetRevision(sheet=sheet2, content=LARPstring("Foo.")).save()

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "foo",
            "raw": False,
            "wholewords": False,
            "matchcase": True,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1, msg_prefix=response.content.decode("utf-8"))
        self.assert_sheet_in_results(response, sheet2, is_in=False)

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "Foo",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1, msg_prefix=response.content.decode("utf-8"))
        self.assert_sheet_in_results(response, sheet2)

    def test_writing_search_wholewords(self):
        sheet1 = models.Sheet.objects.filter(game=self.game).first()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo bar.")).save()
        sheet2 = models.Sheet.objects.filter(game=self.game).last()
        models.SheetRevision(sheet=sheet2, content=LARPstring("foo barbaz.")).save()

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "bar",
            "raw": False,
            "wholewords": True,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1)
        self.assert_sheet_in_results(response, sheet2, is_in=False)

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "bar",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, sheet1.filename)
        self.assertContains(response, sheet2.filename)

    def test_writing_search_old_revision(self):
        sheet1 = models.Sheet.objects.filter(game=self.game).first()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo bar.")).save()
        models.SheetRevision(sheet=sheet1, content=LARPstring("foo baz.")).save()

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "bar",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
        })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1, is_in=False)

        response = self.client.post(f"/writing/{self.game.name}/search/", {
            "query": "baz",
            "raw": False,
            "wholewords": False,
            "matchcase": False,
        })
        self.assertEqual(response.status_code, 200)
        self.assert_sheet_in_results(response, sheet1)

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
        self.assertContains(response, inline_edit_button_html("notes"), html=True)
        self.assertContains(response, inline_edit_button_html("photo"), html=True)
        self.assertContains(response, inline_edit_button_html("Metadata"), html=True)

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

    def test_writing_npc_page_edit_metadata(self):
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

            self.assertContains(response, inline_edit_button_html("Metadata"), html=True)
            self.assertContains(response, inline_edit_button_html("characters"), html=True)
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

class CharacterCreateDeleteTest(GameDesignViewsTestCase):
    def test_npc_create_delete(self):
        """ Test that we can create and delete a player character """
        response = self.client.get(f"/writing/{self.game.name}/character/new/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_first_male")
        self.assertContains(response, "id_first_female")
        self.assertContains(response, "id_last_name")
        self.assertContains(response, "id_char_type")
        self.assertContains(response, """<option value="PC">PC</option>""", html=True)
        self.assertContains(response, """<option value="NPC">NPC</option>""", html=True)
        self.assertContains(response, """<input type="submit" value="Create Character">""", html=True)

        response = self.client.post(f"/writing/{self.game.name}/character/new/", {
            "first_male": "TestM",
            "first_female": "TestF",
            "last_name": "TestL",
            "char_type": "NPC"
            })
        self.assertTrue(models.NonPlayerCharacter.objects.filter(game=self.game, last_name="TestL").exists())
        first_name_obj = models.NonPlayerCharacter.objects.get(game=self.game, last_name="TestL").first_name_obj
        self.assertTrue(models.GenderizedName.objects.filter(id=first_name_obj.id).exists())

        char = models.NonPlayerCharacter.objects.get(game=self.game, last_name="TestL")
        response = self.client.get(f"/writing/{self.game.name}/character/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Character")
        self.assertContains(response, "cannot be undone!")
        self.assertContains(response, "id_character")

        response = self.client.post(f"/writing/{self.game.name}/character/delete/", {"character": char.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.NonPlayerCharacter.objects.filter(game=self.game, last_name="TestL").exists())
        # No more first name
        self.assertFalse(models.GenderizedName.objects.filter(id=first_name_obj.id).exists())

    def test_pc_create_delete(self):
        response = self.client.post(f"/writing/{self.game.name}/character/new/", {
            "first_male": "TestM",
            "first_female": "TestF",
            "last_name": "TestL",
            "char_type": "PC"
            })
        # Check that the character was created
        self.assertTrue(models.PlayerCharacter.objects.filter(game=self.game, last_name="TestL").exists())
        char = models.PlayerCharacter.objects.get(game=self.game, last_name="TestL")
        # Check that the first name obj was created
        first_name_obj = models.PlayerCharacter.objects.get(game=self.game, last_name="TestL").first_name_obj
        self.assertTrue(models.GenderizedName.objects.filter(id=first_name_obj.id).exists())
        # Check that the character has a sheet
        main_char_sheet = None
        for sheet in char.sheets.all():
            if sheet.name.render() == char.name():
                main_char_sheet = sheet
        self.assertIsNotNone(main_char_sheet)
        # Check it's a yellow story sheet
        self.assertEqual(main_char_sheet.color, models.SheetColor.objects.get(name="Yellowsheet"))
        self.assertEqual(main_char_sheet.sheet_type, models.SheetType.objects.get(name="Story"))
        # Check that the user got created
        self.assertTrue(models.User.objects.filter(username=char.username).exists())

        # Delete the character
        response = self.client.post(f"/writing/{self.game.name}/character/delete/", {"character": char.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.PlayerCharacter.objects.filter(game=self.game, last_name="TestL").exists())
        # No more first name
        self.assertFalse(models.GenderizedName.objects.filter(id=first_name_obj.id).exists())
        # Sheet still there - don't delete sheets when we delete characters
        self.assertTrue(models.Sheet.objects.filter(id=main_char_sheet.id).exists())
        # Check user is gone
        self.assertFalse(models.User.objects.filter(username=char.username).exists())

class PlayerCharacterEditingTest(GameDesignViewsTestCase):
    """
    Test everything game-writing-related under /writing/<game>/character/<character>
      * Sheets Tab
      * Metadata Right panel
      * All Sheets Tab
      * Contacts Tab
      * NOT Logistics Tab
    """
    def setUp(self) -> None:
        super().setUp()
        self.pc = models.PlayerCharacter.objects.first()
        assert self.pc.sheets.count() > 0, "The test character doesn't have any sheets"

    def test_character_main_sheets_view(self):
        response = self.client.get(f"/{self.game.name}/character/{self.pc.username}/")
        self.assertEqual(response.status_code, 200, msg=self.pc.username)
        for sheet in self.pc.sheets.all():
            self.assertContains(response, 
                                f"""<a href="{reverse("character_sheet", args=[self.game.name, self.pc.username, sheet.name.render_for_user(writer=False)])}"> {sheet.name.render_for_user(writer=False)} </a>""", html=True)

    def assert_sheet_in_selector_widget(self, response, sheet, selected, is_in=True, **kwargs):
        string = f"""<option value="{sheet.id}" {"selected" if selected else ""}>{sheet.filename}</option>"""
        if is_in:
            self.assertContains(response, string, html=True, **kwargs)
        else:
            self.assertNotContains(response, string, html=True, **kwargs)

    def template_test_edit_sheets_type(self, type_names: List[str], field_name: str):
            types = [models.SheetType.objects.get(name=type_name) for type_name in type_names]
            sheets = [self.game.sheets.filter(sheet_type=type).first() for type in types]

            # Check that the starting situation is ok for testing; they have sheets of each type and not the ones we're going to test adding:
            for type, type_name, a_sheet in zip(types, type_names, sheets):
                assert self.pc.sheets.filter(sheet_type=type).count() > 0, f"The test character {self.pc} doesn't have any {type_name} sheets. Add more in setup_test_db."
                assert self.pc.sheets.filter(sheet_type=type).exclude(id=a_sheet.id).count() > 0, f"The test character {self.pc} doesn't have any {type_name} sheets other than the one we're going to remove ({a_sheet.filename}). Add more in setup_test_db."

            # Check we can get the form
            response = self.client.get(f"/{self.game.name}/character/{self.pc.username}/", {"Edit": field_name})
            self.assertEqual(response.status_code, 200)

            # Check all options are there if the type matches, and not otherwise
            my_sheets = self.pc.sheets.all()
            for sheet in models.Sheet.objects.all():
                if sheet.sheet_type in types and sheet.game == self.game:
                    self.assert_sheet_in_selector_widget(response, sheet, selected=sheet in my_sheets, msg_prefix=response.content.decode())
                    self.assert_sheet_in_selector_widget(response, sheet, selected=sheet not in my_sheets, is_in=False, msg_prefix=response.content.decode())
                else:
                    self.assert_sheet_in_selector_widget(response, sheet, selected=True, is_in=False, msg_prefix=response.content.decode())
                    self.assert_sheet_in_selector_widget(response, sheet, selected=False, is_in=False, msg_prefix=response.content.decode())
            
            # Make a change
            response = self.client.post(f"/{self.game.name}/character/{self.pc.username}/", 
                                        {"Save": field_name, 
                                        "sheets": [a_sheet.id]})
            self.assertEqual(response.status_code, 302)
            self.assertListEqual([sheet.name.render() for sheet in self.pc.sheets.filter(sheet_type=type)], [a_sheet.name.render()])

    def test_edit_character_sheets_public(self):
        self.template_test_edit_sheets_type(["Public Sheet"], "public_sheets")

    def test_edit_character_sheets_igd(self):
        self.template_test_edit_sheets_type(["In-Game Document"], "in-game_documents")

    def test_edit_character_sheets_story(self):
        self.template_test_edit_sheets_type(["Story", "Supplement", "Details"], "private_sheets")

    def test_character_main_sheets_charstats_view(self):
        # Check a required stat and an optional stat with a value shows up
        optional_stat = models.CharacterStatType.objects.filter(game=self.game, optional=True).first()
        assert optional_stat is not None, "Need an optional stat to test this. Add one in setup_test_db."
        pc_optional_stat = self.pc.stats.get(stat_type=optional_stat)
        
        required_stat = models.CharacterStatType.objects.filter(game=self.game, optional=False).first()
        assert required_stat is not None, "Need a required stat to test this. Add one in setup_test_db."
        pc_required_stat = self.pc.stats.get(stat_type=required_stat)

        pc_optional_stat.value = "TEST STAT 1 VALUE"
        pc_optional_stat.save()
        pc_required_stat.value = "TEST STAT 2 VALUE"
        pc_required_stat.save()

        response = self.client.get(f"/{self.game.name}/character/{self.pc.username}/")
        self.assertEqual(response.status_code, 200)
        # count=2 becuase it appears once in the edit bar and once on the main sheet.
        self.assertContains(response, required_stat.name, count=2)
        self.assertContains(response, "TEST STAT 1 VALUE", count=2, msg_prefix=response.content.decode())
        self.assertContains(response, optional_stat.name, count=2)
        self.assertContains(response, "TEST STAT 2 VALUE", count=2)

        # Check that an optional stat with no value doesn't show up, but a required one does.
        pc_optional_stat.value = ""
        pc_optional_stat.save()
        pc_required_stat.value = ""
        pc_required_stat.save()
        response = self.client.get(f"/{self.game.name}/character/{self.pc.username}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, required_stat.name, count=2)
        self.assertNotContains(response, "TEST STAT 1 VALUE", msg_prefix=response.content.decode())
        self.assertContains(response, optional_stat.name, count=1, msg_prefix=response.content.decode())
        self.assertNotContains(response, "TEST STAT 2 VALUE", msg_prefix=response.content.decode())

    def test_character_edit_metadata_simple(self):
        # TODO add testing new genderized names
        response = self.client.get(f"/{self.game.name}/character/{self.pc.username}/", {"Edit": "Metadata"})
        self.assertEqual(response.status_code, 200)
        # Check all the fields are there
        self.assertContains(response, "id_title_obj")
        # These few are clearly testing too much, it shouldn't fail if we change some random html attr. Not sure how to do that.
        self.assertContains(response, f"""<input type="text" name="main_form-first_male" value="{self.pc.first_name_obj.male}" placeholder="Male First Name" size="10" style="background-color: #BCF" required id="id_main_form-first_male">""", html=True)
        self.assertContains(response, f"""<input type="text" name="main_form-first_female" value="{self.pc.first_name_obj.female}" placeholder="Female First Name" size="10" style="background-color:#FFA" required id="id_main_form-first_female">""", html=True)  
        self.assertContains(response, f"""<input type="text" name="main_form-last_name" value="{self.pc.last_name}" placeholder="Last Name" size="28" maxlength="50" id="id_main_form-last_name">""", html=True)
        
        self.assertContains(response, "plus.jpeg")  # Add title button.
        # Make sure the weird NPC gender options aren't available; EQ and OP
        self.assertContains(response, 
                            f"""<select name="main_form-gender_field" id="id_main_form-gender_field">
                                <option value="M" {"selected" if self.pc.gender()=="M" else ""}>Male</option>
                                <option value="F" {"selected" if self.pc.gender()=="F" else ""}>Female</option>
                                </select>""", html=True)
        self.assertContains(response, f"""<input type="text" name="main_form-username" value="{self.pc.username}" placeholder="username" size="10" maxlength="50" id="id_main_form-username">""", html=True)
        self.assertContains(response, f"""<input type="text" name="main_form-password" value="{self.pc.password}" placeholder="password" size="10" maxlength="50" id="id_main_form-password">""", html=True)

        # Check the form submission works
        num_stat_fields = models.CharacterStatType.objects.filter(game=self.game).count()
        assert num_stat_fields == 2, "This test is brittle and assumes the setup_test_db adds 2 stat types. Sorry"   
        num_other_names = self.pc.genderized_names.count() - 1  # first name is handled specially
        assert num_other_names == 0, "This test is brittle and assumes the setup_test_db adds no other names. Sorry"
        title_id = models.GenderizedKeyword.objects.filter(male="king").first().id
        response = self.client.post(f"/{self.game.name}/character/{self.pc.username}/", 
                                    {"Save": "Metadata",
                                     "main_form-title_obj": title_id,
                                     "main_form-first_male": "FIRST MALE",
                                     "main_form-first_female": "FIRST_FEMALE",
                                     "main_form-last_name": "LAST NAME",
                                     "main_form-gender_field": "F",
                                     "main_form-username": "USERNAME",
                                     "main_form-password": "PASSWORD",
                                     "stats-TOTAL_FORMS": num_stat_fields,
                                     "stats-INITIAL_FORMS": num_stat_fields,
                                     "stats-0-value": 'STAT 0 VALUE',
                                     "stats-0-id": self.pc.stats.get(stat_type=self.game.character_stat_types.first()).id,
                                     "stats-1-value": 'STAT 1 VALUE',
                                     "stats-1-id": self.pc.stats.get(stat_type=self.game.character_stat_types.last()).id,
                                     "other_names-TOTAL_FORMS": num_other_names,
                                     "other_names-INITIAL_FORMS": num_other_names,
                                     })
        self.assertEqual(response.status_code, 302)
        # Check data is updated
        self.pc.refresh_from_db()
        self.assertEqual(self.pc.first_name_obj.male, "FIRST MALE")
        self.assertEqual(self.pc.first_name_obj.female, "FIRST_FEMALE")
        self.assertEqual(self.pc.last_name, "LAST NAME")
        self.assertEqual(self.pc.gender(), "F")
        self.assertEqual(self.pc.username, "USERNAME")
        self.assertEqual(self.pc.password, "PASSWORD")
        self.assertEqual(self.pc.title(), "queen")
        self.assertEqual(self.pc.stats.get(stat_type=self.game.character_stat_types.first()).value, "STAT 0 VALUE")
        self.assertEqual(self.pc.stats.get(stat_type=self.game.character_stat_types.last()).value, "STAT 1 VALUE")
                                                                                       
    def test_character_contacts_view(self):
        # create some contacts for our pc
        characters = list(self.game.characters.all())
        models.Contact.objects.create(owner=self.pc, target=characters[0], display_name=LARPstring("Self"), order_number=0)
        models.Contact.objects.create(owner=self.pc, target=characters[2], display_name=LARPstring(characters[1].full_name(), check_keywords_from_game=self.game), order_number=1, description=LARPstring(f"A friend named {characters[1].first_name()}", check_keywords_from_game=self.game))

        response = self.client.get(reverse("character_contacts", args=[self.game.name, self.pc.username]))
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, "Self")
        self.assertContains(response, characters[1].full_name())
        self.assertContains(response, f"A friend named {characters[1].first_name()}")
        self.assertNotContains(response, characters[2].first_name())
        
        # Delete buttons
        for contact in self.pc.contacts.all():
            self.assertContains(response, f"""<input type="hidden" name="contact_id" value="{contact.id}"><input type="submit" value="Delete">""", html=True)

        # Check genderizing works
        assert characters[1].gender() == "M", "Test assumes character starts male. Alterations to setup_test_db may have broken this."
        original_name = characters[1].first_name()
        pc = characters[1].cast()
        pc.default_gender = "F"
        pc.save()
        assert characters[1].first_name() != original_name, characters[1].gender()
        response = self.client.get(reverse("character_contacts", args=[self.game.name, self.pc.username]))
        self.assertNotContains(response, original_name, msg_prefix=response.content.decode())
        self.assertContains(response, characters[1].first_name(), count=2)  # once in display_name and once in decription.

    def test_character_contacts_add(self):
        response = self.client.get(reverse("character_contacts", args=[self.game.name, self.pc.username]), {"Edit": "add"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_target")
        for character in self.game.characters.all():
            self.assertContains(response, f"""<option value="{character.id}">{character.full_name()}</option>""", html=True)
        self.assertContains(response, "id_display_name")
        self.assertContains(response, "id_description")

        # Check the form submission works
        target = self.game.characters.last()
        response = self.client.post(reverse("character_contacts", args=[self.game.name, self.pc.username]), {
            "Save": "add",
            "owner": self.pc.id,  # hidden field
            "target": target.id,
            "display_name": "DISPLAY NAME",
            "description": f"DESCRIPTION {target.first_name()}",
        })
        self.assertEqual(response.status_code, 302)
        new_contact = models.Contact.objects.get(owner=self.pc, target=target)
        self.assertEqual(new_contact.display_name.render(), "DISPLAY NAME")
        self.assertEqual(new_contact.description.render(), f"DESCRIPTION {target.first_name()}")

    def test_character_contacts_edit(self):
        contact = models.Contact.objects.create(owner=self.pc, target=self.game.characters.last(), display_name=LARPstring("Self"), order_number=0)
        response = self.client.get(reverse("character_contacts", args=[self.game.name, self.pc.username]), {"Edit": contact.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_display_name")
        self.assertContains(response, "id_description")

        # Check the form submission works
        response = self.client.post(reverse("character_contacts", args=[self.game.name, self.pc.username]), {
            "Save": contact.id,
            "display_name": "DISPLAY NAME",
            "description": f"DESCRIPTION {contact.target.first_name()}",
        })
        self.assertEqual(response.status_code, 302)
        contact.refresh_from_db()
        self.assertEqual(contact.display_name.render(), "DISPLAY NAME")
        self.assertEqual(contact.description.render(), f"DESCRIPTION {contact.target.first_name()}")

    def test_character_contacts_delete(self):
        contact = models.Contact.objects.create(owner=self.pc, target=self.game.characters.last(), display_name=LARPstring("Self"), order_number=0)
        self.assertTrue(models.Contact.objects.filter(id=contact.id).exists())
        response = self.client.post(reverse("character_contacts_delete", args=[self.game.name, self.pc.username]), {"contact_id": contact.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.Contact.objects.filter(id=contact.id).exists())
