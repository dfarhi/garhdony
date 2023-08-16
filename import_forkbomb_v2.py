import argparse
from collections import defaultdict
import csv
import datetime
import sys
import django
from functools import lru_cache
import os
import re
from typing import Callable, Dict, List, Tuple

# setup stuff so django is happy
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from garhdony_app.LARPStrings import LARPstring
from garhdony_app.models import GenderizedKeyword, GenderizedName, Character, Sheet, GameInstance, SheetRevision, NonPlayerCharacter
from garhdony_app.span_parser import WritersBubbleInnerNode, WritersNode, newGenderSwitchNode, newGenderSwitchNodeGeneric


import logging
# Logging config that prints to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger("garhdony_app.LARPStrings").setLevel(logging.INFO)
# django.db.backends
logging.getLogger('django.db.backends').setLevel(logging.ERROR)


GAME_NAME = "DogmasCloneTest8"
game = GameInstance.objects.get(name=GAME_NAME)


forkbomb_v2_csv_path = "data/forkbomb_v2.csv"
"""
The v2 csv has three columns:
- sheet name with underscores instead of spaces
- last modified date (we don't need this)
- string content
Main issue is that some contents are enormous (100k+ characters), so we have to handle that.
"""
csv.field_size_limit(10000000)

def standardize_name(name):
    return name.lower().replace(' ', '_').replace('(', '').replace(')', '')

def load_forkbomb_v2_csv():
    with open(forkbomb_v2_csv_path, encoding='utf-8') as f:
        reader = csv.reader(f)
        forkbomb_v2_csv = {standardize_name(row[0]): row[2] for row in reader}

    return forkbomb_v2_csv
forkbomb_v2_csv = load_forkbomb_v2_csv()
def get_forkbomb_v2_csv(sheet_name):
    """
    Ignore case
    """
    return forkbomb_v2_csv[sheet_name.lower()]

def mediawiki_to_html(string: str) -> str:
    """
    Replace things like "==foo==" -> "<h2>foo</h2>"
    Leaves raw html untouch ("<span> blah </span>" -> "<span> blah </span>")

    Uses the imported library for this.
    """
    # Then, do the actual markdown parsing
    import pypandoc
    # convert from mediawiki to html, leaving templates (e.g. {{foo}}) alone.
    # Hack this together by escaping the braces marking templates, then unescaping them after
    num_braces = string.count("{"), string.count("}"), string.count("|")
    string = string.replace("{{", "DOUBLEOPENBRACE")
    string = string.replace("}}", "DOUBLECLOSEBRACE")
    string = string.replace("|", "PIPE")
    # Add args to avoid extra linebreaks due to wrapping and headings.
    string = pypandoc.convert_text(string, "html", format="mediawiki", extra_args=["--wrap=none", "--no-highlight"])
    string = string.replace("DOUBLEOPENBRACE", "{{")
    string = string.replace("DOUBLECLOSEBRACE", "}}")
    string = string.replace("PIPE", "|")
    # Check the number of braces is right
    assert string.count("{") == num_braces[0], f"Number of braces changed in {string}"
    assert string.count("}") == num_braces[1], f"Number of braces changed in {string}"
    assert string.count("|") == num_braces[2], f"Number of braces changed in {string}"
    return string.strip()
test_result = mediawiki_to_html("""
List:
* item1
* item2
""")
assert "<ul>" in test_result, test_result
test_result = mediawiki_to_html("foo <span>bar</span> baz")
assert "<span>bar</span>" in test_result, test_result
test_result = mediawiki_to_html("==bar==")
assert "<h2" in test_result and "bar</h2>", test_result  # It can put some attributes if it wants to
test_result = mediawiki_to_html("""bar\nother stuff""")
assert "\r\n" not in test_result, test_result  # It can put some attributes if it wants to
test_result = mediawiki_to_html("{{foobar}}")
assert "{{foobar}}" in test_result, test_result
test_result = mediawiki_to_html("{{charname|Antal Yenis}}")
assert "{{charname|Antal Yenis}}" in test_result, test_result

RECURSIVE_INCLUDE_PAGES = ["Kelemen's Message", "timeline", "goals", "contacts", "packet"]
def resolve_arg_name_to_sheet(arg_name: str) -> str:
    coerced = arg_name.strip().title().replace(" ", "_").lower()
    # Check if it's a redirect, i.e. the content is "#REDIRECT [[<sheet name>]]"
    data = get_forkbomb_v2_csv(coerced)
    if data and data.startswith("#REDIRECT"):
        redirect = data.split("[[")[1].split("]]")[0]
        if redirect.startswith("Template:"):
            redirect = redirect.split(":")[1]
        return resolve_arg_name_to_sheet(redirect)
    return coerced

def fix_page_breaks(string):
    """ Replace
            <div style="page-break-before: always">
            ...
            </div>
        with
            <div class="pagebreak"></div>
            ...
    """
    return re.sub(r'<div style="page-break-before: always">\s*(.*)\s*</div>', r'<div class="pagebreak"></div>\n\1', string)

@lru_cache(maxsize=1000)
def page_content(page_name):
    lookup_name = resolve_arg_name_to_sheet(page_name)
    page_content = get_forkbomb_v2_csv(lookup_name)
    page_content = fix_page_breaks(page_content)
    if page_content is None:
        print(f"Failed Page Include: {page_name}")
        return
    return page_content

@lru_cache(maxsize=1000)
def recursively_include_pages(string:str):
    """
    replace {{ :page name }}
    with the contents of that page
    """
    all_macros = re.findall(r"\{\{\s*:\s*([^\}^\{^\|]*)\}\}", string)
    for page_name in all_macros:
        try:
            recursively_resolved_content = recursively_include_pages(page_content(page_name))
            string = re.sub(r"\{\{\s*:\s*" + page_name + r"\s*\}\}", recursively_resolved_content, string, count=1)
        except KeyError:
            print(f"Failed to include page: {page_name}")

    for page_name in RECURSIVE_INCLUDE_PAGES:
        resolved_content = page_content(page_name)
        string = re.sub(r"\{\{\s*" + page_name + r"\s*\}\}", resolved_content, string)
    return string

@lru_cache(maxsize=1000)
def get_expanded_content(sheet_name, convert_html=False):
    """
    Get the content of a sheet, with all the includes resolved
    """
    content = page_content(sheet_name)
    content = recursively_include_pages(content)
    if convert_html:
        content = mediawiki_to_html(content)
    return content

def build_forkbomb_names_dict(forkbomb_data):
    """
    Some sheet start with:
    {{character | IL=Dogmas | name=<name> | nick=<foo> | ... }}
    We want to gather those up
    """
    names = {}
    for sheet_name in forkbomb_data.keys():
        try:
            sheet_content = get_expanded_content(sheet_name)
        except KeyError:
            print(f"Failed to get content for {sheet_name}")
            continue
        except RecursionError:
            print(f"Recursion error for {sheet_name}")
            continue
        regex = re.compile(r"\s*{{\s*character\s*\|\s*IL=[Dd]ogmas\s*\|([^\}]*)\}\}")
        match = regex.search(sheet_content)
        if match is not None:
            names[sheet_name] = {}
            data = match.groups()[0]
            pieces = data.split('|')  # e.g. "  name=foo  "
            for piece in pieces:
                split = piece.strip().split('=')
                if len(split) != 2:
                    continue
                var, val = split
                names[sheet_name][var.strip()] = val.strip()
    return names
forkbomb_names = build_forkbomb_names_dict(forkbomb_v2_csv)

def build_sheets_dict(forkbomb_data) -> Dict[str, str]:    
    """
    Greensheets includes documents also.
    Starting with {{greensheet|IL=Dogmas|name=<name>|...}}
    or {{document|IL=Dogmas|name=<name>|...}}
    """
    sheet_names = {}
    for sheet_name in forkbomb_v2_csv.keys():
        try:
            sheet_content = get_expanded_content(sheet_name)
        except KeyError:
            print(f"Failed to get content for {sheet_name}")
            continue
        except RecursionError:
            print(f"Recursion error for {sheet_name}")
            continue
        regex = re.compile(r"\s*\{\{\s*(greensheet|document|whitesheet|bluesheet|yellowsheet|character)\s*\|\s*IL\s?=\s?[Dd]ogmas\s*\|([^\}]*)\}\}")

        match = regex.search(sheet_content)
        if match is not None:
            args = match.groups()[1]
            # Need to avoid splitting on |s inside nested args
            # e.g. {{foo|bar={{baz|qux}}|quux=corge}}
            # becomes
            # ['foo', 'bar={{baz|qux}}', 'quux=corge']
            # instead of
            # ['foo', 'bar={{baz', 'qux}}', 'quux=corge']
            matches = re.findall(r"\{\{([^\}]*)\}\}", args)
            for m in matches:
                args = args.replace(m, m.replace("|", "PIPE"))
            args = args.split('|')
            args = [arg.replace("PIPE", "|") for arg in args]
            args_split = [arg.split('=') for arg in args]
            args_dict = {arg[0].strip(): arg[1].strip() for arg in args_split if len(arg) == 2}
            if not all([len(arg) == 2 for arg in args_split]):
                print(f"Failed to parse {sheet_name}'s args: {args}, going with best guess {args_dict}")
            sheet_names[sheet_name] = args_dict
    return sheet_names
forkbomb_sheets = build_sheets_dict(forkbomb_v2_csv)

FORKBOMB_OBSOLETE_SHEETS = {
    'ambran_greensheet', 'kazkan_greensheet', 'kazkan_greensheet_berlo', 'rihul_greensheet', 'tzonkan_greensheet', 'varga_greensheet',
    'erszi_bakos', 'ambrus_writings', 'council_of_eminents:_current_business', 'history_of_garhdony', "mahdzo's_demons", "dogmas_succession_hunts",
    'lorink_toggle_x', 'ritual_to_locate_prophet_detector', 'rihulian_economy', 'janna_kohvari_run2', 'pahla_harsanyi',
    # these aren't obsolete but they are interior templates or just pngs
    'herbology', 'dogmas_magic_cheat_sheet', 
    'garhdony_map', 'hunt_manor_map_hunts', 'hunt_wood_map', 'hunt_wood_map_hunts', 'vargan_economic_notes'
    }
OK_UNMAPPED_GARHDONY = {
    'ambran_economic_notes', 'kazkan_economic_notes', 'tzonkan_economic_notes', 'temesvar_economic_plans', 'cathedral_of_kelemen_construction_plans', 'cathedral_of_sandor_construction_plans', 'church_maintenance_plans', "spider's_notes",\
    'teaser_story', 'vargan_teaser_story', 'the_rules_of_tzikka',
    'map_of_garhdony', 'hunt_manor_map', 'hunt_wood_map', 'hunt_wood_map_public', 'old_map_of_hunt_wood'
    }
MANUAL_MAP = {
    'adorra_magic_sheet': 'adorran_magic_sheet', 
    'antal_magic_sheet': 'anika_magic_sheet',
    'balaas_magic_sheet': 'balissa_magic_sheet',
    'isti_magic_sheet': 'izar_magic_sheet',
    'janna_magic_sheet': 'rikhard_magic_sheet',
    'venz_hajnal': 'valeri_hajnal',
    'tiborc_kertehsz_magar': 'tibarre_kertehsz_magar',
    'ottho_kazka_magar': 'olga_kazka_magar',

    'unraveling': 'unraveling_runes',
    'runebook': 'standard_temesvar_runebook',
    'dogmas_magic_temesvar': 'magic_temesvar',
    'dogmas_magic_hunts': 'magic_hunts',
    'magari_nonhell': 'magar_possession_non-hell',
    'magari': 'magar_possession',
    'demon_summoning_spell': 'how_to_summon_demons',
    'council_of_eminents': 'priesthood_leadership',
    'council_of_eminents_matyas_varadi': 'priesthood_leadership_matya',
    'recent_history_of_kazka_hunts': 'kazka_hunts',
    'opening_the_gate': 'opening_the_gate_of_the_gods',
}
MANUAL_MAP_NONSHEET_FORKBOMB_PAGE = {
    'costuming': 'costuming_advice',
    'general_rules': 'general_rules',
    'storyteller_quick_reference': 'storyteller_quick_reference',
    'npc_guide': 'storyteller_guide',
}
def construct_sheet_mapping():
    unmatched_forkbomb = set([s for s in forkbomb_sheets.keys() if not get_forkbomb_v2_csv(s).startswith("#REDIRECT") and s not in FORKBOMB_OBSOLETE_SHEETS])
    unmatched_garhdony = {standardize_name(sheet.filename): sheet for sheet in Sheet.objects.filter(game=game)}
    unmatched_garhdony = {k:v for k, v in unmatched_garhdony.items() if not k.endswith("contact_photos") and k not in OK_UNMAPPED_GARHDONY}
    forkbomb_to_garhdony = {}
    forkbomb_to_npcs = {}
    garhdony_to_forkbomb = {}

    for fb, gh in MANUAL_MAP.items():
        print(f"MANUAL_MAP matching {fb} to {gh}")
        forkbomb_to_garhdony[fb] = unmatched_garhdony.pop(gh)
        garhdony_to_forkbomb[gh] = fb
        unmatched_forkbomb.remove(fb)
    for fb, gh in MANUAL_MAP_NONSHEET_FORKBOMB_PAGE.items():
        print(f"MANUAL_MAP matching {fb} to {gh}")
        forkbomb_to_garhdony[fb] = unmatched_garhdony.pop(gh)
        garhdony_to_forkbomb[gh] = fb
        

    # Match by sheet internal name
    for standardized_filename, sheet in list(unmatched_garhdony.items()):
        if standardized_filename in unmatched_forkbomb:
            print(f"SAME NAME matching {standardized_filename} to {sheet}")
            forkbomb_to_garhdony[standardized_filename] = sheet
            garhdony_to_forkbomb[sheet] = sheet.name
            unmatched_forkbomb.remove(standardized_filename)
            unmatched_garhdony.pop(standardized_filename)
    
    # Match NPCs
    garhdony_npcs = {standardize_name(npc.name()): npc for npc in NonPlayerCharacter.objects.filter(game=game)}
    garhdony_npcs.update({standardize_name(npc.full_name()): npc for npc in NonPlayerCharacter.objects.filter(game=game)})
    for sheet_name in list(unmatched_forkbomb):
        if sheet_name in garhdony_npcs:
            print(f"NPC NAME matching {sheet_name} to {garhdony_npcs[sheet_name]}")
            forkbomb_to_npcs[sheet_name] = garhdony_npcs[sheet_name]
            unmatched_forkbomb.remove(sheet_name)

    # Match by sheet title
    possible_names_lookup = defaultdict(list)  # alternate_name: [sheet_name]   a list so itcan have more than one if there's a collision
    for sheet_name in sorted(list(unmatched_forkbomb)):
        info_dict = forkbomb_sheets[sheet_name]
        possible_names = set()
        for key in 'title', 'name', 'nick':
            if key in info_dict:
                possible_names.add(info_dict[key])
        if len(possible_names) == 0:
            print(f"Failed to find name for {sheet_name}; had {info_dict}")

        possible_names = possible_names.union([name.replace('_', ' ') for name in possible_names])
        
        possible_names = possible_names.union([name.capitalize() for name in possible_names])
        possible_names = possible_names.union([name.title() for name in possible_names])
        possible_names = possible_names.union([name[4:] for name in possible_names if name.startswith('The ')])
        possible_names = possible_names.union(["The " + name for name in possible_names])
        possible_names = possible_names.union([name[7:] for name in possible_names if name.startswith('Dogmas ')])
        for name in possible_names:
            possible_names_lookup[name].append(sheet_name)
    for alternate, sheet_names in possible_names_lookup.items():
        sheets = [(standardized_name, sheet) for standardized_name, sheet in unmatched_garhdony.items() if sheet.name.render() == alternate]
        if len(sheets) == 0:
            continue
        if len(sheets) > 1:
            print(f"Multiple matches in garhdony for {alternate}: {sheets}")
            continue
        g_sheet, sheet = sheets[0]

        if len(sheet_names) > 1:
            print(f"Multiple matches in forkbomb for {alternate}: {sheet_names}")
            continue
        f_sheet = sheet_names[0]
        if f_sheet not in unmatched_forkbomb:
            print(f"Already matched {f_sheet} to {forkbomb_to_garhdony[f_sheet]}; can't match to {sheet.filename} (display name '{alternate}')")
            continue
        if g_sheet not in unmatched_garhdony:
            print(f"Already matched {g_sheet} to {garhdony_to_forkbomb[g_sheet]}; can't match to {f_sheet} (display name '{alternate}')")
            continue
        print(f"PRINTED NAME matching {f_sheet} to {sheet.filename} (display name '{alternate}'))")
        forkbomb_to_garhdony[sheet_name] = sheet
        garhdony_to_forkbomb[sheet] = sheet.filename
        unmatched_forkbomb.remove(f_sheet)
        unmatched_garhdony.pop(g_sheet)

    if len(unmatched_forkbomb) > 0:
        print(f"Unmatched forkbomb ({len(unmatched_forkbomb)}): {sorted(unmatched_forkbomb)}")
    if len(unmatched_garhdony) > 0:
        print(f"Unmatched garhdony ({len(unmatched_garhdony)}): {sorted(unmatched_garhdony.keys())}")
    return forkbomb_to_garhdony, garhdony_to_forkbomb
sheets_mapping_f2g, sheets_mapping_g2f = construct_sheet_mapping()

SPECIAL_NAME_MAP = {"Mister Nicalao": "Nicalao Gazpahr", "Janna Kohvari": "Rikhard Kohvari", "Zofiya": "Isti Majoras", "Sandor": "Adorra Salom", "Marika": "Venz Hajnal"}
@lru_cache(maxsize=1000)
def character_from_name(name:str):
    """
    Name is "First Last" or just "First" or "First_Last"
    """
    if name in sheets_mapping_f2g:
        gh_sheet = sheets_mapping_f2g[name]
        name = gh_sheet.name.render()
    if name in SPECIAL_NAME_MAP:
        name = SPECIAL_NAME_MAP[name]
    name = name.strip()
    if " " in name or "_" in name:
        first, last = re.split(r" |_| ", name, maxsplit=1)
    else:
        first, last = name, None
    possibilities = set(list(GenderizedName.objects.filter(male=first, character__game=game)) + list(GenderizedName.objects.filter(female=first, character__game=game)))
    correct_last = set(name_obj for name_obj in possibilities if name_obj.character.last_name == last)
    if len(correct_last) == 0:
        logger.info(f"Failed Name Search: Couldn't find {name}")
        return None
    elif len(correct_last) == 1:
        return correct_last.pop().character.cast()  # Cast to PC
    else:
        logger.info(f"Failed Name Search: Multiple {name}: {[name_obj.character for name_obj in correct_last]}")
        return None
        

def try_get_keyword(male, female):
    try:
        return GenderizedKeyword.objects.get(male=male, female=female)
    except GenderizedKeyword.DoesNotExist:
        return None

@lru_cache(maxsize=1000)
def keyword_from_name(string:str) -> Tuple[str, bool]:
    """
    string is like 'he-she'
    """
    if string.strip().endswith("-cap"):
        male, female = string.strip()[:-4].split("-")
        cap=True
    else:
        male, female = string.strip().split("-")
        cap=False
    # If a matching keyword exists, get it out of the database
    result = try_get_keyword(male=male, female=female)
    if result is not None:
        return result, cap
    
    # Try backward ("aunt/uncle")
    result = try_get_keyword(male=female, female=male)
    if result is not None:
        return result, cap
    
    # Try capitalized ("King/Queen")
    result = try_get_keyword(male=male.capitalize(), female=female.capitalize())
    if result is not None:
        return result, cap

    logger.info(f"Failed Keyword Search: No keyword {male}-{female}")
    return None, False


def macro_hit_replace(macro_name:str, string:str, callback:Callable[[str, List[str]], str]):
    """
    macro_name can be regex
    callback(macro, args_list) -> replacement_string

    Find all instances of {{ macro_name }} or {{ macro_name | <arg1> }}, {{ macro_name | <arg1> | <arg2> }}, etc.

    Replace with callback([arg1, arg2, ...])

    Doesn't handle nested macros; ignores the outer one.
    """
    # regex to get macro and ensure all args don't have braces in them
    # e.g. {{ macro_name | arg1 | arg2 }} -> ("macro_name", ["arg1", "arg2"])
    # but not {{ macro_name | arg1 | {{arg2}} }}, that's simply not a hit
    regex = re.compile(r"\{\{\s*(" + macro_name + r")\s*(?:\|([^\}\{]*))?\}\}")
    hits = re.findall(regex, string)
    cleaned_hits = []
    for hit in hits:
        macro, args = hit[0], hit[1].split("|") if len(hit) > 1 and len(hit[1])>0 else []
        macro = macro.strip()

        args = tuple([arg.strip() for arg in args])
        cleaned_hits.append((macro, args))
    cleaned_hits = set(cleaned_hits)

    for macro, args in cleaned_hits:
        replacement = callback(macro, args)
        if replacement is not None:
            # Replace uses of this particular macro + args with the replacement
            this_regex = re.compile(r"\{\{\s*" + macro + "".join([r"\s*\|\s*" + re.escape(arg) for arg in args]) + r"\s*\}\}")
            string = re.sub(this_regex, replacement, string)

    return string

"""
====================================================================================================
"""

def clear_unused_tags(string:str) -> str:
    """
    Remove these tags:
      {{ Primary Author | ... }}

    """
    TAGS = ["Primary Author", "PreviousPlayer", "character", "Player", "blurb", "in group", "dogmas update", "status", "Status", "greensheet", "yellowsheet", "whitesheet", "bluesheet"]
    for tag in TAGS:
        string = macro_hit_replace(tag, string, lambda macro, args: "")
    return string
assert clear_unused_tags("foo {{ Primary Author | author }} bar {{Player}}") == "foo  bar ", clear_unused_tags("foo {{ Primary Author | author }} bar {{Player}}")

def resolve_charname_and_charnicks(string: str) -> str:
    """
    replace all {{ charname | <sheet name>}} with the corresponding character name in forkbomb_names
    similarly charnick
    """
    def split_arg(arg):
        try:
            key, val = arg.split("=")
            return key.strip(), val.strip()
        except ValueError:
            logger.info(f"Failed to split arg in charname {arg}")
            return None, None
    def charname_callback(_macro, args):
        lookup_name = resolve_arg_name_to_sheet(args[0])
        name_dict = forkbomb_names[lookup_name]

        args_dict = {split_arg(arg)[0]: split_arg(arg)[1] for arg in args[1:]}
        nick = 'nick' in args_dict and args_dict['nick']
        alias = 'alias' in args_dict and args_dict['alias']
        if nick and alias:
            name_key = "aliasnick"
        elif nick and not alias:
            name_key = "nick"
        elif alias and not nick:
            name_key = "alias"
        else:
            name_key = "name"
        try:
            return name_dict[name_key]
        except KeyError:
            logger.info(f"Failed to find {name_key} for {lookup_name}; had: {forkbomb_names[lookup_name]}")
            return None
    string = macro_hit_replace("charname", string, charname_callback)
    
    def charnick_callback(_macro, args):
        lookup_name = resolve_arg_name_to_sheet(args[0])
        name_dict = forkbomb_names[lookup_name]
        
        try:
            return name_dict['nick']
        except KeyError:
            logger.info(f"Failed to find {'nick'} for {lookup_name}; had: {forkbomb_names[lookup_name]}")
            return None
    string = macro_hit_replace("charnick", string, charnick_callback)
    return string

test_result = resolve_charname_and_charnicks("foo {{ charname | Berlo Hunt }} bar {{charname|Nemeth Hunt|nick=1}} baz {{charnick|Nemeth Hunt}}")
assert test_result == "foo Berlo Hunt bar Nemmy baz Nemmy", test_result


def replace_genderized_keywords(string: str) -> str:
    """
    replace {{ he-she | Character Name }}
    with a genderized keyword html span
    """
    def keyword_callback(macro, args):
        try:
            keyword, capitalized = keyword_from_name(macro)
        except:
            logger.info(f"Failed Keyword Search: {macro}|{args}")
            return None
        if keyword is None:
            logger.info(f"Failed Keyword Search: {macro}|{args}")
            return None
        # Try to get the character
        assert len(args) == 1
        name = args[0].strip()
        character = character_from_name(name)
        if character is None:
            logger.info(f"Failed Character Search: {macro}|{name}")
            return None
        node = newGenderSwitchNodeGeneric(keyword, character, character.gender(), capitalize=capitalized)
        new_markup = node.raw()
        return new_markup
    macro_regex = r"[^\}^\{^\|]*-[^\}^\{^\|]*"
    string = macro_hit_replace(macro_regex, string, keyword_callback)
    return string
test_result = replace_genderized_keywords("foo {{ he-she | Berlo Hunt }} bar {{aunt-uncle|Nemeth Hunt}} baz {{him-her|Nemeth Hunt}}")
assert re.match(r"foo <span [^\>]*>he<span [^\>]*>she</span></span> bar <span [^\>]*>aunt<span [^\>]*>uncle</span></span> baz <span [^\>]*>her<span [^\>]*>him</span></span>", test_result), test_result

def character_stats_check(string:str, sheet_name) -> str:
    """
    If the sheet is a main character sheet, check the stats on the sheet against the database
    """
    STATS = [("age", "Age"), ("CR", "Combat Rating"), ("patron", "Patron Ascended")]
    character = character_from_name(sheet_name)
    def callback_check_stat(db_stat_name, forkbomb_tag_args):
        if character is None:
            logger.info(f"Stat on non-existent character: {db_stat_name}")
            return None
        if len(forkbomb_tag_args) > 1:
            assert len(forkbomb_tag_args)==2 and forkbomb_tag_args[1] == "show=1", f"Stat tag had too many args: {forkbomb_tag_args}"
        forkbomb_v2_value = forkbomb_tag_args[0].strip()
        db_value = character.get_stat(db_stat_name).strip()
        if forkbomb_v2_value != db_value:
            logger.info(f"Stat mismatch: {db_stat_name} {forkbomb_v2_value} != {db_value}")
        return ""

    for tag, db_stat in STATS:
        string = macro_hit_replace(tag, string, lambda macro, args: callback_check_stat(db_stat, args))

    return string

def check_has_greensheets(string: str, sheet_name: str) -> str:
    character = character_from_name(sheet_name)
    if character is not None:
        sheets = set(s.name.render() for s in character.sheets.all())
    def has_greensheet_callback(macro, args):
        assert character is not None, f"Failed to find character {sheet_name} for greensheet check {macro}|{args}"
        assert len(args) == 1
        greensheet_page_name = resolve_arg_name_to_sheet(args[0])
        try:
            greensheet_data = forkbomb_sheets[greensheet_page_name]
        except KeyError:
            logger.info(f"Failed to find greensheet {greensheet_page_name} for {sheet_name}")
            return None
        greensheet_name = greensheet_data["title"]
        if greensheet_name not in sheets:
            logger.info(f"Greensheet '{greensheet_name}' not found on character {sheet_name}; has {sheets}")
        return greensheet_name
    string = macro_hit_replace("has greensheet", string, has_greensheet_callback)
    string = macro_hit_replace("has document", string, has_greensheet_callback)
    string = macro_hit_replace("has yellowsheet", string, has_greensheet_callback)

    return string

def resolve_you_macro(string: str, sheet_name: str) -> str:
    def callback_you(macro, args, cap):
        assert len(args) == 1
        name = args[0].strip()
        if name == sheet_name:
            return "You" if cap else "you"
        else:
            # Need to escape the right number of braces so we get {{charnick|Bob}}
            return f"{{{{charnick|{name}}}}}"
    string = macro_hit_replace("you", string, lambda macro, args: callback_you(macro, args, False))
    string = macro_hit_replace("you-cap", string, lambda macro, args: callback_you(macro, args, True))
    return string

def resolve_date1276_macro(string: str) -> str:
    """
    replace {{ date1276 | date }}
    with date + 6 days
    This was customizeable in the old forkbomb, but I don't think it's worth it
    """
    def callback_date1276(macro, args):
        assert len(args) == 1
        original_date = args[0].strip()  # e.g. 'April 13'
        date = datetime.datetime.strptime(original_date, "%B %d")
        date += datetime.timedelta(days=6)
        new_date = date.strftime("%B %d")
        return new_date
    string = macro_hit_replace("date1276", string, callback_date1276)
    return string

def resolve_ifcastle_macro(string: str) -> str:
    """
    replace {{ ifcastle | <if-yes> | <if-no> }}
    """
    castle = False # TODO???
    def callback_ifcastle(macro, args):
        if len(args) == 1:
            # Defaults to empty string for the no case
            yes = args[0]
            no = ""
        elif len(args) == 2:
            yes, no = args
        else:
            raise ValueError(f"ifcastle macro had wrong number of args: {args}")
        if castle:
            return yes
        else:
            return no

    string = macro_hit_replace("ifCastle", string, callback_ifcastle)
    string = macro_hit_replace("IfCastle", string, callback_ifcastle)
    return string

def resolve_ifiam_macro(string: str, sheet_name: str) -> str:
    """
    replace {{ ifiam | <sheet name> | <if-yes> | <if-no> }}
    """
    def callback_ifiam(macro, args):
        if len(args) == 2:
            # Defaults to empty string for the no case
            name, yes = args
            no = ""
        elif len(args) == 3:
            name, yes, no = args
        else:
            raise ValueError(f"ifiam macro had wrong number of args: {args}")
        if name == sheet_name:
            return yes
        else:
            return no

    string = macro_hit_replace("ifiam", string, callback_ifiam)
    return string

def resolve_commentout_macro(string: str) -> str:
    """
    replace {{ CommentOut | <summary> | <text> }}
    """
    def callback_commentout(macro, args):
        assert len(args) == 2
        return WritersNode.new_html(type="hidden", visible_text=args[0], hover_text=args[1], hover_title="CommentOut (Imported wiki macro)")
    string = macro_hit_replace("CommentOut", string, callback_commentout)
    return string

def resolve_stnote_macro(string: str) -> str:
    """
    replace {{ STNote | <text> }}
    """
    def callback_stnote(macro, args):
        assert len(args) == 1
        result = WritersNode.new_html(type="stnote", visible_text="", hover_text=args[0], hover_title="STNote (Imported wiki macro)")
        return result
    string = macro_hit_replace("STnote", string, callback_stnote)
    return string
test_result = resolve_stnote_macro("foo{{ STnote | This is a test }} bar")
assert """ data-larp-action="stnote" """ in test_result, test_result

def resolve_todo_macro(string: str) -> str:
    """
    replace {{ ToDo | <text> }}
    """
    def callback_stnote(macro, args):
        assert len(args) == 1
        return WritersNode.new_html(type="todo", visible_text="", hover_text=args[0], hover_title="ToDo (Imported wiki macro)")
    string = macro_hit_replace("ToDo", string, callback_stnote)
    return string

def clear_hide_unhide(string):
    string = re.sub(r"\{\{\s*hide\s*\}\}\s*\{\{\s*unhide\s*\}\}", "", string)
    return string

def cleanup_ps(string: str) -> str:
    # Now we need to replace all the nice <p> tags with lame <br><br>s, because the editor doesn't like <p>s (they interfere with stnote spans)
    # First remove any useless empty p's
    string = re.sub(r"<p>\s*</p>", "", string)
    
    # Now replace the rest
    string = string.replace("</p>", "<br><br>")
    string = string.replace("<p>", "")
    return string

def all_processing(data: str, fb_sheet_name:str) -> str:
    braces_count = data.count("{{")
    logger.info(f"  Found {braces_count} templates in {fb_sheet_name}")

    data = resolve_you_macro(data, fb_sheet_name)
    data = replace_genderized_keywords(data)
    data = character_stats_check(data, fb_sheet_name)
    data = check_has_greensheets(data, fb_sheet_name)
    data = clear_unused_tags(data)
    data = resolve_charname_and_charnicks(data)
    data = resolve_ifcastle_macro(data)
    data = resolve_date1276_macro(data)
    data = resolve_ifiam_macro(data, fb_sheet_name)
    data = resolve_commentout_macro(data)
    data = resolve_stnote_macro(data)
    data = resolve_todo_macro(data)
    data = clear_hide_unhide(data)
    return data

def import_forkbomb_v2(fb_sheet_name:str):
    data = get_expanded_content(fb_sheet_name, convert_html=True)
    old_data = None
    iter = 0
    while old_data != data:
        logger.info(f"=== Iteration {iter} ===")
        old_data = data
        data = all_processing(data, fb_sheet_name)
        iter += 1
    data = cleanup_ps(data)
    return data

def import_forkbomb_v2_sheet(fb_sheet_name: str, garhdony_sheet: Sheet):
    data = import_forkbomb_v2(fb_sheet_name)
    remaining_templates = re.findall(r"\{\{[^}]*\}\}", data)
    reminaing_templates_str = "".join([f"\n  {t}" for t in remaining_templates])
    logger.info(f"""Remaining templates: {reminaing_templates_str}""")

    garhdony_sheet.content_type = 'html'
    garhdony_sheet.save()
    
    new_revision = SheetRevision(sheet=garhdony_sheet, content=LARPstring(data))
    new_revision.save()

    return remaining_templates

# Main function
# Get sheet name from args
def main():
    parser = argparse.ArgumentParser(description='Import a sheet from the wiki.')
    parser.add_argument('--sheet_name', metavar='sheet_name', type=str, help='The name of the sheet to import')
    parser.add_argument('--max_sheets', metavar='sheet_name', type=int, help='max sheets', required=False)

    args = parser.parse_args()
    
    sheet_name = standardize_name(args.sheet_name)
    if sheet_name == "all":
        BLACKLIST = "benkai_garmani"
        target_sheets = {k: v for k, v in sheets_mapping_f2g.items() if "magic_sheet" not in k and k not in BLACKLIST}
    else:
        target_sheets = {sheet_name: sheets_mapping_f2g[sheet_name]}

    unresolved_templates = {}
    for fb_name, gh_sheet in sorted(list(target_sheets.items()))[:args.max_sheets]:
        logger.info(f"\n\n======================\nImporting sheet {fb_name} to {gh_sheet}\n======================")
        unresolved_templates[fb_name] = import_forkbomb_v2_sheet(fb_name, gh_sheet)
    logger.info(f"Unresolved templates:")
    for fb_name, templates in unresolved_templates.items():
        logger.info(f"  {fb_name}: {templates}")
    
if __name__ == "__main__":
    main()