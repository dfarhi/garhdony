import os
import shutil
from garhdony_app.forms_game_design import CharacterNewForm
import garhdony_app.models as models

def setup_test_db(game=True, sheets=True, characters=True):
    # Check we're in the test db
    assert models.GameInstance.objects.count() == 0
    
    # Global setup
    models.setup_database()

    if not game:
        return
    # Create a test game, clearing old test data
    template = models.GameTemplate(name="TestGameTemplate", blurb="TestGameTemplate blurb", about="TestGameTemplate about", how_to_app="TestGameTemplate how_to_apply", app="TestGameTemplate app", interest="TestGameTemplate interest", short_desc="TestGameTemplate short_desc", is_accepting_apps=False)
    template.save()

    game = models.GameInstance(name="TestGame")
    if os.path.exists(game.abs_media_directory):
        shutil.rmtree(game.abs_media_directory)
    game.save()

    if not sheets:
        return
    # Create a few sheets.
    for color in ["Bluesheet", "Yellowsheet", "Greensheet"]:
        for type in ["Story", "Details", "Supplement"]:
            for i in range(1, 3):
                models.Sheet(game=game, name=f"{color} {type} {i}", sheet_type=models.SheetType.objects.get(name=type), color=models.SheetColor.objects.get(name=color), filename=f"test_sheet_{color}_{type}_{i}.txt", content_type="html").save()

    if not characters:
        return
    # Create a few characters
    f = CharacterNewForm({
        'first_male': 'NPC1-Male',
        'first_female': 'NPC1-Feale',
        'last_name':  'NPC1-Last',
        'char_type': 'NPC'})
    f.is_valid()
    f.save(game)
    f = CharacterNewForm({
        'first_male': 'PC1-Male',
        'first_female': 'PC1-Feale',
        'last_name':  'PC1-Last',
        'char_type': 'PC'})
    f.is_valid()
    f.save(game)
    f = CharacterNewForm({
        'first_male': 'PC2-Male',
        'first_female': 'PC2-Feale',
        'last_name':  'PC2-Last',
        'char_type': 'PC'})
    f.is_valid()
    f.save(game)