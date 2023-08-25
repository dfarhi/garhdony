"""

python merge_two_npc.py game "<npc name to keep>" "<npc name to deprecate>"

"""
import argparse
import re
import django
import os
import sys

# setup stuff so django is happy
sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 2)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from garhdony_app.models import GameInstance, SheetRevision
from garhdony_app.LARPStrings import LARPstring

def get_npc_by_name(game, name):
    """Get an NPC by name"""
    # Since name is a method not a field, we can't use the normal filter
    # So we have to do it manually
    for npc in game.npcs():
        if npc.name() == name:
            return npc
    return None

def update_sheet(sheet, npc_source, npc_dest):
    last_revision: SheetRevision = sheet.last_revision()
    raw_content = last_revision.content.raw()
    changed = False

    substitutions = [
        (re.compile(f'''data-character=["']{npc_source.id}["']'''), f'data-character="{npc_dest.id}"'),
        (re.compile(f'''data-keyword=["']{npc_source.first_name_obj.id}["']'''), f'data-keyword="{npc_dest.first_name_obj.id}"'),
    ]

    for regex, replacement in substitutions:
        if re.search(regex, raw_content) is not None:
            raw_content = re.sub(regex, replacement, raw_content)
            changed = True
    if changed:
        print("Updating sheet {}".format(sheet.filename))
        new_revision = SheetRevision.objects.create(sheet=sheet, content=LARPstring(raw_content), author=None)
        new_revision.embeddedImages.set(last_revision.embeddedImages.all())
        new_revision.save()
    else:
        print("Sheet {} does not reference {}".format(sheet.filename, npc_source.name()))

def main():
    parser = argparse.ArgumentParser(description='Merge two NPCs')
    parser.add_argument('game', help='Game to merge into')
    parser.add_argument('npc1', help='NPC to merge (name to keep)')
    parser.add_argument('npc2', help='NPC to merge (name to deprecate)')
    args = parser.parse_args()

    game = args.game
    npc1 = args.npc1
    npc2 = args.npc2

    try:
        game = GameInstance.objects.get(name=game)
    except GameInstance.DoesNotExist:
        print("Game {} does not exist".format(game))
        return
    
    npc_dest = get_npc_by_name(game, npc1)
    if npc_dest is None:
        print("NPC {} does not exist".format(npc1))
        return
    
    npc_source = get_npc_by_name(game, npc2)
    if npc_source is None:
        print("NPC {} does not exist".format(npc2))
        return

    # Find all references to npc2 and replace them with npc1
    for sheet in game.sheets.filter(content_type='html'):
        update_sheet(sheet, npc_source, npc_dest)

    # TODO - probably need to deal with contacts and other larpstring fields. But for now let's leave it at that.    

    # # Delete npc_source
    print("Deleting {}".format(npc_source.name()))
    npc_source.delete()

if __name__ == "__main__":
    main()
