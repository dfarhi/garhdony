from guardian.shortcuts import assign_perm

from django.contrib.auth.models import User

def assign_writer_game(writer: User, game):
    """
    Assigns a writer permissions on a game.
    """
    return assign_perm('writer', writer, game)