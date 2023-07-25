"""
Stuff related to logging in and authenticating.

The main goal is the authenticate_resolve_and_callback function.
"""

from .models import GameInstance, PlayerCharacter
from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from datetime import datetime
import logging
logger = logging.getLogger(__name__) # TODO: Organize logging.


class callback_package():
    """
    This is the class of thing that callbacks being called by authenticate_resolve_and_callback should return.
    It's just like the normal django render function: callback_package(template, args)
    """
    def __init__(self, template, args={}):
        self.template = template
        self.args = args

    def add(self, dic):
        self.args.update(dic)
        return self


def authenticate_and_callback(request, callback, requires_writer=False):
    """
    Make sure that the user is logged in, and optionally that they're a writer.
    Then call callback(), which should return a callback_package
    (or a regular HttpResponse, if you want, but that's less good).
    """

    approved = request.user.is_authenticated

    if requires_writer and not request.user.has_perm('garhdony_app.writer'):
        approved = False

    if not approved:
        if request.method == 'GET':
            return HttpResponseRedirect(reverse('login_view') + "?next=" + request.path)
        else:
            # Presumably this is where we fix the logged-out post problem.
            return HttpResponseRedirect(reverse('login_view') + "?next=" + request.path)

    callback_result = callback()

    if isinstance(callback_result, callback_package):
        args = callback_result.args
        template = callback_result.template
        logger.debug(str(datetime.now())+": Rendering template: " + template + "   (" + str(args)+")")
        response = render(request, template, args)
        if 'writer' in args and args['writer']:
            # This turns off some security settings
            # Which would otherwise prevent you from
            # entering html into textboxes.
            response['X-XSS-Protection'] = 0
        logger.debug(str(datetime.now())+": authenticate_resolve_and_callback: returning from callback_package (" + template + ").\n\n\n\n")
        return response
    else:
        # You can return a direct render if you want.
        logger.debug(str(datetime.now())+": authenticate_resolve_and_callback: returning HTTPresponse.\n\n\n\n")
        return callback_result


def authenticate_resolve_and_callback(request, callback, run_name, username=None, requires_writer=False,
                                      sheet=None, sheet_by_display_name=False):
    """
    Does four things:
        1. Authenticate: Check that user is logged in and matches run_name and and username, if provided,
                            and that they are a writer if requires_writer is True,
                            and that they have permission to view sheet if provided.
        2. Resolve: Really part of #1, but also resolves the strings run_name, username, and sheet into
                            GameInstance, Character, and Sheet objects, respectively
        3. Callback: calls callback(game, writer, character, sheet) (all four arguments are there are or not as
                            depending on whether they were provided to authenticate_resolve_and_callback).
                            Make sure to use those same argument names, since they are provided as kwargs.

        4. Render: Callback should return a callback_package, which is then rendered.
                            The extra arguments {game, writer, character, and sheet} are provided to the template.
    """

    def resolve_and_callback():
        # TODO: This needs better error handling for optimal security; I think someone could see what games exist, at least, by the errors?
        approved = False


        if request.user.is_staff:
            # Always allow storyteller and admin to do anything.
            approved = True

        resolved_items = {}
        resolved_items['game'] = GameInstance.objects.get(name=run_name)

        resolved_items['writer'] = request.user.has_perm('garhdony_app.writer', resolved_items['game'])\
                                   or request.user.is_staff
        if resolved_items['writer']:
            # Allow writers to do anything.
            approved = True

        if requires_writer and not approved:
            # Not a writer; raise error. This is stricter than what authenticate_and_callback already did,
            # Since this checks that you're explicitly a writer for this game.
            raise Http404

        if username:
            resolved_items['character'] = PlayerCharacter.objects.get(game=resolved_items['game'],
                                                                             username=username)

        if not approved:
            # Not a writer; might be a player. Check credentials
            user_char = request.user.character
            if user_char.game == resolved_items['game']:
                if username is None or user_char.username == username or resolved_items['game'].complete:
                    # You can go to a page if:
                    #   * Game is complete. TODO: Make a link for that someplace.
                    #   * You are the right user.
                    #   * The authenticate call didn't specify a particular user.
                    approved = True

        if not approved:
            # Do this again
            # (had to do it twice since we ned to short circuit if requires_writer was true
            # to prevent people from detecting what usernames are valid by the errors).
            raise Http404

        if sheet:
            # First get a list of all sheets this person can see
            if 'character' in resolved_items:
                visible_sheets = resolved_items['character'].sheets.all()
            else:
                visible_sheets = resolved_items['game'].sheets.all()

            # then find the one we want.
            if sheet_by_display_name:
                resolved_items['sheet'] = visible_sheets.get(name=sheet)
            else:
                resolved_items['sheet'] = visible_sheets.get(filename=sheet)


        logger.debug(str(datetime.now())+": authentication complete; calling back.")
        # Call callback with our assembled arguments.
        callback_result = callback(**resolved_items)

        # Update the callback_package with our resolved items
        # This lets you use {{character}} and stuff in templates.
        if isinstance(callback_result, callback_package):
            args = callback_result.args
            resolved_items.update(args)
            callback_result.args = resolved_items
        return callback_result
    logger.debug("\n\n\n\n" + str(datetime.now()) +
                 ": authenticate_resolve_and_callback beginning for path: %s"%request.path)
    return authenticate_and_callback(request, resolve_and_callback, requires_writer)
