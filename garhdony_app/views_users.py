from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import logout
from garhdony_app.forms_users import NewWriterForm
from django.views.generic.edit import CreateView
from django.contrib.auth import login
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

def user_redirect(request):
    """
    redirects to the user's homepage.
    """
    logger.debug("User redirect: " + request.user.username)
    if request.user.username == "admin":
        # Send the admin user to the admin interface
        redir = reverse('admin:index')
    elif request.user.has_perm("garhdony_app.writer"):
        # Send writers to writer_home
        redir = reverse('writer_home')
    elif not request.user.character.player_cast:
        # Send uncast users to ... ummm ... character_home?
        redir = reverse('character_home', args=(request.user.character.game.name, request.user.character.username))
    elif request.user.character.PlayerProfile.confirmed():
        # Send confirmed players to character_home
        redir = reverse('character_home', args=(request.user.character.game.name, request.user.character.username))
    else:
        # Send unconfirmed players to the confirmation page so they can confirm.
        redir = reverse('character_welcome', args=(request.user.character.game.name, request.user.character.username))
    return HttpResponseRedirect(redir)


def logout_then_login(request, next):
    """
    Does what it sounds like.
    For people who are logged in as storyteller and listen to the
    scolding note telling them to log in as a personal user.
    """
    logout(request)
    return HttpResponseRedirect(next)

class NewWriterView(CreateView):
    """
    The form for making a new writer user.
    People will get here after logging in as storyteller and being asked to make personal users.
    This uses some django magic to automatically create a new User.

    The fact that it's a User being created is described in NewWriterForm
    """

    form_class = NewWriterForm
    template_name = 'garhdony_app/new_writer.html'
    success_url = "/writing"

    def form_valid(self, form):
        # This is what it does if the form is valid
        # We want to override it to include logging in as the new guy.

        # form.instance is the new user. You can't log in a user using django's login function
        # unless a backend object has authenticated it. Since we don't know the user's password,
        # We just make believe that the first backend has authenticated it.
        # Maybe this is insecure for some reason?
        form.instance.backend = settings.AUTHENTICATION_BACKENDS[0]

        result = super(NewWriterView, self).form_valid(form)
        login(self.request, form.instance)
        return result