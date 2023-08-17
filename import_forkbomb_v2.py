import argparse
from collections import Counter, defaultdict
import csv
import datetime
import django
from functools import lru_cache
import mwparserfromhell
import os
import re
from typing import Callable, Dict, List, Tuple

# setup stuff so django is happy
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from garhdony_app.LARPStrings import LARPstring
from garhdony_app.models import GenderizedKeyword, GenderizedName, Character, Sheet, GameInstance, SheetRevision, NonPlayerCharacter, PlayerCharacter
from garhdony_app.span_parser import WritersBubbleInnerNode, WritersNode, inlineAsideHTML, newComplexGenderSwitchNodeHTML, newGenderStaticNode, newGenderSwitchNode, newGenderSwitchNodeGeneric


import logging
# Logging config that prints to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger("garhdony_app.LARPStrings").setLevel(logging.INFO)
# django.db.backends
logging.getLogger('django.db.backends').setLevel(logging.ERROR)


GAME_NAME = "DogmasCloneTest8"
game = GameInstance.objects.get(name=GAME_NAME)

def database_cleanup():
    buggy_problem_title = GenderizedKeyword.objects.get(male="BUGGY_PROBLEM_TITLE")
    for char in game.characters.all():
        if char.title_obj == buggy_problem_title:
            char.title_obj = None
            char.save()
    if not GenderizedKeyword.objects.filter(male="men", female="women", category="pronoun").exists():
        mw = GenderizedKeyword(male="men", female="women", category="pronoun")
        mw.save()
    
    for m, f, l, g, u in [
        ("Sammi", "Sammi", "Ehroz", "F", "sehroz"), 
        ("Dominik", "Domnika", "Zhell", "F", "dzhell"), 
        ("????", "Katalin", "Aller", "F", "kaller"),
        ("Rikhard", "????", "Kohvari", "M", "rkohvari"),
        ("????", "Timea", "Hunt", "F", "thunt")]:
        if PlayerCharacter.objects.filter(game=game, last_name=l, first_name_obj__male=m, first_name_obj__female=f).exists():
            print(f"Already created { m } { f } { l }")
        else:
            name = GenderizedName(male=m, female=f)
            new_char = PlayerCharacter(first_name_obj=name, last_name=l, default_gender=g, game=game, username=u)
            new_char.save()
            print(f"Created { m } { f } { l }")
        char = PlayerCharacter.objects.get(game=game, last_name=l, first_name_obj__male=m, first_name_obj__female=f)

        char_sheet = Sheet.objects.get(game=game, filename=char.name())
        char.sheets.add(char_sheet)
        char.save()

    for m, f, l, g in [
        ("Pahl", "Pahla", "Harsanyi", "F"),
    ]:
        if NonPlayerCharacter.objects.filter(game=game, last_name=l, first_name_obj__male=m, first_name_obj__female=f).exists():
            print(f"Already created { m } { f } { l }")
        else:
            name = GenderizedName(male=m, female=f)
            new_char = NonPlayerCharacter(first_name_obj=name, last_name=l, gender_field=g, game=game)
            new_char.save()
            print(f"Created { m } { f } { l }")
        

database_cleanup()

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

def cleanup_ps(string: str) -> str:
    # Now we need to replace all the nice <p> tags with lame <br><br>s, because the editor doesn't like <p>s (they interfere with stnote spans)
    # First remove any useless empty p's
    string = re.sub(r"<p>\s*</p>", "", string)
    
    # Now replace the rest
    string = string.replace("</p>", "<br><br>")
    string = string.replace("<p>", "")
    return string

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
    # We also don't want pandoc screwing with [[...]] links, so we escape those too
    
    num_braces = string.count("{"), string.count("}"), string.count("|"), string.count("["), string.count("]")
    safe_string = string.replace("{{", "DOUBLEOPENBRACE")
    safe_string = safe_string.replace("}}", "DOUBLECLOSEBRACE")
    safe_string = safe_string.replace("|", "PIPE")
    safe_string = safe_string.replace("[[", "DOUBLEOPENBRACKET")
    safe_string = safe_string.replace("]]", "DOUBLECLOSEBRACKET")
    # Add args to avoid extra linebreaks due to wrapping and headings.
    convert_safe_string = pypandoc.convert_text(safe_string, "html", format="mediawiki", extra_args=["--wrap=none", "--no-highlight"])
    output_string = convert_safe_string.replace("DOUBLEOPENBRACE", "{{")
    output_string = output_string.replace("DOUBLECLOSEBRACE", "}}")
    output_string = output_string.replace("PIPE", "|")
    output_string = output_string.replace("DOUBLEOPENBRACKET", "[[")    
    output_string = output_string.replace("DOUBLECLOSEBRACKET", "]]")
    # Check the number of braces is right
    try:
        new_num_braces = output_string.count("{"), output_string.count("}"), output_string.count("|"), output_string.count("["), output_string.count("]")
        assert num_braces == new_num_braces, f"num_braces {num_braces} != new_num_braces {new_num_braces}"
    except AssertionError as e:
        print(e)
        import pdb; pdb.set_trace()
    clean_output_string = cleanup_ps(output_string).strip()
    return clean_output_string
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

RECURSIVE_INCLUDE_PAGES = ["Kelemen's Message", "timeline", "goals", "contacts", "packet", "AWhile"]
def resolve_arg_name_to_sheet(arg_name: str) -> str:
    coerced = standardize_name(arg_name)
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

def manual_fixes(string):
    TYPOS = {
        "{{charname | Matya Varadi}}": "{{charname | Matyas Varadi}}",  # gizella tzonka
        "{{charnick|Antal}}": "{{charnick|Antal Yenis}}",   # 
        "{{charname|Aleksander ZaHunt|alias=1|aliasnick=1}}": "{{charname|Aleksander ZaHunt|nick=1}}",   # some hunts
        """ green rule.)}}</li>\n</ul>""": """ green rule.)</li>\n</ul>}}""",   # artificer's knowledge
        """ green rule.)}}</li>\r\n</ul>""": """ green rule.)</li>\r\n</ul>}}""",  # artificer's knowledge
        """<strong>Litzeer</strong> }}</li>\n</ul></li>\n</ul>""" : """<li>Freeze: <strong>Litzeer</strong> </li>\n</ul></li>\n</ul> }}""",  # magari
        """<strong>Litzeer</strong> }}</li>\r\n</ul></li>\r\n</ul>""" : """<li>Freeze: <strong>Litzeer</strong> </li>\n</ul></li>\n</ul> }}""",  # magari
        """appear by mid-April.}}</li>\r\n</ul>""": """appear by mid-April.</li>\n</ul>}}""",  # council of eminents
        """appear by mid-April.}}</li>\n</ul>""": """appear by mid-April.</li>\n</ul>}}""",  # council of eminents
        """==Current Business==""": "<h2>Current Business</h2>",  # council of eminents
        """{{hide}} {{has ability | Signatory for Rihul}} {{unhide}}""": "{{has ability | Signatory for Rihul}}",  # Rammy
        """<code>\xa0|\xa0}}</code>""": "|}}",  # Opening the Gate
        """Today.}}</li>\r\n</ul>""": """April 25, 1276: Today.</li>\n</ul>}}""",  # hunt  manor
        """Today.}}</li>\n</ul>""": """April 25, 1276: Today.</li>\n</ul>}}""",  # hunt  manor
        """this high?}}</li>\r\n</ol>""": """this high?</li>\n</ol>}}""",  # general rules
        """this high?}}</li>\n</ol>""": """this high?</li>\n</ol>}}""",  # general rules
        """should be monitered.}}</li>\r\n</ul>""": """should be monitered.</li>\n</ul>}}""",  # temesvar academy
        """should be monitered.}}</li>\n</ul>""": """should be monitered.</li>\n</ul>}}""",  # temesvar academy
        """Departures.}}</li>\r\n</ul>""": """Departures.</li>\n</ul>}}""",  # order of almos
        """Departures.}}</li>\n</ul>""": """Departures.</li>\n</ul>}}""",  # order of almos
        """302</em>}}</li>\r\n</ol></li>\r\n</ol></li>\r\n</ol>""": """302</em></li>\n</ol></li>\n</ol></li>\n</ol>}}""",  # keepers evidence
        """302</em>}}</li>\n</ol></li>\n</ol></li>\n</ol>""": """302</em></li>\n</ol></li>\n</ol></li>\n</ol>}}""",  # keepers evidence
        """{{g|Ramestor Rihul|princes and princesses|prince and princesses}}""": """{{g|Ramehstor Rihul|princes and princesses|prince and princesses}}""", # Matyas
        }
    for typo, fix in TYPOS.items():
        string = string.replace(typo, fix)
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
    content = manual_fixes(content)
    return content

def build_forkbomb_sheets_dict(forkbomb_data):
    """
    Some sheet start with:
    {{character | IL=Dogmas | name=<name> | nick=<foo> | ... }}
    We want to gather those up
    """
    sheet_names = {}
    for sheet_name in forkbomb_data.keys():
        try:
            sheet_content = get_expanded_content(sheet_name)
        except KeyError:
            print(f"Failed to get content for {sheet_name}")
            continue
        except RecursionError:
            print(f"Recursion error for {sheet_name}")
            continue
        wikicode = mwparserfromhell.parse(sheet_content)
        templates = wikicode.filter_templates()

        SHEET_DEFINING_TEMPLATES = ['greensheet', 'document', 'whitesheet', 'bluesheet', 'yellowsheet', 'character']
        sheet_templates = [t for t in templates if t.name.strip() in SHEET_DEFINING_TEMPLATES]
        if len(sheet_templates) > 0:
            assert len(sheet_templates) == 1, f"Multiple sheet templates found for {sheet_name}"
            sheet_template = sheet_templates[0]
            param_dict = {p.name.strip(): p.value.strip() for p in sheet_template.params}
            param_dict['color'] = sheet_template.name.strip()

            if 'IL' in param_dict and param_dict['IL'].lower() == 'dogmas':
                sheet_names[sheet_name] = param_dict
    return sheet_names
forkbomb_sheets = build_forkbomb_sheets_dict(forkbomb_v2_csv)

FORKBOMB_OBSOLETE_SHEETS = {
    'ambran_greensheet', 'kazkan_greensheet', 'kazkan_greensheet_berlo', 'rihul_greensheet', 'tzonkan_greensheet', 'varga_greensheet',
    'erszi_bakos', 'ambrus_writings', 'council_of_eminents:_current_business', 'history_of_garhdony', "mahdzo's_demons", "dogmas_succession_hunts",
    'lorink_toggle_x', 'ritual_to_locate_prophet_detector', 'rihulian_economy', 'janna_kohvari_run2',
    # these aren't obsolete but they are interior templates or just pngs
    'herbology', 'dogmas_magic_cheat_sheet', 
    'garhdony_map', 'hunt_manor_map_hunts', 'hunt_wood_map', 'hunt_wood_map_hunts', 'vargan_economic_notes', 'runebook'
    }
OK_UNMAPPED_GARHDONY = {
    'ambran_economic_notes', 'kazkan_economic_notes', 'tzonkan_economic_notes', 'temesvar_economic_plans', 'cathedral_of_kelemen_construction_plans', 'cathedral_of_sandor_construction_plans', 'church_maintenance_plans', "spider's_notes",\
    'teaser_story', 'vargan_teaser_story', 'the_rules_of_tzikka',
    'map_of_garhdony', 'hunt_manor_map', 'hunt_wood_map', 'hunt_wood_map_public', 'old_map_of_hunt_wood', 'standard_temesvar_runebook',
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
    forkbomb_to_garhdony = {}  # fb_name: Sheet
    forkbomb_to_npcs = {} 
    garhdony_to_forkbomb = {}  # Sheet: fb_name

    for fb, gh in MANUAL_MAP.items():
        # print(f"MANUAL_MAP matching {fb} to {gh}")
        forkbomb_to_garhdony[fb] = unmatched_garhdony.pop(gh)
        garhdony_to_forkbomb[gh] = fb
        unmatched_forkbomb.remove(fb)
    for fb, gh in MANUAL_MAP_NONSHEET_FORKBOMB_PAGE.items():
        # print(f"MANUAL_MAP matching {fb} to {gh}")
        forkbomb_to_garhdony[fb] = unmatched_garhdony.pop(gh)
        garhdony_to_forkbomb[gh] = fb
        

    # Match by sheet internal name
    for standardized_filename, sheet in list(unmatched_garhdony.items()):
        if standardized_filename in unmatched_forkbomb:
            # print(f"SAME NAME matching {standardized_filename} to {sheet}")
            forkbomb_to_garhdony[standardized_filename] = sheet
            garhdony_to_forkbomb[sheet] = standardized_filename
            unmatched_forkbomb.remove(standardized_filename)
            unmatched_garhdony.pop(standardized_filename)
    
    # Match NPCs
    garhdony_npcs = {standardize_name(npc.name()): npc for npc in NonPlayerCharacter.objects.filter(game=game)}
    garhdony_npcs.update({standardize_name(npc.full_name()): npc for npc in NonPlayerCharacter.objects.filter(game=game)})
    for sheet_name in list(unmatched_forkbomb):
        if sheet_name in garhdony_npcs:
            # print(f"NPC NAME matching {sheet_name} to {garhdony_npcs[sheet_name]}")
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
        if len(sheet_names) == 0:
            #something has gone wrong.
            import pdb; pdb.set_trace()
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
        # print(f"PRINTED NAME matching {f_sheet} to {sheet.filename} (display name '{alternate}'))")
        forkbomb_to_garhdony[f_sheet] = sheet
        garhdony_to_forkbomb[sheet] = f_sheet
        unmatched_forkbomb.remove(f_sheet)
        unmatched_garhdony.pop(g_sheet)

    if len(unmatched_forkbomb) > 0:
        print(f"Unmatched forkbomb ({len(unmatched_forkbomb)}): {sorted(unmatched_forkbomb)}")
    if len(unmatched_garhdony) > 0:
        print(f"Unmatched garhdony ({len(unmatched_garhdony)}): {sorted(unmatched_garhdony.keys())}")
    return forkbomb_to_garhdony, garhdony_to_forkbomb, forkbomb_to_npcs
sheets_mapping_f2g, sheets_mapping_g2f, forkbomb_to_npcs = construct_sheet_mapping()


SPECIAL_NAME_MAP = {"Mister Nicalao": "Nicalao Gazpahr", "Janna Kohvari": "Rikhard Kohvari", "Ramehstor Rihul": "Ramestor Rihul"}
POSSESSION_MAP = {"Zofiya": ("Isti Majoras", "F"), "Sandor": ("Adorra Salom", "M"), "Marika": ("Venz Hajnal", "F")}
@lru_cache(maxsize=1000)
def character_from_name(name:str):
    """
    Name is "First Last" or just "First" or "First_Last"
    """
    fb_name = resolve_arg_name_to_sheet(name)
    if fb_name in sheets_mapping_f2g:
        gh_sheet = sheets_mapping_f2g[fb_name]
        if gh_sheet.characters.count() != 1:
            # import pdb; pdb.set_trace()
            logger.warning(f"Got {gh_sheet.characters.count()} characters for {name}")
            return None
        return gh_sheet.characters.first()
    elif fb_name in forkbomb_to_npcs:
        return forkbomb_to_npcs[fb_name]
    else:
        logger.warning(f"Couldn't find character for {name}")
        return None
test_result = character_from_name("Nemeth Hunt")
assert test_result is not None and test_result.name() == "Nemeth Hunt", f"Failed to find Nemeth Hunt: {test_result}"
test_result = character_from_name("Vilmos")
assert test_result is not None and test_result.name() in ["Verness", "Vilmos"], f"Failed to find Vilmos: {test_result}"

def try_get_keyword(male, female):
    for m, f in [(male, female), (male.lower(), female.lower()), (male.capitalize(), female.capitalize())]:
        try:
            return GenderizedKeyword.objects.get(male=m, female=f)
        except GenderizedKeyword.DoesNotExist:
            continue
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
    
    logger.warning(f"Failed Keyword Search: No keyword {male}-{female}")
    return None, False


# New version using mwparsefromhell:
def macro_hit_replace(macro_name:str, wikicode, callback:Callable[[str, List[str]], str]):
    """
    macro_name can be regex
    callback(macro, args_list) -> replacement_string

    Find all instances of {{ macro_name }} or {{ macro_name | <arg1> }}, {{ macro_name | <arg1> | <arg2> }}, etc.

    Replace with callback([arg1, arg2, ...])
    """
    for template in wikicode.filter_templates():
        template_macro = template.name.strip()
        if re.match(macro_name, template_macro, re.IGNORECASE):
            args = [arg.strip() for arg in template.params]
            try:
                replacement = callback(template_macro, args)
            except Exception as e:
                e.args += (template,)
                raise e
            if replacement is not None:
                # replace the entire template node with the replacement
                try:
                    wikicode.replace(template, replacement)
                except ValueError:
                    # print(f"Failed to replace {template} with '{replacement}'")
                    # Can try to continue; maybe we already removed it due to an outer macro
                    pass
    return wikicode

"""
====================================================================================================
"""

def clear_unused_tags(string:str) -> str:
    """
    Remove these tags:
      {{ Primary Author | ... }}

    """
    TAGS = ["Primary Author", "PreviousPlayer", "character", "Player", "blurb", "in group", "dogmas update", "status", "Status", "greensheet", "yellowsheet", "whitesheet", "bluesheet", "document", "group info", "has plot", "STPage"]
    for tag in TAGS:
        string = macro_hit_replace(tag, string, lambda macro, args: "")
    return string
assert clear_unused_tags(mwparserfromhell.parse("foo {{ Primary Author | author }} bar {{Player}}")) == "foo  bar ", clear_unused_tags("foo {{ Primary Author | author }} bar {{Player}}")

def resolve_pagebreak_macro(string) -> str:
    """
    Replace {{pagebreak}} with <div class="pagebreak"></div>
    """
    return macro_hit_replace("pagebreak", string, lambda macro, args: '<div class="pagebreak"></div>')

def resolve_chapter_macro(string) -> str:
    """
    Replace {{pagebreak}} with <div class="pagebreak"></div>
    """
    def chapter_callback(_macro, args):
        assert len(args) == 1
        return f'<h2>{args[0]}</h2>'
    return macro_hit_replace("chapter", string, chapter_callback)

def resolve_charname_and_charnicks(string):
    """
    replace all {{ charname | <sheet name>}} with the corresponding character name in forkbomb_sheets
    similarly charnick
    """
    def split_arg(arg):
        try:
            key, val = arg.split("=")
            return key.strip(), val.strip()
        except ValueError:
            logger.warning(f"Failed to split arg in charname {arg}")
            return None, None
    def charname_callback(_macro, args):
        lookup_name = resolve_arg_name_to_sheet(args[0])
        name_dict = forkbomb_sheets[lookup_name]

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
            logger.warning(f"Failed to find {name_key} for {lookup_name}; had: {forkbomb_sheets[lookup_name]}")
            return None
    string = macro_hit_replace("charname", string, charname_callback)
    
    def charnick_callback(_macro, args):
        lookup_name = resolve_arg_name_to_sheet(args[0])
        name_dict = forkbomb_sheets[lookup_name]
        
        try:
            return name_dict['nick']
        except KeyError:
            logger.warning(f"Failed to find {'nick'} for {lookup_name}; had: {forkbomb_sheets[lookup_name]}")
            return None
    string = macro_hit_replace("charnick", string, charnick_callback)

    def charaliasnick_callback(_macro, args):
        lookup_name = resolve_arg_name_to_sheet(args[0])
        name_dict = forkbomb_sheets[lookup_name]
        
        try:
            return name_dict['aliasnick']
        except KeyError:
            logger.warning(f"Failed to find {'aliasnick'} for {lookup_name}; had: {forkbomb_sheets[lookup_name]}")
            return None
    string = macro_hit_replace("charaliasnick", string, charaliasnick_callback)
    return string

test_result = resolve_charname_and_charnicks(mwparserfromhell.parse("foo {{ charname | Berlo Hunt }} bar {{charname|Nemeth Hunt|nick=1}} baz {{charnick|Nemeth Hunt}}"))
assert test_result == "foo Berlo Hunt bar Nemmy baz Nemmy", test_result

def capitalize_first_letter(string):
    return string[0].upper() + string[1:]

def replace_genderized_keywords(string):
    """
    replace {{ he-she | Character Name }}
    with a genderized keyword html span
    """
    def keyword_callback(macro, args):
        try:
            keyword, capitalized = keyword_from_name(macro)
        except:
            logger.warning(f"Failed Keyword Search: {macro}|{args}")
            return None
        if keyword is None:
            logger.warning(f"Failed Keyword Search: {macro}|{args}")
            return None
        # Try to get the character
        assert len(args) == 1
        name = args[0].strip()
        # capitalized name; "Nemeth Hunt", or "Liza ZaHunt"
        name = " ".join([capitalize_first_letter(word) for word in name.split(" ")])

        if name in POSSESSION_MAP:
            import pdb; pdb.set_trace()
            _, gender = POSSESSION_MAP[name]
            # For ascended genders, use static genders
            content = keyword.render(gender)
            if capitalized:
                content = content.capitalize()
            node = newGenderStaticNode(content)
        else:
            character = character_from_name(name)
            if character is None:
                logger.warning(f"Failed Character Search: {macro}|{name}")
                return None
            node = newGenderSwitchNodeGeneric(keyword, character, character.gender(), capitalize=capitalized)
        new_markup = node.raw()
        return new_markup
    macro_regex = r"[^\}^\{^\|]*-[^\}^\{^\|]*"
    string = macro_hit_replace(macro_regex, string, keyword_callback)
    return string
test_result = replace_genderized_keywords(mwparserfromhell.parse("foo {{ he-she | Berlo Hunt }} bar {{aunt-uncle|Nemeth Hunt}} baz {{him-her|Nemeth Hunt}}"))
assert re.match(r"foo <span [^\>]*>he<span [^\>]*>she</span></span> bar <span [^\>]*>aunt<span [^\>]*>uncle</span></span> baz <span [^\>]*>her<span [^\>]*>him</span></span>", str(test_result)), test_result

STATS = {"age": "Age", "CR": "Combat Rating", "patron": "Patron Ascended", "MS": "Magic Skill", "MP": "Magic Power"}
def character_stats_check(string, sheet_name):
    """
    If the sheet is a main character sheet, check the stats on the sheet against the database
    """
    character = character_from_name(sheet_name)
    def callback_check_stat(db_stat_name, forkbomb_tag_args):
        if character is None:
            logger.warning(f"Stat on non-existent character: {db_stat_name}")
            return None
        if len(forkbomb_tag_args) > 1:
            assert len(forkbomb_tag_args)==2 and forkbomb_tag_args[1] == "show=1", f"Stat tag had too many args: {forkbomb_tag_args}"
        forkbomb_v2_value = forkbomb_tag_args[0].strip()
        db_value = character.get_stat(db_stat_name).strip()
        if db_value == "":
            character.set_stat(db_stat_name, forkbomb_v2_value)
            return ""
        elif forkbomb_v2_value != db_value:
            logger.warning(f"Stat mismatch: {db_stat_name} {forkbomb_v2_value} != {db_value}")
            return None
        return ""

    for tag, db_stat in STATS.items():
        string = macro_hit_replace(tag, string, lambda macro, args: callback_check_stat(db_stat, args))

    return string

def character_stats_show(string, sheet_name):
    """
    {{#show: Hajdu Rozzu | ?MP}}
    """
    def callback_show_stat(macro, args):
        # Note the  macro includes the name, not the args
        assert len(args) == 1
        character_name = macro.split(":")[1].strip()
        if character_name == "":
            character_name = sheet_name
        stat_name = args[0].strip()
        assert stat_name.startswith("?")
        stat_name = stat_name[1:]
        if stat_name in STATS:
            db_stat_name = STATS[stat_name]
            character = character_from_name(character_name)
            if character is None:
                logger.warning(f"Stat show on non-existent character: {character_name}")
                return None
            stat_value = character.get_stat(db_stat_name)
            return stat_value
        fb_name = standardize_name(character_name)
        if fb_name in forkbomb_sheets and stat_name in forkbomb_sheets[fb_name]:
            return forkbomb_sheets[fb_name][stat_name]
        logger.warning(f"Stat show on non-existent stat: {character_name} {stat_name}")
        return None

    string = macro_hit_replace(r"\#show:(^\})*", string, callback_show_stat)
    return string

test_result = character_stats_show(mwparserfromhell.parse("foo {{#show: Hajdu Rozzu | ?MP}} bar"), "")
assert test_result == "foo 9 bar", test_result

def resolve_ifeq(string):
    """
    {{#ifeq: thing1 | thing2 | yes | no}}
    """
    def callback_ifeq(macro, args):
        assert len(args) == 3
        first_arg = macro.split(":")[1].strip()
        if args[0] == first_arg:
            return args[1]
        else:
            return args[2]
    string = macro_hit_replace(r"\#ifeq:(^\{)*", string, callback_ifeq)
    return string
test_result = resolve_ifeq(mwparserfromhell.parse("foo {{#ifeq: thing1 | thing2 | yes | no}} bar"))
assert test_result == "foo no bar", test_result
test_result = resolve_ifeq(mwparserfromhell.parse("foo {{#ifeq: thing1 | thing1 | yes | no}} bar"))
assert test_result == "foo yes bar", test_result
test_result = resolve_ifeq(mwparserfromhell.parse("foo {{#ifeq: | thing1 | yes | no}}"))
assert test_result == "foo no", test_result

def check_has_greensheets(string, sheet_name: str):
    character = character_from_name(sheet_name)
    if character is not None:
        sheets = set(s.name.render() for s in character.sheets.all())
    def has_greensheet_callback(macro, args):
        if character is None:
            logger.warning(f"Sheet check on non-existent character: {sheet_name}")
            return None
        assert len(args) == 1
        greensheet_page_name = resolve_arg_name_to_sheet(args[0])
        try:
            greensheet_data = forkbomb_sheets[greensheet_page_name]
        except KeyError:
            logger.warning(f"Failed to find sheet {greensheet_page_name} for {sheet_name}")
            return None
        greensheet_name = greensheet_data["title"]
        if greensheet_name not in sheets:
            logger.warning(f"Sheet '{greensheet_name}' not found on character {sheet_name}; has {sheets}")
        return greensheet_name
    string = macro_hit_replace("has greensheet", string, has_greensheet_callback)
    string = macro_hit_replace("has document", string, has_greensheet_callback)
    string = macro_hit_replace("has yellowsheet", string, has_greensheet_callback)
    string = macro_hit_replace("has whitesheet", string, has_greensheet_callback)

    return string

def resolve_var_owner_macro(string):
    """
    replace {{{{#var: owner}}
    with the content of {{owner | foo}}
    """
    owner = ""
    def owner_callback(macro, args):
        assert len(args) == 1
        nonlocal owner
        owner = args[0].strip()
        return f""
    string = macro_hit_replace("owner", string, owner_callback)
    def callback_var_owner(macro, args):
        assert len(args) == 0
        return owner
    string = macro_hit_replace("#var:\s*owner", string, callback_var_owner)
    return string

def resolve_you_macro(string, sheet_name: str):
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

def resolve_date1276_macro(string):
    """
    replace {{ date1276 | date }}
    with date + 6 days
    This was customizeable in the old forkbomb, but I don't think it's worth it
    """
    def try_parsing_date(text):
        for fmt in ("%B %d", "%B %d %Y"):
            try:
                return datetime.datetime.strptime(text, fmt)
            except ValueError:
                pass
        raise ValueError('no valid date format found')
    def callback_date1276(macro, args):
        assert len(args) == 1
        original_date = args[0].strip()  # e.g. 'April 13' or 'April 13 1276'
        date = try_parsing_date(original_date)
        date += datetime.timedelta(days=6)
        new_date = date.strftime("%B %d")
        return new_date
    string = macro_hit_replace("date1276", string, callback_date1276)
    return string

def resolve_ifcastle_macro(string):
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

def resolve_ifiam_macro(string, sheet_name: str):
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
            # Apparently sometimes we are dumb and put extra blank args at the end. That's ok.
            if all(arg.strip() == "" for arg in args[3:]):
                name, yes, no = args[:3]
            else:
                raise ValueError(f"ifiam macro had wrong number of args: {args}")
        if standardize_name(name) == sheet_name:
            return yes
        else:
            return no

    string = macro_hit_replace("ifiam", string, callback_ifiam)
    string = macro_hit_replace("said", string, lambda _, charname: callback_ifiam(None, args=[charname[0], "you said", f"said {{{{charnick|{charname[0]}}}}}"]))
    return string
test_result = resolve_ifiam_macro(mwparserfromhell.parse("{{ifiam|Bob|yes|no}}"), "bob")
assert test_result == "yes", test_result
test_result = resolve_ifiam_macro(mwparserfromhell.parse("{{ifiam|Bob|yes|no}}"), "alice")
assert test_result == "no", test_result
test_result = resolve_ifiam_macro(mwparserfromhell.parse("{{said | Bob}}"), "bob")
assert test_result == "you said", test_result
test_result = resolve_ifiam_macro(mwparserfromhell.parse("{{said | Bob}}"), "Alice")
assert test_result == "said {{charnick|Bob}}", test_result

def resolve_ooc_macro(string):
    """
    replace {{ OOC | <text> }}
    """
    def callback_ooc(macro, args):
        assert len(args) == 1, args
        return inlineAsideHTML(content=args[0])
    string = macro_hit_replace("OOC", string, callback_ooc)
    return string

def resolve_commentout_macro(string):
    """
    replace {{ CommentOut | <summary> | <text> }}
    """
    def callback_commentout(macro, args):
        if len(args) == 2:
            visible_text, hover_text = args
        elif len(args) == 1:
            logger.warning(f"CommentOut macro had only one arg, something may be wrong: {args[0][:100]}")
            visible_text = ""
            hover_text = args[0]
        else:
            import pdb; pdb.set_trace()
        return WritersNode.new_html(type="hidden", visible_text=visible_text, hover_text=hover_text, hover_title="CommentOut (Imported wiki macro)")
    string = macro_hit_replace("CommentOut", string, callback_commentout)
    return string

def resolve_stnote_macro(string):
    """
    replace {{ STNote | <text> }}
    """
    def callback_stnote(macro, args):
        if len(args) > 1:
            logger.warning(f"STNote macro had too many args: {args}")
        result = WritersNode.new_html(type="stnote", visible_text="", hover_text=args[0], hover_title="STNote (Imported wiki macro)")
        return result
    string = macro_hit_replace("STnote", string, callback_stnote)
    return string
test_result = resolve_stnote_macro(mwparserfromhell.parse("foo{{ STnote | This is a test }} bar"))
assert """ data-larp-action="stnote" """ in test_result, test_result

def resolve_todo_macro(string):
    """
    replace {{ ToDo | <text> }}
    """
    def callback_stnote(macro, args):
        if len(args) > 1:
            logger.warning(f"ToDo macro had too many args: {args}")
        return WritersNode.new_html(type="todo", visible_text="", hover_text=args[0], hover_title="ToDo (Imported wiki macro)")
    string = macro_hit_replace("ToDo", string, callback_stnote)
    return string

def resolve_g_macros(string):
    """
    {{g | character | m-version | f-version}}
    """
    def callback_g(macro, args):
        if len(args) == 3:
            charname, m_version, f_version = args
        else:
            raise ValueError(f"g macro had wrong number of args: {args}")
        character = character_from_name(charname)
        return newComplexGenderSwitchNodeHTML(character=character, m_version=m_version, f_version=f_version)
    string = macro_hit_replace("g", string, callback_g)
    return string

def clear_hide_unhide(string):
    # regex should match "{{hide  }} <br> <br><br> {{unhide}}" with arbitrary whitespace and any number of br tags
    string = re.sub(r"{{\s*hide\s*}}\s*(<br\s*/?>\s*)*{{\s*unhide\s*}}", "", string, flags=re.IGNORECASE)
    return string

def non_macro_cleanup(string):
    string = string.replace("__NOTOC__", "")
    if re.match(r"\s*<strong>Age:</strong>", string):
        string = re.sub(r"\s*<strong>Age:</strong>", "", string)
    return string

def all_processing(data: str, fb_sheet_name:str) -> str:
    braces_count = data.count("{{")
    logger.info(f"  Found {braces_count} templates in {fb_sheet_name}")

    data = mwparserfromhell.parse(data)
    data = resolve_you_macro(data, fb_sheet_name)
    data = replace_genderized_keywords(data)
    data = character_stats_check(data, fb_sheet_name)
    data = character_stats_show(data, fb_sheet_name)
    data = check_has_greensheets(data, fb_sheet_name)
    data = resolve_var_owner_macro(data)
    data = resolve_ifeq(data)
    data = clear_unused_tags(data)
    data = resolve_pagebreak_macro(data)
    data = resolve_chapter_macro(data)
    data = resolve_charname_and_charnicks(data)
    data = resolve_ifcastle_macro(data)
    data = resolve_date1276_macro(data)
    data = resolve_ifiam_macro(data, fb_sheet_name)
    data = resolve_ooc_macro(data)
    data = resolve_commentout_macro(data)
    data = resolve_stnote_macro(data)
    data = resolve_todo_macro(data)
    data = resolve_g_macros(data)
    data = str(data)
    data = clear_hide_unhide(data)
    data = non_macro_cleanup(data)
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
    remaining_templates = re.findall(r"\{\{([^\}\|]*)", data)
    remaining_templates = [t.strip() for t in remaining_templates]
    remaining_template_counts = Counter(remaining_templates)
    # reminaing_templates_str = "".join([f"\n  {t}:{n}" for t, n in remaining_template_counts.items()])
    # logger.info(f"""Remaining templates: {reminaing_templates_str}""")

    garhdony_sheet.content_type = 'html'
    garhdony_sheet.save()
    
    new_revision = SheetRevision(sheet=garhdony_sheet, content=LARPstring(data))
    new_revision.save()

    return remaining_template_counts

# Main function
# Get sheet name from args
def main():
    parser = argparse.ArgumentParser(description='Import a sheet from the wiki.')
    parser.add_argument('--sheet_name', metavar='sheet_name', type=str, help='The name of the sheet to import')
    parser.add_argument('--max_sheets', metavar='sheet_name', type=int, help='max sheets', required=False)

    args = parser.parse_args()
    
    sheet_name = standardize_name(args.sheet_name)
    if sheet_name == "all":
        BLACKLIST = []#["benkai_garmani", "dogmas_magic_hunts", "dogmas_magic_temesvar"]
        target_sheets = {k: v for k, v in sheets_mapping_f2g.items() if "magic_sheet" not in k and k not in BLACKLIST}
    else:
        target_sheets = {sheet_name: sheets_mapping_f2g[sheet_name]}

    unresolved_templates = {}
    for fb_name, gh_sheet in sorted(list(target_sheets.items()))[:args.max_sheets]:
        logger.info(f"\n\n======================\nImporting sheet {fb_name} to {gh_sheet}\n======================")
        unresolved_templates[fb_name] = import_forkbomb_v2_sheet(fb_name, gh_sheet)
    # collapse the unresolved templates counters
    total_unresolved_templates = Counter()
    for fb_name, templates in unresolved_templates.items():
        total_unresolved_templates += templates
    grand_total = sum(total_unresolved_templates.values())
    result_string = f"Unresolved templates ({grand_total}):"
    for template, count in sorted(total_unresolved_templates.items(), key=lambda x: x[1], reverse=True):
        sample_sheets = [k for k, v in unresolved_templates.items() if template in v.keys()]
        sample_sheets_str = ", ".join(sample_sheets[:3]) + (f", ..."  if len(sample_sheets) > 3 else "")
        result_string += f"\n  {template}: {count} - [{sample_sheets_str}]"
    logger.info(result_string)
    if sheet_name == "all":
        with open("unresolved_templates.txt", "w") as f:
            f.write(result_string)

    
if __name__ == "__main__":
    main()