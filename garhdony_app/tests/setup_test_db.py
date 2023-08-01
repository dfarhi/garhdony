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
    game.save()

    # create a few CharacterStatTypes
    models.CharacterStatType(name="Stat1-optional", game=game, optional=True).save()
    models.CharacterStatType(name="Stat2-required", game=game, optional=False).save()

    if not sheets:
        return
    
    models.SheetStatus(name="Status 1", game=game, sort_order=1).save()
    models.SheetStatus(name="Status 2", game=game, sort_order=2).save()
    # Create a few sheets.
    for color in ["Bluesheet", "Yellowsheet", "Greensheet"]:
        for type in ["Story", "Details", "Supplement"]:
            for i in range(1, 3):
                models.Sheet(
                    game=game, 
                    name=f"{color} {type} {i}", 
                    sheet_type=models.SheetType.objects.get(name=type), 
                    color=models.SheetColor.objects.get(name=color), 
                    filename=f"test_sheet_{color}_{type}_{i}", 
                    content_type="html",
                    preview_description=f"Test sheet {color} {type} {i} preview description",
                    sheet_status=models.SheetStatus.objects.get(name="Status 1"),
                    ).save()
    
    for type in ["Public Sheet", "In-Game Document"]:
        for i in range(1, 3):
            models.Sheet(
                game=game, 
                name=f"{type} {i}", 
                sheet_type=models.SheetType.objects.get(name=type), 
                color=models.SheetColor.objects.get(name="Bluesheet"), 
                filename=f"test_sheet_{type}_{i}", 
                content_type="html",
                preview_description=f"Test sheet {type} {i} preview description",
                sheet_status=models.SheetStatus.objects.get(name="Status 1"),
                ).save()
    
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
        'first_female': 'PC1-Female',
        'last_name':  'PC1-Last',
        'char_type': 'PC'})
    f.is_valid()
    f.save(game)
    f = CharacterNewForm({
        'first_male': 'PC2-Male',
        'first_female': 'PC2-Female',
        'last_name':  'PC2-Last',
        'char_type': 'PC'})
    f.is_valid()
    f.save(game)

    # give characters some sheets
    char1 = models.PlayerCharacter.objects.get(last_name="PC1-Last")
    char1.sheets.add(models.Sheet.objects.get(name="Public Sheet 1"))
    char1.sheets.add(models.Sheet.objects.get(name="Public Sheet 2"))
    char1.sheets.add(models.Sheet.objects.get(name="Greensheet Story 1"))
    char1.sheets.add(models.Sheet.objects.get(name="Bluesheet Details 1"))
    char1.sheets.add(models.Sheet.objects.get(name="Bluesheet Details 2"))
    char1.sheets.add(models.Sheet.objects.get(name="Yellowsheet Supplement 1"))
    char1.sheets.add(models.Sheet.objects.get(name="In-Game Document 2"))
    char1.save()

    char2 = models.PlayerCharacter.objects.get(last_name="PC2-Last")
    char2.sheets.add(models.Sheet.objects.get(name="Public Sheet 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Public Sheet 2"))
    char2.sheets.add(models.Sheet.objects.get(name="Bluesheet Story 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Bluesheet Details 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Bluesheet Details 2"))
    char2.sheets.add(models.Sheet.objects.get(name="Bluesheet Supplement 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Yellowsheet Supplement 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Yellowsheet Supplement 2"))
    char2.sheets.add(models.Sheet.objects.get(name="Greensheet Supplement 1"))
    char2.sheets.add(models.Sheet.objects.get(name="Greensheet Details 2"))
    char2.sheets.add(models.Sheet.objects.get(name="In-Game Document 1"))
    char2.sheets.add(models.Sheet.objects.get(name="In-Game Document 2"))
    char2.save()
