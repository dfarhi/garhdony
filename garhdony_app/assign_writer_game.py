from guardian.shortcuts import assign_perm


def assign_writer_game(writer, game):
    """
    Assigns a writer permissions on a game.
    """
    return assign_perm('writer', writer, game)