
import tempfile
from django.conf import settings
from django.test import TestCase
from garhdony_app import models
from garhdony_app.tests.setup_test_db import setup_test_db

class AdminNotLoggedInTest(TestCase):
   
    def test_admin_site_not_logged_in(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/admin/login/?next=/admin/')

class AdminTest(TestCase):
    MODELS_TO_TEST = [
            models.Character,
            models.CharacterStat,
            models.CharacterStatType,
            models.Contact,
            # models.EmbeddedImage,  # We dont' yet have tests for sheet editing stuff
            models.GameTemplate,
            models.GameInstance,
            models.GameInfoLink,
            models.GenderizedKeyword,
            models.GenderizedName,
            # models.LogisticalTask,  # Don't yet have tests for player logistics
            models.NonPlayerCharacter,
            models.PlayerCharacter,
            # models.PlayerProfile,  # Don't yet have tests for player logistics
            # models.QuizSubmission,  # This was a one-time silly thing
            models.Sheet,
            models.SheetColor,
            models.SheetRevision,
            models.SheetStatus,
            models.SheetType,
            # models.TimelineEvent,  # NotImplemented
            # models.TimelineEventSheetDescription,  # NotImplemented
            # models.TravelProfile,  # Don't yet have tests for player logistics
            models.WebsiteAboutPage
        ]
    def setUp(self) -> None:
        settings.MEDIA_ROOT = tempfile.mkdtemp()
        setup_test_db()
        # Add a superuser
        self.user = models.User.objects.create_user(username='testuser', password='12345')
        self.user.is_superuser = True
        self.user.is_staff = True
        models.Group.objects.get(name='Writers').user_set.add(self.user)
        self.user.save()
        self.client.login(username='testuser', password='12345')
        return super().setUp()

    def test_admin_home_loads(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site administration", msg_prefix=response.content.decode())

    def test_all_models_load(self):
        for model in self.MODELS_TO_TEST:
            model_name = model.__name__
            response = self.client.get(f'/admin/garhdony_app/{model_name.lower()}/')
            self.assertEqual(response.status_code, 200, msg=f"Failed to load {model_name}")
            self.assertContains(response, f"Select", msg_prefix=response.content.decode())

    def test_all_models_load_edit_page(self):
        for model in self.MODELS_TO_TEST:
            instance = model.objects.first()
            assert instance is not None, f"No instance of {model.__name__} found; add one in setup_test_db.py"
            model_name = model.__name__
            response = self.client.get(f'/admin/garhdony_app/{model_name.lower()}/{instance.id}/change/')
            self.assertEqual(response.status_code, 200, msg=f"Failed to load {model_name} edit page")

            

