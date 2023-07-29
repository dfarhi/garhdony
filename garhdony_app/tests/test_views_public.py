from django.test import TestCase
from garhdony_app import models
from garhdony_app.tests.setup_test_db import setup_test_db

class PublicPagesTest(TestCase):
    def setUp(self):
        models.setup_database()
        
    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garhdony_app/index.html")

    def test_about_page(self):
        response = self.client.get("/about/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garhdony_app/about.html")

class PublicGamePagesTest(TestCase):
    def setUp(self):
        setup_test_db(game=True, sheets=False, characters=False)

    def test_game_home(self):
        game = models.GameTemplate.objects.get(name="TestGameTemplate")
        BLURB = "test blurb"
        game.blurb = BLURB
        game.save()

        response = self.client.get("/TestGameTemplate/home/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garhdony_app/game_blurb.html")
        self.assertContains(response, BLURB)
        self.assertContains(response, game.name)

    def test_game_about(self):
        game = models.GameTemplate.objects.get(name="TestGameTemplate")
        ABOUT = "test about"
        game.about = ABOUT
        game.save()

        response = self.client.get("/TestGameTemplate/about/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garhdony_app/game_about.html")
        self.assertContains(response, ABOUT)
        