"""
Views for players and logistical things

This will get revamped at some point.
"""

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
import auth
from django.shortcuts import render
from django.core.mail import send_mail
from garhdony_app.forms_players import LogisticalTaskFormClass
from garhdony_app.models import LogisticalTask, PlayerProfile

def character_welcome(request, run_name, username):
    """
    The first thing a player sees upon logging in for the first time.
    Asks them to confirm that they are playing.
    """

    def render_character_welcome(game, writer, character):
        p = character.PlayerProfile
        if request.method == 'POST':
            which_button = request.POST.get("which_button")
            if which_button == "confirm":
                p.confirm_playing()
                return HttpResponseRedirect(reverse('user_redirect'))
            if which_button == "abdicate":
                return HttpResponseRedirect(reverse('character_abdicate', args=[game.name, character.username]))
        if p.confirmed():
            return HttpResponseRedirect(reverse('user_redirect'))
        else:
            return auth.callback_package('garhdony_app/character_welcome.html', {})

    return auth.authenticate_resolve_and_callback(request, render_character_welcome, run_name, username)


def character_abdicate(request, run_name, username):
    """
    If a player clicks the abdicate button, it brings them here.
    This asks them to confirm.
    """

    def render_character_abdicate(game, writer, character):
        p = character.PlayerProfile
        if request.method == 'POST':  # If the form has been submitted...
            message = "Player " + p.name + " has chosen not to play. We'd better get in touch with them and find someone on the waitlist."
            send_mail(subject="A player has abdicated!", message=message, from_email="dogmas-gms@mit.edu",
                      recipient_list=["dogmas-gms@mit.edu"])
            return HttpResponseRedirect(reverse('actually_abdicated'))
        return auth.callback_package('garhdony_app/character_abdicate.html', {})

    return auth.authenticate_resolve_and_callback(request, render_character_abdicate, run_name, username)


def actually_abdicated(request):
    """
    Upon actually abdicating their spot, a player is redirected here.
    """
    return render(request, 'garhdony_app/actually_abdicated.html')


def character_logistics(request, run_name, username):
    """
    This Logistics stuff will get improved and updated later.
    """
    def render_logistics(game, writer, character):
        return auth.callback_package('garhdony_app/logistics.html', {'here':'Logistics', 'all_tasks':LogisticalTask.objects.all().order_by('sort_order')})
    return auth.authenticate_resolve_and_callback(request, render_logistics, run_name, username)


def character_logistics_task(request, run_name, username, task_name):
    def render_logistical_task(game, writer, character):
        t = LogisticalTask.objects.get(name=task_name)
        form_class = LogisticalTaskFormClass(t)
        if form_class is None:
            return auth.callback_package('garhdony_app/logistical_task.html', {'task':t, 'form':None})
        if request.method == 'POST': # If the form has been submitted...
            form = form_class(request.POST, request.FILES, instance=character.PlayerProfile) # A form bound to the POST data
            if form.is_valid(): # All validation rules pass
                form.save()
                character.PlayerProfile.done_tasks.add(t)
                character.PlayerProfile.save()
                return HttpResponseRedirect(reverse('character_logistics', args=[game.name, character.username])) # Redirect after POST
        else:
            form = form_class(instance=character.PlayerProfile)
        return auth.callback_package('garhdony_app/logistical_task.html', {'task':t, 'form':form})
    return auth.authenticate_resolve_and_callback(request, render_logistical_task, run_name, username)


def logistics_table(request, run_name):
        def render_logistics_table(game, writer):
                tasks = LogisticalTask.objects.all().order_by('sort_order')
                players = PlayerProfile.objects.filter(character__game=game)
                return auth.callback_package('admin/logistics_table.html', {'tasks':tasks, 'players':players})
        return auth.authenticate_resolve_and_callback(request, render_logistics_table, run_name, requires_writer = True)

