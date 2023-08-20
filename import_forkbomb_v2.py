import argparse
from collections import Counter, defaultdict
import csv
import datetime
import django
from django.core.files import File
from functools import lru_cache
import html5lib
import mwparserfromhell
import os
import re
from typing import Callable, Dict, List, Tuple

from import_forkbomb_preprocess_images import unpack

# setup stuff so django is happy
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from garhdony_app.LARPStrings import LARPstring
from garhdony_app.models import GenderizedKeyword, GenderizedName, Character, Sheet, GameInstance, SheetRevision, NonPlayerCharacter, PlayerCharacter, EmbeddedImage
from garhdony_app.span_parser import WritersBubbleInnerNode, WritersNode, inlineAsideHTML, newComplexGenderSwitchNodeHTML, newGenderStaticNode, newGenderSwitchNode, newGenderSwitchNodeGeneric


import logging
# Logging config that prints to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='%(message)s')
logging.getLogger("garhdony_app.LARPStrings").setLevel(logging.INFO)
logging.getLogger("garhdony_app.span_parser").setLevel(logging.INFO)
logging.getLogger("garhdony_app.models").setLevel(logging.INFO)
# django.db.backends
logging.getLogger('django.db.backends').setLevel(logging.ERROR)


def surroundings(string, snippet, width=100):
    """ return the 20 characters before and after the snippet """
    index = string.find(snippet)
    if index == -1:
        return None
    return string[index-width:index+width]

GAME_NAME = "DogmasRevival"
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
            logger.info(f"Already created { m } { f } { l }")
        else:
            name = GenderizedName(male=m, female=f)
            new_char = PlayerCharacter(first_name_obj=name, last_name=l, default_gender=g, game=game, username=u)
            new_char.save()
            logger.warning(f"Created { m } { f } { l }")
        char = PlayerCharacter.objects.get(game=game, last_name=l, first_name_obj__male=m, first_name_obj__female=f)

        char_sheet = Sheet.objects.get(game=game, filename=char.name())
        char.sheets.add(char_sheet)
        char.save()

    for m, f, l, g in [
        ("Pahl", "Pahla", "Harsanyi", "F"),
        ("Finlo", "????", "Hunt", "M"),
        ("Mahdzo", "????", "Hunt", "M"),
        ("????", "Minka", "Hunt", "F"),
        ("Gyorgy", "????", "Zahunt", "M"),
        ("????", "Iren", "Varga", "F"),
        ("Kuhlmer", "????", "Valzant", "M"),
    ]:
        if NonPlayerCharacter.objects.filter(game=game, last_name=l, first_name_obj__male=m, first_name_obj__female=f).exists():
            logger.info(f"Already created { m } { f } { l }")
        else:
            name = GenderizedName(male=m, female=f)
            new_char = NonPlayerCharacter(first_name_obj=name, last_name=l, gender_field=g, game=game)
            new_char.save()
            logger.warning(f"Created { m } { f } { l }")
    kuhlmer = NonPlayerCharacter.objects.get(game=game, last_name="Valzant")
    kuhlmer.title_obj = GenderizedKeyword.objects.get(male="Sir")
    kuhlmer.save()

    
    gizella = PlayerCharacter.objects.get(game=game, last_name="Tzonka", first_name_obj__female="Gizella")
    history_of_tzonka = Sheet.objects.get(game=game, filename="History of Tzonka")
    gizella.sheets.add(history_of_tzonka)
    gizella.save()

    venz = PlayerCharacter.objects.get(game=game, last_name="Hajnal", first_name_obj__male="Venz")
    wriitngs = Sheet.objects.get(game=game, filename="Writings of Sir Retel Verhdas")
    venz.sheets.add(wriitngs)
    venz.save()


    for filename, new_display_name in {
        "Magic (Hunts)": "Magic",
        "Magic (Temesvar)": "Magic",
        "Magar Possession (non-hell)": "Magar Possession",
        "How to Summon Demons": "Notes about Boring Things",
        "Priesthood Leadership (Matya)": "Priesthood Leadership",
        "Kazka Hunts": "Rangers' Reports",
        "Hunt Manor Map": "Map of Hunt Manor",
        "Hunt Wood Map Public": "Hunt Wood Map",
        "Hunt Manor Map (Timea)": "Map of Hunt Manor",
        "Orrun Ambrus": "Orrun Ambrus III",
        "Imre Tzonka": "Imre Tzonka IX",
        "Order of Almos (Hunts)": "Order of Almos",
    }.items():
        sheet = Sheet.objects.get(game=game, filename=filename)
        sheet.name = LARPstring(new_display_name)
        sheet.save()

database_cleanup()

def dedent(string):
    return "\n".join([line.strip() for line in string.split("\n")])

forkbomb_v2_csv_path = "data/forkbomb_with_namespace.csv"
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
        forkbomb_v2_csv = {standardize_name(row[1]): row[3] for row in reader}

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
    string = re.sub(r"</p>\s*<p>", "<br><br>\n\n", string)
    string = re.sub(r"<p>", "", string)
    string = re.sub(r"</p>", "", string)
    return string

def cleanup_code_tags(string: str) -> str:
    """
    The parser often puts things like this:
    <code>&nbsp;&nbsp;This&nbsp;was&nbsp;indented&nbsp;with&nbsp;spaces&nbsp;but&nbsp;the&nbsp;parser&nbsp;doesn't&nbsp;like&nbsp;that</code><br />
    We want to return it to:
        This was indented with spaces but the parser doesn't like that
    Ideally without removing any other nbsp's that aren't inside a <code> offender
    """
    blocks = re.findall(r"<code>.*?</code>(?:<br />)?", string, re.DOTALL)
    for block in blocks:
        sane_block = block.replace("\xa0", " ").replace("<code>", "").replace("</code>", "")
        string = string.replace(block, sane_block)
    string = string.replace("<br />", "")
    return string


TABLE_CLASS_MAPPING = {
    'text-align: left;': None,
    'text-align: center; width: 85%;': 'runelist',
}
def table_style_to_class(attrs_str) -> str:
    """
    attrs is e.g. 
        style="background-color: #ffffff; border-style: none; text-align: center; width:85%;" cellpadding="5" class="wikitable"
    """
    attrs_dict = {}  # e.g. 'style': "...", 'class': "wikitable", 'cellpadding': "5"
    #we later have to process the style attr string further
    for match in re.findall(r"(\w+)=\"(.*?)\"", attrs_str):
        attrs_dict[match[0]] = match[1]
    # wikitable class doesn't exist anymore
    if 'class' in attrs_dict:
        if attrs_dict['class'] == "wikitable":
            attrs_dict.pop('class', None)
        else:
            logger.warning(f"Unknown table class {attrs_dict['class']}")
    # cell padding is always 5, and doesn't do anything.
    if 'cellpadding' in attrs_dict:
        attrs_dict.pop('cellpadding', None)
    # Only key left should be style (or nothing)
    if len(attrs_dict) > 1 or (len(attrs_dict) == 1 and 'style' not in attrs_dict):
        logger.warning(f"Unknown table attributes {attrs_dict}")
    # Now we need to process the style attr string
    style_dict = {}
    if 'style' in attrs_dict:
        for match in re.findall(r"(\S*?)\s*:\s*(.*?)\s*;", attrs_dict['style']):
            style_dict[match[0]] = match[1]
    # Clear out things that are explicitly re-set to default
    if 'background-color' in style_dict and style_dict['background-color'] in {"#ffffff", "#ffffee"}:  # Remove this random yellow background
        style_dict.pop('background-color')
    if 'color' in style_dict and style_dict['color'] == "black":
        style_dict.pop('color')
    if 'border-style' in style_dict and style_dict['border-style'] == "none":
        style_dict.pop('border-style')
        style_dict.pop('border-width', None)

    # Now we need to convert the style dict back to a canonical string
    style_str = " ".join([f"{key}: {value};" for key, value in sorted(style_dict.items())])
    attrs_dict['style'] = style_str
    # Now we need to convert the attrs dict back to a canonical string
    if style_str in TABLE_CLASS_MAPPING:
        cls = TABLE_CLASS_MAPPING[style_str]
        attrs_dict.pop('style', None)
        if cls is not None:
            attrs_dict['class'] = cls
    else:
        logger.warning(f"Unmapped table style {style_str}")
    output_attrs_str = " ".join([f'{key}="{value}"' for key, value in sorted(attrs_dict.items())])
    return output_attrs_str

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
    
    starting_templates = re.findall(r"{{.*?}}", string)

    #  pandoc ignores attributes on tables, so we need to remember them and re-add them later
    table_attributes = re.findall(r"\{\|.*\n", string)
    # Strip off the {| and \n
    table_attributes = [attr[2:-1] for attr in table_attributes]
    convert_safe_string = pypandoc.convert_text(string, "html", format="mediawiki", extra_args=["--wrap=none", "--no-highlight"])
    clean_output_string = cleanup_ps(convert_safe_string).strip()
    clean_output_string = cleanup_code_tags(clean_output_string)
    if table_attributes:
        # Now put back the table attributes
        # making sure the first goes on the first table, next on the second table, etc.
        table_attributes = [table_style_to_class(l) for l in table_attributes]
        if len(table_attributes) != clean_output_string.count("<table>"):
            logger.error(f"""Table attributes len {len(table_attributes)} not {clean_output_string.count("<table>")}: {table_attributes}""")
            import pdb; pdb.set_trace()
        splt = clean_output_string.split("<table>")
        tags = [f"<table {table_attribute}>" for table_attribute in table_attributes]
        clean_output_string = splt[0] + "".join([tag + splt[i+1] for i, tag in enumerate(tags)])
    assert '<code>' not in clean_output_string, clean_output_string
    remaining_templates = re.findall(r"{{.*?}}", clean_output_string)
    swallowed_templates = set(starting_templates) - set(remaining_templates)
    if swallowed_templates:
        logger.warning(f"Swallowed templates: {swallowed_templates}")
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
assert "\r\n" not in test_result, test_result
thing_with_newlines = """
    foo
    bar
    baz
    
    bop"""
test_result = mediawiki_to_html(thing_with_newlines)


# table = """
# <table><tbody>
# <tr><th>hover</th></tr>
# </tbody></table>"""
# # stnote_block = "<pre>" + stnote_block + "</pre>"
# test_result = mediawiki_to_html(table)
# assert test_result == table, f"{test_result}\n\n!=\n\n{table}"

# stnote_block = dedent(WritersNode.new_html(type="stnote", visible_text="vis", hover_title="hover", hover_text="hover"))
# # stnote_block = "<pre>" + stnote_block + "</pre>"
# test_result = mediawiki_to_html(stnote_block)
# assert test_result == stnote_block, f"{test_result}\n\n!=\n\n{stnote_block}"


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

def escape_spells(string: str) -> str:
    """
    Replace <T: ... > with &lt;T: ... &gt;
    """
    return re.sub(r"<([TtDdRr]):([^>]*)>", r"&lt;\1:\2&gt;", string)
test_result = escape_spells("(heal / <D:infinity> / <T:H> / <T:B> / <T:N> /<T:I> /<T:blood> / (heal / <T:blood>x3))")
assert test_result == "(heal / &lt;D:infinity&gt; / &lt;T:H&gt; / &lt;T:B&gt; / &lt;T:N&gt; /&lt;T:I&gt; /&lt;T:blood&gt; / (heal / &lt;T:blood&gt;x3))", test_result

def pre_html_manual_fixes(string, sheet_name):
    TYPOS = {
        "{{charname | Matya Varadi}}": "{{charname | Matyas Varadi}}",  # gizella tzonka
        "{{charnick|Antal}}": "{{charnick|Antal Yenis}}",   # 
        "{{charname|Aleksander ZaHunt|alias=1|aliasnick=1}}": "{{charname|Aleksander ZaHunt|nick=1}}",   # some hunts
        """{{g|Ramestor Rihul|princes and princesses|prince and princesses}}""": """{{g|Ramehstor Rihul|princes and princesses|prince and princesses}}""", # Matyas
        "{{#show: Artifact of Zag | ?title}}": "Plates of Zag",  # Venz hajnal
        "{{has document | Spellbook}}": "{{has item | Spellbook}}",  # Adorran salom
        "{{has document | Writ of Safe Passage}}": "{{has item | Writ of Safe Passage}}",  # Orrun Ambrus
        "{{has greensheet | Kazkan Greensheet}}": "{{has greensheet | Recent History of Kazka}}",  # Many Kazkans
        "{{has greensheet | Tzonkan Greensheet}}": "{{has greensheet | Recent History of Tzonka}}",  # Tiborc
        "{{ has greensheet | Ambran Greensheet}}": "{{has greensheet | Recent History of Ambrus}}",  # Katalin
        "Wound <name>": "Wound &lt;name&gt;",  # st guide
        "Wound <target\'s name>": "Wound &lt;target\'s name&gt;",  # magic hunts
        "Daze <target\'s name>": "Daze &lt;target\'s name&gt;",  # magic
        """{{hide}}\n{{has ability | Signatory for Rihul}}\n{{unhide}}""": "{{has ability | Signatory for Rihul}}",  # Rammy
        "Matya doesn't get the following section: [[Council of Eminents (Matyas Varadi)]]": "Matya doesn't get the following section",  # council of eminents; the link confuses us
        "\n\n&#149; ": "\n* ",  # bullet points
    }
    for typo, fix in TYPOS.items():
        string = string.replace(typo, fix)
    if sheet_name in {"hajdu_rozzu", "patrik_zahunt"}:
        string = re.sub(r"\{\{has greensheet \| Recent History of Kazka\s*\}\}", "\{\{has greensheet \| Recent History of Kazka Hunts\}\}", string)
    return string

@lru_cache(maxsize=1000)
def get_expanded_content(sheet_name):
    """
    Get the content of a sheet, with all the includes resolved
    """
    content = page_content(sheet_name)
    content = recursively_include_pages(content)

    content = escape_spells(content)

    content = pre_html_manual_fixes(content, sheet_name)
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
        except (KeyError, RecursionError):
            if sheet_name not in {"event", "all_colored_sheet_copies", "earth_defense_force_insignia"}:
                logger.warning(f"Failed to get content for {sheet_name}")
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
    'lorink_toggle_x', 'rihulian_economy', 'janna_kohvari_run2', 'vargan_economic_notes', 
    # these aren't obsolete but they are interior templates
    'herbology', 'dogmas_magic_cheat_sheet', 
    }
OK_UNMAPPED_GARHDONY = {
    # Produced outside forkbomb
    'ambran_economic_notes', 'kazkan_economic_notes', 'tzonkan_economic_notes', 'temesvar_economic_plans', 'cathedral_of_kelemen_construction_plans', 'cathedral_of_sandor_construction_plans', 'church_maintenance_plans', "spider's_notes",\
    'teaser_story', 'vargan_teaser_story', 'the_rules_of_tzikka',
    'old_map_of_hunt_wood',
    }
DONT_MIGRATE = {
    # pdfs, pngs, etc
    'garhdony_map', 'hunt_manor_map_hunts', 'hunt_manor_map_timea', 'hunt_wood_map', 'hunt_wood_map_hunts', 'runebook'
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

    # Possibly bad titles
    'recent_history_of_kazka_hunts': 'kazka_hunts',
    'opening_the_gate': 'opening_the_gate_of_the_gods',
    'runebook': 'standard_temesvar_runebook',
    'hunt_manor_map_hunts': 'hunt_manor_map',
    'hunt_wood_map': 'hunt_wood_map_public',
    'hunt_wood_map_hunts': 'hunt_wood_map',
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

# Check all the dont_migrates names are typed right
for fb_name in DONT_MIGRATE:
    assert fb_name in sheets_mapping_f2g, f"Missing sheet {fb_name}"

for fb, gh in sheets_mapping_f2g.items():
    if fb not in forkbomb_sheets:
        logger.warning(f"Missing sheet metadata {fb}")
        continue
    fb_name = forkbomb_sheets[fb].get('title', forkbomb_sheets[fb].get('name', None))
    if fb_name != gh.name.render():
        # logger.warning(f"Title mismatch: {fb} ({fb_name}) vs {gh.name.render()}")
        pass

NEW_CHARACTERS = ["Rikhard Kohvari", "Sammi Ehroz", "Timea Hunt", "Katalin Aller", "Domnika Zhell"]

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
            logger.info(f"Got {gh_sheet.characters.count()} characters for {name}")
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
    hits_replaced = set()
    for template in wikicode.filter_templates():
        template_str = str(template)
        if template_str in hits_replaced:
            # We've already replaced this earlier in the loop
            continue
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
                    wikicode.replace(template_str, replacement)
                    hits_replaced.add(template_str)
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
        if len(forkbomb_tag_args) > 1:
            assert len(forkbomb_tag_args)==2 and forkbomb_tag_args[1] == "show=1", f"Stat tag had too many args: {forkbomb_tag_args}"
        forkbomb_v2_value = forkbomb_tag_args[0].strip()
        if db_stat_name == "Age" and forkbomb_v2_value == "1281":
            # ignore magari ages
            return ""
        if character is None:
            logger.warning(f"Stat on non-existent character: {db_stat_name}")
            return None
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

# test_result = character_stats_show(mwparserfromhell.parse("foo {{#show: Hajdu Rozzu | ?MP}} bar"), "")
# assert test_result == "foo 9 bar", test_result

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
        new = (character.name() in NEW_CHARACTERS)
    def has_greensheet_callback(macro, args):
        if character is None:
            logger.warning(f"Sheet check on non-existent character: {sheet_name}")
            return None
        assert len(args) == 1
        greensheet_page_name = resolve_arg_name_to_sheet(args[0])
        try:
            gh_sheet = sheets_mapping_f2g[greensheet_page_name]
        except KeyError:
            logger.warning(f"Failed to find sheet {greensheet_page_name} for {sheet_name}")
            return None
        gh_name = gh_sheet.name.render()
        if gh_name not in sheets and not new:
            if gh_name == 'Writings of Sir Retel Verhdas' and sheet_name == 'tiborc_kertehsz':
                # special case, here I think it's fine not to have it,
                return ""            
            logger.warning(f"Sheet '{gh_name}' not found on character {sheet_name}; has {sheets}")
            return None
        if new:
            logger.info(f"Adding sheet '{gh_name}' to new character {sheet_name}")
            character.sheets.add(gh_sheet)
        return f"* {gh_name}"
    string = macro_hit_replace("has (greensheet|document|yellowsheet|whitesheet|appendix)", string, has_greensheet_callback)
    return string

def resolve_has_item_macro(string):
    """
    {{ has_item | item name}}
    """
    def callback_has_item(macro, args):
        assert len(args) == 1
        item_name = resolve_arg_name_to_sheet(args[0])
        item_sheet_content = get_expanded_content(item_name)
        titles = re.findall(r"\|\s*title\s*=\s*([^\|\{\}]*)", item_sheet_content)
        if len(titles) == 0:
            title = item_name.replace("_", " ").title()
        elif len(titles) > 1:
            logger.warning(f"Item has multiple titles: {item_name}")
            return None
        else:
            title = titles[0].strip()
        return f"* {title}"
    string = macro_hit_replace("has item", string, callback_has_item)
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

abilities_map = defaultdict(set)
def resolve_ability_macro(string, sheet_name: str):
    """
    {{ ability | <ability name> }}
    collate who has which abilities, but for now just leave the text
    """
    def callback_ability(macro, args):
        assert len(args) == 1
        ability_name = resolve_arg_name_to_sheet(args[0])
        abilities_map[ability_name].add(sheet_name)
        ability_content = get_expanded_content(ability_name)
        parse = mwparserfromhell.parse(ability_content)
        title = None
        card_text = None
        for template in parse.filter_templates():
            if template.name.matches("ability info"):
                try:
                    title = template.get("title").value
                except ValueError:
                    title = ability_name.replace("_", " ").title()
                continue
            if template.name.matches("card text"):
                assert len(template.params) == 1
                card_text = template.params[0].value
        html = f"<div class='ability'><h3>{title}</h3>{card_text}</div>"
        return html
        
    string = macro_hit_replace("has ability", string, callback_ability)
    return string

all_files = set()
def find_bracket_problems(string):
    for match in re.findall(r"\[\[\s*([^\]]*)\]\]", string):
        # We know about File, so ignore those
        if match.startswith("File:"):
            all_files.add(match[5:])
            continue
        if match in {"Artifact of Kohsar", "Artifact of Orahun", "Artifact of Zag", "Katalin Aller"}:
            # These are silly links, remove their linkageness
            string = string.replace(f"[[{match}]]", match)
            continue
        if match in {"Adorra Update", "Berlo Update", "Isti Update"}:
            # This is just empty, remove it entirely
            string = string.replace(f"[[{match}]]", "")
            continue
        if match in {"Keepers' Evidence (Lorink)", "Opening the Gate (Lorink)"}:
            # This is in an stnote where it kind of could be a link; just leave it as a broken link
            continue
        location = string.find(match)
        print(f"Found bracket problem: {match} at {location}:")
        print(string[location-100:location+100])
        import pdb; pdb.set_trace()
    return string

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
        return dedent(WritersNode.new_html(type="hidden", visible_text=visible_text, hover_text=hover_text, hover_title="CommentOut (Imported wiki macro)"))
    string = macro_hit_replace("CommentOut", string, callback_commentout)
    return string

def resolve_stnote_macro(string):
    """
    replace {{ STNote | <text> }}
    """
    def callback_stnote(macro, args):
        if len(args) == 1:
            arg = args[0]
        else:
            logger.warning(f"STNote macro had too many args: {args}")
            arg = " | ".join(args)
        result = dedent(WritersNode.new_html(type="stnote", visible_text="", hover_text=arg, hover_title="STNote (Imported wiki macro)"))
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
        if len(args) == 1:
            arg = args[0]
        else:
            logger.warning(f"ToDo macro had too many args: {args}")
            arg = " | ".join(args)
        result = dedent(WritersNode.new_html(type="todo", visible_text="", hover_text=arg, hover_title="ToDo (Imported wiki macro)"))
        return result
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
        result = newComplexGenderSwitchNodeHTML(character=character, m_version=m_version, f_version=f_version)
        return result
    string = macro_hit_replace("g", string, callback_g)
    return string

def clear_embedded_images(game):
    EmbeddedImage.objects.filter(game=game).delete()
# clear_embedded_images(game)

def resolve_embedded_images(data):
    """ 
    data is a wikicode object
    We need to process all the [[File:filename]] snippets
    """
    assert data is not None
    for template in data.filter_wikilinks():
        splt = template.title.split(":", maxsplit=1)
        if len(splt) == 1:
            continue
        namespace, filename = splt
        filename = filename.strip().replace(" ", "_").capitalize()
        if namespace != "File":
            continue
        style = {}
        if template.text:
            for opt in template.text.split("|"):
                p = opt.strip()
                if p.endswith("px"):
                    w = int(p[:-2])
                    style["width"] = p
                else:
                    import pdb; pdb.set_trace()
        style_string = "; ".join(f'{k}: {v}' for k, v in style.items())
        # See if we already have the file
        try:
            embedded_image = EmbeddedImage.objects.get(game=game, filename=filename)  
        except EmbeddedImage.DoesNotExist:
            # find it in data/forkbomb_images/<filename>
            # check that the file doesn't already exist:
            logger.info(f"Creating embedded image {filename}")
            if os.path.exists(os.path.join(game.sheets_directory, "embedded_images", filename)):
                print(f"File {filename} already exists in game {game.name} but is not in the database")
                import pdb; pdb.set_trace()
            try:
                file = open(f"data/forkbomb_images/{filename}", "rb")
                embedded_image = EmbeddedImage(game=game, filename=filename, file=File(file))
                embedded_image.save()
            except FileNotFoundError:
                logger.warning(f"File {filename} not found in data/forkbomb_images")

        # Replace the wikicode with an image tag
        url = embedded_image.url
        data.replace(template, f'<img data-id="{embedded_image.id}" src="{url}" style="{style_string}">')
    return data

def clear_hide_unhide(string):
    # regex should match "{{hide  }} <br> <br><br> {{unhide}}" with arbitrary whitespace and any number of br tags
    string = re.sub(r"{{\s*hide\s*}}\s*(<br\s*/?>\s*)*{{\s*unhide\s*}}", "", string, flags=re.IGNORECASE)
    return string

def non_macro_cleanup(string):
    string = string.replace("__NOTOC__", "")
    if re.match(r"\s*<strong>Age:</strong>", string):
        string = re.sub(r"\s*<strong>Age:</strong>", "", string)
    return string

def cleanup_excessive_linebreaks(string):
    """ replace any number of <br>s greater than two, with only two."""
    string = re.sub(r"<br\s*/?>\s*(<br\s*/?>\s*)+", "<br><br>\n\n", string)

    # Also remove any amount of whitespace and brs at the start of the string
    string = re.sub(r"^\s*(<br\s*/?>\s*)+", "", string)
    return string

def assert_valid_html(string, pdb=True):
    parser = html5lib.HTMLParser(strict=True)
    # Encapsulate it in the DOCTYPE stuff that html5lib expects
    wrapped_string = "<!DOCTYPE html><html><head></head><body>" + string + "</body></html>"
    try:
        parser.parse(wrapped_string)
    except Exception as e:
        if pdb:
            print(f"Failed to parse html: {string[:200]}")
            print(f"error: {e}")
            import pdb; pdb.set_trace()
        raise e
test_result = assert_valid_html("<p>foo</p>", pdb=False)
assert test_result is None, test_result
try:
    test_result = assert_valid_html("<div>foo<p>bar</div> baz </p>", pdb=False)
    raise ValueError("Should have failed")
except Exception as e:
    # Anything other than ValueError is fine
    if isinstance(e, ValueError):
        raise e
    else:
        pass

def oneshot_processing(data, fb_sheet_name:str):
    braces_count = data.count("{{")
    logger.info(f"  Found {braces_count} templates in {fb_sheet_name}")

    data = clear_unused_tags(data)
    data = resolve_ifcastle_macro(data)
    data = resolve_date1276_macro(data)
    data = resolve_var_owner_macro(data)
    data = resolve_ifeq(data)
    data = resolve_you_macro(data, fb_sheet_name)
    data = character_stats_check(data, fb_sheet_name)
    data = character_stats_show(data, fb_sheet_name)
    data = check_has_greensheets(data, fb_sheet_name)
    data = resolve_has_item_macro(data)
    data = resolve_ability_macro(data, fb_sheet_name)
    data = resolve_embedded_images(data)
    return data

def iterated_processing(data, fb_sheet_name:str):
    braces_count = data.count("{{")
    logger.info(f"  Found {braces_count} templates in {fb_sheet_name}")

    # Probbaly don't need to be iterated; could pull these out
    data = resolve_charname_and_charnicks(data)
    data = replace_genderized_keywords(data)
    data = resolve_pagebreak_macro(data)
    data = resolve_chapter_macro(data)

    # Can be nested in complicated ways; important to iterate
    data = resolve_ifiam_macro(data, fb_sheet_name)
    data = resolve_ooc_macro(data)
    data = resolve_commentout_macro(data)
    data = resolve_stnote_macro(data)
    data = resolve_todo_macro(data)
    data = resolve_g_macros(data)
    return data

def print_table(str):
    print("================================================================================================================================================")
    # need to match shortest possible string, otherwise we get all of them.
    t = re.search(r"\{\|.*?\|\}", str, flags=re.DOTALL)
    if t:
        #just the first hit
        print(t[0])

def import_forkbomb_v2(fb_sheet_name:str):
    data_str = get_expanded_content(fb_sheet_name)
    assert_valid_html(data_str)
    data = mwparserfromhell.parse(data_str)
    assert data_str == str(data)
    old_data_str = None

    data = oneshot_processing(data, fb_sheet_name)
    data_str = str(data)
    assert_valid_html(data_str)

    iter = 0
    while old_data_str != data_str:
        logger.info(f"=== Iteration {iter} ===")
        old_data_str = data_str
        data = iterated_processing(data, fb_sheet_name)
        data_str = str(data)
        assert_valid_html(data_str)
        iter += 1
    data_str = find_bracket_problems(data_str)
    data_str = clear_hide_unhide(data_str)

    data_str = mediawiki_to_html(data_str)
    data_str = cleanup_ps(data_str)

    data_str = non_macro_cleanup(data_str)
    data_str = cleanup_excessive_linebreaks(data_str)
    return data_str

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
        target_sheets = {k: v for k, v in sheets_mapping_f2g.items() if "magic_sheet" not in k and k not in DONT_MIGRATE}
    else:
        target_sheets = {sheet_name: sheets_mapping_f2g[sheet_name]}

    unpack()

    unresolved_templates = {}
    for fb_name, gh_sheet in sorted(list(target_sheets.items()))[:args.max_sheets]:
        logger.info(f"\n\n======================\n")
        logger.warning(f"===Importing sheet {fb_name} to {gh_sheet}===")
        logger.info("\n======================")
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
    print(result_string)
    if sheet_name == "all":
        with open("unresolved_templates.txt", "w") as f:
            f.write(result_string)

        # print the abilities:
        with open("abilities.txt", "w") as f:
            for ability_name, sheets in abilities_map.items():
                sheets_str = ", ".join(sheets)
                f.write(f"{ability_name}: {sheets_str}\n")

        # print files
        with open("files.txt", "w") as f:
            for file in all_files:
                f.write(f"{file}\n")
    
if __name__ == "__main__":
    main()