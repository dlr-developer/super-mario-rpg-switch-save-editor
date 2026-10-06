"""Super Mario RPG (Nintendo Switch, 2023) save editor.

Save files are UTF-16 LE JSON with no checksum. Works with saves from any
emulator (Ryujinx-style folders "0"/"1", or yuzu-style single folder) and
with saves dumped from a real Switch (e.g. with JKSV).

Item IDs/names: Echocolat/SMR-save-edit-scripts (data/ids.json).
Equipment stats: Nintendo Life, Gamer Guides, Samurai Gamers, Super Mario Wiki.
"""
import copy
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "Super Mario RPG Switch Save Editor"
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
BACKUP_DIR = os.path.join(APP_DIR, "backups")
CHEAT_LIB_DIR = os.path.join(APP_DIR, "cheats")   # cheats/<game>/<version - build ID>/, shareable
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)     # bundled files live here inside the .exe
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"),
                             APP_NAME, "settings.json")
TITLE_ID = "0100BC0018138000"
SLOT_PREFIX = "SMR_Save_Ver0011"
SLOT_NAMES = {"000": "Autosave", "002": "Slot 1", "003": "Slot 2", "004": "Slot 3",
              "005": "Backup copy of last save"}
MIRROR_SLOT = "005"
SINGLE_LAYOUT = "save"  # backup subfolder name for single-folder save layouts

ITEM_NAMES = [
    "(none)", "Hammer", "Super Hammer", "Masher", "Lucky Hammer", "Ultra Hammer", "NokNok Shell",
    "Troopa Shell", "Lazy Shell (weapon)", "Punch Glove", "Mega Glove", "Froggie Stick",
    "Ribbit Stick", "Cymbals", "Sonic Cymbal", "Whomp Glove", "Sticky Glove", "Finger Shot",
    "Hand Gun", "Hand Cannon", "Star Gun", "Double Punch", "Chomp Shell", "Chomp",
    "Spiked Link", "Hurly Gloves", "Drill Claw", "Slap Glove", "Super Slap", "Parasol", "War Fan",
    "Frying Pan", "Shirt", "Thick Shirt", "Mega Shirt", "Happy Shirt", "Sailor Shirt",
    "Fluffy Shirt", "Fire Shirt", "Hero Shirt", "Pants", "Thick Pants", "Mega Pants", "Work Pants",
    "Happy Pants", "Sailor Pants", "Fluffy Pants", "Fire Pants", "Prince Pants", "Mega Cape",
    "Happy Cape", "Sailor Cape", "Fluffy Cape", "Fire Cape", "Star Cape", "Happy Shell",
    "Courage Shell", "Fire Shell", "Heal Shell", "Lovely Dress", "Sailor Dress", "Fluffy Dress",
    "Fire Dress", "Royal Dress", "Super Suit", "Lazy Shell (armor)", "Jump Shoes", "Zoom Shoes",
    "Antidote Pin", "Wake-Up Pin", "Trueform Pin", "Fearless Pin", "Safety Badge", "Nurture Ring",
    "Safety Ring", "Signal Ring", "Jinx Belt", "Defense Scarf", "Attack Scarf", "Feather",
    "Troopa Medal", "Ghost Medal", "Booster's Charm", "Quartz Charm", "Exp. Booster", "Coin Trick",
    "Flower Ring", "Mushroom", "Mid Mushroom", "Max Mushroom", "Yoshi Candy", "Tadpola Cola",
    "Frogleg Cola", "Finless Cola", "Croaka Cola", "Thropher Cookie", "Honey Syrup", "Maple Syrup",
    "Royal Syrup", "Flower Tab", "Flower Jar", "Flower Box", "Pick Me Up", "Cleansing Juice",
    "Party Cleanse", "Bracer", "Energizer", "Party Bracer", "Party Energizer", "Yoshi-Ade",
    "Red Essence", "Pure Water", "Poison Mushroom", "Sleepy Bomb", "Fright Bomb", "Fire Bomb",
    "Ice Bomb", "Rock Candy", "Star Egg", "Mystery Egg", "Lamb's Lure", "Sheep Attack", "See Ya",
    "Earlier Times", "Yoshi Cookie", "Goodie Bag", "Lucky Jewel", "Wilt Shroom", "Rotten Mush",
    "Moldy Mush", "Mushroom (Triplets)", "Special Frog Coin", "Wallet", "Cricket Pie", "Cricket Jam",
    "Carbo Cookie", "Alto Card", "Tenor Card", "Soprano Card", "Bright Card", "Microbomb",
    "Fireworks", "Shiny Stone", "Elder Key", "Room Key", "Shed Key", "Temple Key", "Castle Key 1",
    "Castle Key 2", "Beetle Box (empty)", "Beetle Box", "Dry Bones Flag", "Greaper Flag",
    "Boo Flag", "Seed", "Fertilizer", "(unused)", "(unused)", "Sage Stick", "Stella 023",
    "Wonder Chomp", "Enduring Brooch", "Teamwork Band", "Crystal Shard", "Stay Voucher",
    "Extra-Shiny Stone", "Monster Trophy", "Echo Signal Ring",
]
CONSUMABLE_RANGE = range(87, 131)

MARIO, MALLOW, GENO, BOWSER, PEACH = 1, 2, 3, 4, 5
ALL = (MARIO, MALLOW, GENO, BOWSER, PEACH)
WEAPON, ARMOR, ACCESSORY = "_weapon_id", "_armor_id", "_accessory_id"
SLOT_LABELS = {WEAPON: "Weapon", ARMOR: "Armor", ACCESSORY: "Accessory"}
STAT_KEYS = ("_attack", "_defence", "_magic_attack", "_magic_defence", "_speed")


def _gear():
    g = {}  # id -> (slot, characters, (atk, def, matk, mdef, spd))

    def add(slot, chars, ids, stats):
        for i, s in zip(ids, stats):
            g[i] = (slot, chars, s)

    w = lambda *atk: [(a, 0, 0, 0, 0) for a in atk]
    add(WEAPON, (MARIO,), range(1, 11), w(10, 40, 50, 0, 70, 20, 50, 90, 30, 60))
    add(WEAPON, (MALLOW,), range(11, 17), w(20, 50, 30, 70, 35, 60))
    add(WEAPON, (GENO,), range(17, 22), w(12, 24, 45, 57, 35))
    add(WEAPON, (BOWSER,), range(22, 27), w(9, 10, 30, 20, 40))
    add(WEAPON, (PEACH,), range(27, 32), w(40, 70, 50, 60, 90))
    add(WEAPON, (MALLOW,), [158], [(80, 0, 15, 0, 0)])
    add(WEAPON, (GENO,), [159], w(62))
    add(WEAPON, (BOWSER,), [160], w(57))

    a = lambda *pairs: [(0, d, 0, m, 0) for d, m in pairs]
    add(ARMOR, (MARIO,), range(32, 40), a((6, 6), (12, 8), (18, 10), (24, 12), (30, 15), (36, 18), (42, 21), (48, 24)))
    add(ARMOR, (MALLOW,), [40, 41, 42, 44, 45, 46, 47, 48],
        a((6, 3), (12, 6), (18, 9), (24, 12), (30, 15), (36, 18), (42, 21), (48, 24)))
    add(ARMOR, (GENO,), range(49, 55), a((6, 3), (12, 6), (18, 9), (24, 12), (30, 15), (36, 18)))
    add(ARMOR, (BOWSER,), range(55, 59), a((6, 3), (12, 6), (18, 9), (24, 12)))
    add(ARMOR, (PEACH,), range(59, 64), a((24, 12), (30, 15), (36, 18), (42, 21), (48, 24)))
    add(ARMOR, ALL, [43, 64, 65], [(10, 15, 10, 5, 5), (50, 50, 50, 50, 30), (-50, 127, -50, 127, -50)])

    acc = {66: (0, 1, 5, 1, 2), 67: (0, 5, 0, 5, 10), 68: (0, 2, 0, 2, 0), 69: (0, 3, 0, 3, 0),
           70: (0, 4, 0, 4, 0), 71: (0, 5, 0, 5, 0), 72: (0, 5, 0, 5, 0), 74: (0, 5, 0, 5, 5),
           76: (27, 27, 0, 0, 12), 77: (0, 15, 0, 15, 0), 78: (30, 30, 30, 30, 30),
           79: (0, 5, 0, 5, 20), 80: (0, 0, 0, 0, 20), 82: (7, 7, 7, 7, -5), 167: (0, 0, 0, 0, 10)}
    only = {66: (MARIO,), 78: (MARIO,), 85: (MARIO,), 73: (PEACH,)}
    for i in list(range(66, 87)) + [161, 162, 167]:
        g[i] = (ACCESSORY, only.get(i, ALL), acc.get(i, (0, 0, 0, 0, 0)))
    return g


GEAR = _gear()
EQUIP_IDS = sorted(GEAR)
KEY_IDS = [i for i in range(131, len(ITEM_NAMES)) if i not in GEAR and ITEM_NAMES[i] != "(unused)"]
SHARED_MAX = 5    # most copies allowed of gear that every character can wear

GENERAL_FIELDS = [
    ("_coin", "Coins", 0, 9999),
    ("_frog_coin", "Frog Coins", 0, 9999),
    ("_current_flower_point", "Flower Points (current)", 0, 99),
    ("_max_flower_point", "Flower Points (max)", 0, 99),
    ("_wine_coin", "Wine Coins", 0, 9999),
    ("_play_time", "Play time (seconds)", 0, 10**9),
]

CHAR_FIELDS = [
    ("_level", "Level", 1, 30),
    ("_experience", "Experience", 0, 9999),     # 9,999 EXP = level 30, the cap
    ("_hp", "HP (current)", 0, 999),
    ("_hp_max", "HP (max)", 1, 999),
    ("_speed", "Speed", 0, 255),
    ("_attack", "Attack", 0, 255),
    ("_defence", "Defense", 0, 255),
    ("_magic_attack", "Magic Attack", 0, 255),
    ("_magic_defence", "Magic Defense", 0, 255),
]

CARRY_MAX = 30     # per item; extra goes to the Storage Box at Mario's Pad
STORAGE_MAX = 99
FIELD_ONLY = (99, 100, 101)   # Flower Tab/Jar/Box raise max FP; not in the battle menu


def is_recovery(i):
    """Default menu for an item the save hasn't filed yet: 87–101 and 127–130 are Recovery
    items, everything else (including Lucky Jewel, 126) is a Battle item."""
    return 87 <= i <= 101 or 127 <= i <= 130


def item_name(i):
    return ITEM_NAMES[i] if 0 <= i < len(ITEM_NAMES) else f"Unknown #{i}"


def item_label(i):
    return f"{i:3d}  {item_name(i)}"


def gear_label(i):
    if not i:
        return "  0  (nothing)"
    stats = GEAR.get(i, (None, None, (0,) * 5))[2]
    bits = [f"{n} {v:+d}" for n, v in zip(("Atk", "Def", "MgAtk", "MgDef", "Spd"), stats) if v]
    return f"{item_label(i)}" + (f"   ({', '.join(bits)})" if bits else "")


def star_count(flags):
    return bin(flags & 0xFF).count("1")


# Decimal numbers are kept as their original text (wrapped in markers while loaded) so
# values the editor doesn't touch are written back exactly as the game wrote them.
RAW_MARK = "\x01"
RAW_NUMBER = re.compile(r'"\\u0001([^"\\]*)\\u0001"')


def load_save(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-16-le"), parse_float=lambda s: RAW_MARK + s + RAW_MARK)


def dump_save(data, path):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = RAW_NUMBER.sub(r"\1", text)
    with open(path, "wb") as f:
        f.write(text.encode("utf-16-le"))


def ordered_counts(lst):
    counts = {}
    for i in lst:
        if i:
            counts[i] = counts.get(i, 0) + 1
    return counts


def pad(lst, size):
    return (lst + [0] * size)[:size]


def has_slots(folder):
    return bool(glob.glob(os.path.join(glob.escape(folder), SLOT_PREFIX + "[0-9][0-9][0-9]")))


def save_copies(folder):
    """Folders holding the save files: ["0", "1"] (Ryujinx) or the folder itself."""
    dual = [os.path.join(folder, c) for c in ("0", "1") if has_slots(os.path.join(folder, c))]
    if dual:
        return dual
    return [folder] if has_slots(folder) else []


def resolve_save_folder(folder):
    """Accept the exact save folder, a 0/1 copy, or any parent and find the save in it."""
    if not folder or not os.path.isdir(folder):
        return None
    if os.path.basename(folder) in ("0", "1") and save_copies(os.path.dirname(folder)):
        return os.path.dirname(folder)
    if save_copies(folder):
        return folder
    found = []
    for depth in range(1, 7):
        pattern = os.path.join(glob.escape(folder), *(["*"] * depth), SLOT_PREFIX + "[0-9][0-9][0-9]")
        found = glob.glob(pattern)
        if found:
            break
    if not found:
        return None
    newest = max(found, key=os.path.getmtime)
    return resolve_save_folder(os.path.dirname(newest))


def candidate_roots():
    roots = []
    appdata = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")
    bases = [appdata, os.path.join(home, ".config"), os.path.join(home, ".local", "share"),
             os.path.join(home, "Library", "Application Support")]
    # Linux Flatpaks (most Linux and Steam Deck installs) keep data in ~/.var/app/<app id>/{config,data}
    bases += glob.glob(os.path.join(glob.escape(os.path.join(home, ".var", "app")), "*", "config"))
    bases += glob.glob(os.path.join(glob.escape(os.path.join(home, ".var", "app")), "*", "data"))
    for base in bases:
        if not base:
            continue
        roots.append(os.path.join(base, "Ryujinx", "bis", "user", "save"))
        for emu in ("yuzu", "suyu", "sudachi", "citron", "eden", "torzu"):
            roots.append(os.path.join(base, emu, "nand", "user", "save"))
    # Portable Ryujinx builds sitting next to this app or in Downloads/Desktop.
    for base in (os.path.dirname(APP_DIR), os.path.join(home, "Downloads"), os.path.join(home, "Desktop")):
        for depth in range(0, 4):
            pattern = os.path.join(glob.escape(base), *(["*"] * depth), "bis", "user", "save")
            roots += glob.glob(pattern)
    return [r for r in roots if os.path.isdir(r)]


def autodetect():
    for root in candidate_roots():
        if os.sep + "nand" + os.sep in root:   # yuzu family: save/0000.../<user>/<title id>
            hits = glob.glob(os.path.join(glob.escape(root), "*", "*", TITLE_ID))
            hits += glob.glob(os.path.join(glob.escape(root), "*", "*", TITLE_ID.lower()))
            hits = [h for h in hits if save_copies(h)]
            if hits:
                return max(hits, key=os.path.getmtime)
        else:
            found = resolve_save_folder(root)
            if found:
                return found
    return None


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def store_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


def backup_time(name):
    """When a backup was made, from its folder name (YYYY-MM-DD_HH-MM-SS …)."""
    try:
        return datetime.strptime(name[:19], "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        path = os.path.join(BACKUP_DIR, name)
        return datetime.fromtimestamp(os.path.getmtime(path)) if os.path.exists(path) else None


def age_text(delta):
    s = max(0, int(delta.total_seconds()))
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if s >= size:
            n = s // size
            return f"{n} {unit}{'s' if n != 1 else ''}"
    return "less than a minute"


def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


def describe_changes(old, new):
    """Human-readable (group, line) pairs for everything that differs between two saves."""
    out = []
    for key, label, _, _ in GENERAL_FIELDS:
        if old.get(key) != new.get(key):
            out.append(("General", f"{label}: {old.get(key)} → {new.get(key)}"))

    shown = [("_equip" + k, "Attack Defense MagicAttack MagicDefense Speed".split()[n])
             for n, k in enumerate(STAT_KEYS)]
    for po, pn in zip(old["_player_work"], new["_player_work"]):
        if not po.get("_name"):
            continue
        who = po["_name"]
        for key, label, _, _ in CHAR_FIELDS:
            if po.get(key) != pn.get(key):
                out.append((who, f"{label}: {po.get(key)} → {pn.get(key)}"))
        for slot in (WEAPON, ARMOR, ACCESSORY):
            if po.get(slot) != pn.get(slot):
                out.append((who, f"{SLOT_LABELS[slot]}: {item_name(po.get(slot, 0))} → "
                                 f"{item_name(pn.get(slot, 0))}"))
        totals = [f"{re.sub(r'(?<!^)(?=[A-Z])', ' ', lbl)} {po[k]} → {pn[k]}"
                  for k, lbl in shown if k in po and po[k] != pn.get(k)]
        if totals:
            out.append((who, "Stats with equipment: " + ", ".join(totals)))

    oi, ni = old["_item_manager"], new["_item_manager"]
    before, after = ordered_counts(oi["_item_list"]), ordered_counts(ni["_item_list"])
    for i in sorted(set(before) | set(after)):
        a, b = before.get(i, 0), after.get(i, 0)
        if a != b:
            note = "  (new)" if not a else "  (removed)" if not b else ""
            out.append(("Items carried", f"{item_name(i)}: {a} → {b}{note}"))
    for i, (a, b) in enumerate(zip(oi["_storage_box_list"], ni["_storage_box_list"])):
        if a != b:
            out.append(("Storage Box", f"{item_name(i)}: {a} → {b}"))

    before, after = ordered_counts(oi["_equipment_item_list"]), ordered_counts(ni["_equipment_item_list"])
    for i in sorted(set(before) | set(after)):
        a, b = before.get(i, 0), after.get(i, 0)
        if a != b:
            out.append(("Equipment bag", f"{item_name(i)}: {a} → {b}"))
    ko = {i for i in oi["_important_item_list"] if i}
    kn = {i for i in ni["_important_item_list"] if i}
    for i in sorted(ko ^ kn):
        out.append(("Key items", f"{item_name(i)}: {'added' if i in kn else 'removed'}"))
    return out



# ---------- cheats (Atmosphère cheat format, used by Ryujinx, the yuzu family and Atmosphère) ----------
CHEAT_MOD_NAME = "SMR Save Editor Cheats"      # our own mod folder, so we never touch other cheat files
CHEATS_URL = "https://www.cheatslips.com/game/super-mario-rpg"
WALKTHROUGH_URL = "https://game8.co/games/Super-Mario-RPG/archives/417834"
TREASURE_URL = "https://www.ign.com/wikis/super-mario-rpg-switch-remake/Hidden_Treasure_Chest_Locations"
HIDDEN_TREASURES = 39
CHAPTERS = [   # (chapter, goal, Game8 guide)
    ("Chapter 1", "1st Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434340"),
    ("Chapter 2", "2nd Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434357"),
    ("Chapter 3", "3rd Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434362"),
    ("Chapter 4", "4th Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434418"),
    ("Chapter 5", "5th Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434356"),
    ("Chapter 6", "6th Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434358"),
    ("Chapter 7", "7th Star Piece", "https://game8.co/games/Super-Mario-RPG/archives/434419"),
    ("Post-game", "Post-game content", "https://game8.co/games/Super-Mario-RPG/archives/431396"),
]
CHEAT_LINE = re.compile(r"^[0-9A-Fa-f]{8}( [0-9A-Fa-f]{8})*$")
KNOWN_BUILDS = {"E968832CADE2AD7C": "v1.0.0"}
CHEAT_GUIDE_URL = "https://github.com/dlr-developer/super-mario-rpg-switch-save-editor/blob/main/docs/CHEATS.md"
CHEAT_GUIDE = [   # (tag, line) shown in the in-app guide; docs/CHEATS.md has the full version
    ("warn", "Cheats are experimental. A wrong or mismatched code can crash the game or corrupt your save. "
             "Always back up first."),
    ("h", "How cheats work"),
    ("", "While the game runs, everything it tracks (HP, coins, items) is a number in memory. A cheat is a "
         "short list of instructions such as \"write 9999 at this address\". The emulator, or Atmosphère on a "
         "Switch, repeats them many times a second, so the value stays locked. Cheats never change your save "
         "file directly, but if you save while one is on, its effects are saved too."),
    ("h", "Will a code work for me?"),
    ("", "• Game version: a code only works for the build it was made for. The build ID is shown on this tab "
         "(v1.0.0 is E968832CADE2AD7C). After a game update, old codes usually stop working."),
    ("", "• Emulator: Ryujinx and its forks, the yuzu family (yuzu, suyu, sudachi, citron, eden, torzu) and "
         "Atmosphère on a real Switch all use the same Atmosphère cheat format. Most codes work in all of "
         "them, but some behave differently, so test before relying on one."),
    ("h", "Using a cheat"),
    ("", "1. Back up your save (Back up now… at the top of the window)."),
    ("", "2. Import a cheat file or click Add cheat… and paste a code made for your build ID."),
    ("", "3. Turn on only the cheats you want (double-click a row)."),
    ("", "4. Click Install to emulator (or Export for Switch), then restart the game."),
    ("", "5. If the game misbehaves: close it, turn the cheat off, Install again, and restore your backup."),
    ("h", "Where the files go"),
    ("", "• Ryujinx: mods\\contents\\0100bc0018138000\\SMR Save Editor Cheats\\cheats\\<build ID>.txt, switched "
         "on through Ryujinx's enabled.txt. You'll also see them under right-click → Manage Cheats."),
    ("", "• yuzu family: load\\0100BC0018138000\\SMR Save Editor Cheats\\cheats\\<build ID>.txt. Enable the "
         "\"SMR Save Editor Cheats\" add-on in the game's properties."),
    ("", "• Switch: atmosphere/contents/0100BC0018138000/cheats/<build ID>.txt on the SD card."),
    ("h", "Code format"),
    ("", "[Cheat name]\n04000000 01234567 0000270F\n(format example only, not a real code)"),
    ("", "Each line is groups of 8 hexadecimal digits. A name in { } is a master code: some cheats need it "
         "turned on as well."),
    ("h", "Making your own"),
    ("", "Search the game's memory for a value you can see (for example your coins), change it in game, "
         "search again, and repeat until one address is left. Tools like Breeze or EdiZon SE on a Switch can "
         "then write it out as a cheat code. Data that moves around between sessions needs a pointer search "
         "so the code keeps working. See the full guide online for details."),
]


def parse_cheats(text):
    """Split an Atmosphère cheat file into [{name, lines, master}]. Raises ValueError if malformed."""
    cheats, current = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line[0] in "[{":
            close = "]" if line[0] == "[" else "}"
            if not line.endswith(close) or len(line) < 3:
                raise ValueError(f"Line {n}: a cheat name must look like [Name].")
            current = {"name": line[1:-1].strip(), "lines": [], "master": line[0] == "{"}
            cheats.append(current)
        else:
            if current is None:
                raise ValueError(f"Line {n}: code found before any [Cheat name].")
            words = line.split()
            if not CHEAT_LINE.match(" ".join(words)):
                raise ValueError(f"Line {n}: '{line}' isn't a cheat code line (groups of 8 hex digits).")
            current["lines"].append(" ".join(w.upper() for w in words))
    empty = [c["name"] for c in cheats if not c["lines"]]
    if empty:
        raise ValueError(f"These cheats have no code: {', '.join(empty)}")
    return cheats


def format_cheats(cheats):
    out = []
    for c in cheats:
        out.append(("{%s}" if c.get("master") else "[%s]") % c["name"])
        out.extend(c["lines"])
        out.append("")
    return "\n".join(out)


# ---------- cheat library: cheats/<game>/<version - build ID>/ ----------
GAME_FOLDER = f"{TITLE_ID} - Super Mario RPG"
TEST_TARGETS = ("Ryujinx", "yuzu family", "Switch")
TEST_STATES = ("Untested", "Works", "Doesn't work")
TEST_ICONS = {"Untested": "❔", "Works": "✅", "Doesn't work": "❌"}


def library_builds():
    """{build ID: folder} for every game version that has a cheat folder."""
    root = os.path.join(CHEAT_LIB_DIR, GAME_FOLDER)
    found = {}
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            m = re.search(r"([0-9A-Fa-f]{16})$", name)
            if m and os.path.isdir(os.path.join(root, name)):
                found[m.group(1).upper()] = os.path.join(root, name)
    return found


def build_folder(bid):
    return library_builds().get(bid) or os.path.join(
        CHEAT_LIB_DIR, GAME_FOLDER, f"{KNOWN_BUILDS.get(bid, 'unknown version')} - {bid}")


def read_library(bid):
    """Cheats filed for one build: the Atmosphère file plus the details in info.json."""
    folder = library_builds().get(bid)
    if not folder:
        return []
    try:
        cheats = parse_cheats(open(os.path.join(folder, bid + ".txt"), encoding="utf-8-sig").read())
    except (OSError, ValueError):
        return []
    try:
        info = json.load(open(os.path.join(folder, "info.json"), encoding="utf-8"))
        details = {c["name"]: c for c in info.get("cheats", [])}
    except (OSError, ValueError, KeyError):
        details = {}
    for c in cheats:
        d = details.get(c["name"], {})
        c["description"] = d.get("description", "")
        c["tested"] = {t: d.get("tested", {}).get(t, "Untested") for t in TEST_TARGETS}
    return cheats


def write_library(bid, cheats):
    """Write a build's folder: <build ID>.txt (ready for any emulator), info.json, README.md.

    Known game versions always keep their folder (with a "no cheats yet" README) so the library
    shows every version; folders for hand-entered build IDs are removed once they're empty."""
    folder = build_folder(bid)
    version = KNOWN_BUILDS.get(bid, "unknown version")
    if not cheats:
        for f in (bid + ".txt", "info.json", "README.md"):
            if os.path.exists(os.path.join(folder, f)):
                os.remove(os.path.join(folder, f))
        if bid not in KNOWN_BUILDS:
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
            return
    os.makedirs(folder, exist_ok=True)
    header = f"# Super Mario RPG {version} cheats\n\nBuild ID `{bid}` · title ID `{TITLE_ID}`\n\n"
    if not cheats:
        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(header + "No cheats for this version yet. Add some on the editor's **Cheats** tab and "
                    "they'll be filed here automatically. See the [cheat guide](../../../docs/CHEATS.md).\n")
        return
    with open(os.path.join(folder, bid + ".txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(format_cheats(cheats))
    info = {"game": "Super Mario RPG", "title_id": TITLE_ID, "version": version, "build_id": bid,
            "cheats": [{"name": c["name"], "description": c.get("description", ""),
                        "master": bool(c.get("master")),
                        "tested": {t: c.get("tested", {}).get(t, "Untested") for t in TEST_TARGETS}}
                       for c in cheats]}
    with open(os.path.join(folder, "info.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    rows = ["| Cheat | What it does | " + " | ".join(TEST_TARGETS) + " |",
            "|---|---|" + "---|" * len(TEST_TARGETS)]
    for c in cheats:
        name = c["name"] + (" *(master code)*" if c.get("master") else "")
        tested = " | ".join(TEST_ICONS[c.get("tested", {}).get(t, "Untested")] for t in TEST_TARGETS)
        rows.append(f"| {name} | {c.get('description', '') or '—'} | {tested} |")
    with open(os.path.join(folder, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "\n".join(rows) + "\n\n✅ works · ❌ doesn't work · ❔ untested\n\n"
                "Install with the editor's **Cheats** tab (**Import cheat file…** and pick "
                f"`{bid}.txt`), or copy `{bid}.txt` into your emulator's cheat folder. "
                "See the [cheat guide](../../../docs/CHEATS.md).\n")


def ensure_known_folders():
    """Create a folder for every known game version, so the library lists them all."""
    for bid in KNOWN_BUILDS:
        if bid not in library_builds():
            try:
                write_library(bid, [])
            except OSError:
                pass


def emulator_for(save_folder):
    """Work out which emulator a save folder belongs to, and where its cheats go.

    Returns {name, root, cheat_dir, enabled_file, logs} or None for a plain folder (e.g. a
    save dumped from a Switch)."""
    if not save_folder:
        return None
    parts = os.path.normpath(save_folder).split(os.sep)
    low = [p.lower() for p in parts]
    for i in range(len(low) - 2):
        if low[i:i + 3] == ["bis", "user", "save"]:            # Ryujinx (installed or portable)
            root = os.sep.join(parts[:i]) or os.sep
            title_dir = os.path.join(root, "mods", "contents", TITLE_ID.lower())
            return {"name": "Ryujinx", "root": root,
                    "cheat_dir": os.path.join(title_dir, CHEAT_MOD_NAME, "cheats"),
                    "enabled_file": os.path.join(title_dir, "cheats", "enabled.txt"),
                    "logs": [os.path.join(root, "Logs"), os.path.join(os.environ.get("APPDATA", ""), "Ryujinx", "Logs")]}
        if low[i:i + 3] == ["nand", "user", "save"]:           # yuzu, suyu, sudachi, citron, eden, torzu
            root = os.sep.join(parts[:i]) or os.sep
            return {"name": os.path.basename(root) or "yuzu-based emulator", "root": root,
                    "cheat_dir": os.path.join(root, "load", TITLE_ID, CHEAT_MOD_NAME, "cheats"),
                    "enabled_file": None, "logs": [os.path.join(root, "log")]}
    return None


def detect_build_ids(emulator):
    """Build IDs the emulator logged for this game, newest log first (Ryujinx logs them)."""
    found = []
    for folder in (emulator or {}).get("logs", []):
        logs = sorted(glob.glob(os.path.join(glob.escape(folder), "*.log")), key=os.path.getmtime, reverse=True)
        for path in logs[:10]:
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines):
                if "Build ids found for application" in line and TITLE_ID in line.upper():
                    for nxt in lines[n + 1:n + 8]:
                        token = nxt.strip()
                        if re.fullmatch(r"[0-9A-Fa-f]{16,64}", token):
                            bid = token[:16].upper()
                            if bid not in found:
                                found.append(bid)
                        else:
                            break
            if found:
                return found
    return found


PALETTES = {
    "light": {"bg": "#f0f0f0", "surface": "#e6e6e6", "field": "#ffffff", "fg": "#000000", "muted": "#555555",
              "faint": "#888888", "border": "#c8c8c8", "hover": "#dcdcdc", "select": "#0078d7",
              "accent": "#0b5cad", "warn": "#b26a00", "banner": "#fff4e0", "tag_worn": "#0b5cad", "tag_key": "#6a4c93",
              "tag_none": "#999999", "tag_on": "#2e7d32", "tag_off": "#888888"},
    "dark": {"bg": "#1f2125", "surface": "#2b2e33", "field": "#26292e", "fg": "#e8e8e8", "muted": "#a9adb4",
             "faint": "#7d828a", "border": "#3d4148", "hover": "#353940", "select": "#2f5f9e",
             "accent": "#6cb4ff", "warn": "#ffb74d", "banner": "#3a3020", "tag_worn": "#6cb4ff", "tag_key": "#c7a8ff",
             "tag_none": "#6f747c", "tag_on": "#7fd88a", "tag_off": "#7d828a"},
}
THEMES = ("System", "Light", "Dark")


def system_prefers_dark():
    """True if the system is set to dark mode for apps (Windows, macOS, GNOME/KDE on Linux)."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                 capture_output=True, text=True, timeout=2).stdout
            return "dark" in out.lower()
        except (OSError, subprocess.SubprocessError):
            return False
    if sys.platform != "win32":
        try:   # GNOME, and most desktops that follow the freedesktop colour-scheme setting
            out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                                 capture_output=True, text=True, timeout=2).stdout
            if "dark" in out.lower():
                return True
        except (OSError, subprocess.SubprocessError):
            pass
        try:   # KDE Plasma
            kde = open(os.path.expanduser("~/.config/kdeglobals"), encoding="utf-8", errors="ignore").read()
            return "colorscheme=" in kde.lower() and "dark" in kde.lower().split("colorscheme=", 1)[1].split("\n", 1)[0]
        except OSError:
            return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


class Editor(tk.Tk):
    def __init__(self, folder=None):
        super().__init__()
        self.title(APP_NAME)
        self._set_icon()
        self.geometry("960x740")
        self.minsize(820, 560)
        self.settings = load_settings()
        self.root_dir = tk.StringVar()
        self.slot = tk.StringVar()
        self.slot_files = []
        self.data = None
        self.chars = []
        self.general_vars = {}
        self.char_vars = {}
        self.gear_vars = {}
        self.items = {}     # consumable id -> number carried
        self.order = []     # item IDs in the order the game stored them
        self.known_recovery, self.known_battle = set(), set()
        self.storage = []   # per-ID counts in the Storage Box
        self.equipment = []
        self.key_items = []
        self._key_warned = False

        self._sort = {}          # tree -> (column, descending)
        self.cheats, self.emulator = [], None
        self.load_cheat_library()
        self._style()
        self._build_top()
        self._build_tabs()
        self.apply_theme()
        start = folder or self.settings.get("save_folder")
        start = resolve_save_folder(start) if start else None
        self.set_folder(start or autodetect())

    # ---------- layout ----------
    def _set_icon(self):
        icons = os.path.join(RESOURCE_DIR, "assets")
        try:
            if sys.platform == "win32":
                self.iconbitmap(default=os.path.join(icons, "icon.ico"))   # also used by pop-ups
            else:
                self._icon = tk.PhotoImage(file=os.path.join(icons, "icon.png"))
                self.iconphoto(True, self._icon)
        except (tk.TclError, OSError):
            pass

    def _style(self):
        self.style = ttk.Style(self)
        self.base_theme = self.style.theme_use()      # the native look, used for Light
        self.palette = PALETTES["light"]
        self._style_common()

    def _build_top(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Save folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.root_dir, state="readonly").grid(row=0, column=1, sticky="ew", padx=4)
        fb = ttk.Frame(top)
        fb.grid(row=0, column=2, sticky="ew")
        ttk.Button(fb, text="Browse…", command=self.browse).pack(side="left")
        ttk.Button(fb, text="Auto-detect", command=self.redetect).pack(side="left", padx=(4, 0))

        ttk.Label(top, text="Slot:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.slot_box = ttk.Combobox(top, textvariable=self.slot, state="readonly")
        self.slot_box.grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        self.slot_box.bind("<<ComboboxSelected>>", lambda e: self.load_slot())
        btns = ttk.Frame(top)
        btns.grid(row=1, column=2, pady=(6, 0), sticky="ew")
        ttk.Button(btns, text="Reload", command=self.load_slot).pack(side="left")
        self.primary_button(btns, "Save changes", self.save).pack(side="left", padx=(4, 0))

        bk = ttk.LabelFrame(top, text="Backups", padding=6)
        bk.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(bk, text="Back up now…", command=self.backup_now).pack(side="left")
        ttk.Button(bk, text="Restore a backup…", command=self.restore_dialog).pack(side="left", padx=4)
        ttk.Button(bk, text="Open backups folder", command=self.open_backups).pack(side="left")
        self.backup_count = tk.StringVar()
        ttk.Label(bk, textvariable=self.backup_count, style="Muted.TLabel").pack(side="left", padx=10)
        self.theme_choice = tk.StringVar(value=self.settings.get("theme", "System"))
        theme = ttk.Combobox(bk, textvariable=self.theme_choice, values=THEMES, state="readonly", width=8)
        theme.pack(side="right")
        theme.bind("<<ComboboxSelected>>", self.on_theme_pick)
        ttk.Label(bk, text="Theme:").pack(side="right", padx=(0, 4))
        top.columnconfigure(1, weight=1)

        self.status = tk.StringVar(value="Close the game/emulator before saving or restoring.")
        ttk.Label(self, textvariable=self.status, style="Muted.TLabel", padding=(8, 0)).pack(
            side="bottom", fill="x", pady=4)

    def _build_tabs(self):
        nb = self.nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # General
        gen = ttk.Frame(nb, padding=12)
        nb.add(gen, text="General")
        for r, (key, label, lo, hi) in enumerate(GENERAL_FIELDS):
            ttk.Label(gen, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Spinbox(gen, from_=lo, to=hi, textvariable=v, width=14).grid(row=r, column=1, sticky="w", padx=8)
            if key != "_play_time":
                ttk.Button(gen, text="Max", width=6, command=lambda k=key: self.max_general(k)).grid(
                    row=r, column=2, sticky="w")
            ttk.Label(gen, text=f"({lo}–{hi})", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))
            self.general_vars[key] = (v, lo, hi)
        ttk.Button(gen, text="Max all", command=self.max_general).grid(
            row=len(GENERAL_FIELDS), column=1, sticky="w", padx=8, pady=(8, 0))
        self.info = tk.StringVar()
        ttk.Label(gen, textvariable=self.info, style="Muted.TLabel", justify="left").grid(
            row=len(GENERAL_FIELDS) + 1, column=0, columnspan=4, sticky="w", pady=(16, 0))

        # Characters
        ch = ttk.Frame(nb, padding=12)
        nb.add(ch, text="Characters")
        ttk.Label(ch, text="Character:").grid(row=0, column=0, sticky="w")
        self.char_sel = tk.StringVar()
        self.char_box = ttk.Combobox(ch, textvariable=self.char_sel, state="readonly", width=16)
        self.char_box.grid(row=0, column=1, sticky="w", padx=8)
        self.char_box.bind("<<ComboboxSelected>>", lambda e: self.show_char())
        mx = ttk.Frame(ch)
        mx.grid(row=0, column=3, sticky="w", padx=(24, 0))
        self.max_char_btn = ttk.Button(mx, text="Max out character", command=self.max_character)
        self.max_char_btn.pack(side="left")
        ttk.Button(mx, text="Max out all characters", command=lambda: self.max_character(everyone=True)).pack(
            side="left", padx=6)
        self._char_index = None
        for r, (key, label, lo, hi) in enumerate(CHAR_FIELDS, start=1):
            ttk.Label(ch, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Spinbox(ch, from_=lo, to=hi, textvariable=v, width=14,
                        command=self.update_totals).grid(row=r, column=1, sticky="w", padx=8)
            ttk.Label(ch, text=f"({lo}–{hi})", style="Faint.TLabel").grid(row=r, column=2, sticky="w")
            self.char_vars[key] = (v, lo, hi)

        eqf = ttk.LabelFrame(ch, text="Equipped", padding=8)
        eqf.grid(row=1, column=3, rowspan=len(CHAR_FIELDS), sticky="nw", padx=(24, 0))
        self.gear_boxes = {}
        for r, slot in enumerate((WEAPON, ARMOR, ACCESSORY)):
            ttk.Label(eqf, text=SLOT_LABELS[slot]).grid(row=r * 2, column=0, sticky="w")
            v = tk.StringVar()
            box = ttk.Combobox(eqf, textvariable=v, state="readonly", width=60)
            box.grid(row=r * 2 + 1, column=0, sticky="w", pady=(0, 8))
            box.bind("<<ComboboxSelected>>", lambda e: self.update_totals())
            self.gear_vars[slot] = v
            self.gear_boxes[slot] = box
        self.totals = tk.StringVar()
        ttk.Label(eqf, textvariable=self.totals, style="Muted.TLabel", justify="left").grid(
            row=6, column=0, sticky="w")
        ttk.Label(ch, style="Muted.TLabel", wraplength=820, text=(
            "Only gear that character can wear is listed. Gear you don't own is added to your bag "
            "automatically. Stat changes and gear changes also update the 'with equipment' totals "
            "the menu shows. Switching characters keeps your unsaved edits. Max out sets level, EXP, "
            "HP and every stat to the highest value shown.")).grid(
            row=len(CHAR_FIELDS) + 1, column=0, columnspan=4, sticky="w", pady=(12, 0))

        # Items
        it = ttk.Frame(nb, padding=12)
        nb.add(it, text="Items")
        bag = ttk.Frame(it)
        bag.grid(row=0, column=0, columnspan=7, sticky="ew")
        ttk.Label(bag, text="Bag space", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.bag_bar = ttk.Progressbar(bag, length=300)
        self.bag_bar.pack(side="left", padx=10)
        self.bag_count = tk.StringVar()
        self.bag_label = ttk.Label(bag, textvariable=self.bag_count, style="Muted.TLabel")
        self.bag_label.pack(side="left")
        self.tree = self._make_tree(it, (("id", "ID", 50), ("name", "Item", 200), ("menu", "Menu", 160),
                                         ("qty", "Carried", 80), ("box", "Storage Box", 90)), row=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        ttk.Label(it, text="Item").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(it, text=f"Carried (0–{CARRY_MAX})").grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Label(it, text=f"Storage Box (0–{STORAGE_MAX})").grid(row=2, column=2, sticky="w", pady=(10, 0))
        self.item_pick = tk.StringVar()
        self.item_qty = tk.StringVar()
        self.item_box = tk.StringVar()
        pick = ttk.Combobox(it, textvariable=self.item_pick, state="readonly", width=28,
                            values=[item_label(i) for i in CONSUMABLE_RANGE])
        pick.grid(row=3, column=0, sticky="w")
        pick.bind("<<ComboboxSelected>>", self.on_pick)
        ttk.Spinbox(it, from_=0, to=CARRY_MAX, textvariable=self.item_qty, width=8).grid(row=3, column=1, sticky="w", padx=4)
        ttk.Spinbox(it, from_=0, to=STORAGE_MAX, textvariable=self.item_box, width=8).grid(row=3, column=2, sticky="w", padx=4)
        ttk.Button(it, text="Set", command=self.set_item).grid(row=3, column=3, padx=4)
        ttk.Button(it, text=f"Max carried ({CARRY_MAX})", command=self.max_items).grid(row=3, column=4)

        bulk = ttk.LabelFrame(it, text="Selected items", padding=8)
        bulk.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        ttk.Button(bulk, text="Select all", command=self.select_all_items).grid(row=0, column=0)
        ttk.Button(bulk, text="Clear", command=lambda: self.tree.selection_set(())).grid(row=0, column=1, padx=4)
        self.sel_count = tk.StringVar(value="0 selected")
        ttk.Label(bulk, textvariable=self.sel_count, width=12).grid(row=0, column=2, padx=(4, 12))
        ttk.Label(bulk, text="Set carried to").grid(row=0, column=3)
        self.bulk_qty = tk.StringVar(value=str(CARRY_MAX))
        ttk.Spinbox(bulk, from_=0, to=CARRY_MAX, textvariable=self.bulk_qty, width=6).grid(row=0, column=4, padx=4)
        ttk.Button(bulk, text="Apply", command=lambda: self.bulk_set("carried")).grid(row=0, column=5)
        ttk.Label(bulk, text="Set Storage Box to").grid(row=0, column=6, padx=(16, 0))
        self.bulk_box = tk.StringVar(value="0")
        ttk.Spinbox(bulk, from_=0, to=STORAGE_MAX, textvariable=self.bulk_box, width=6).grid(row=0, column=7, padx=4)
        ttk.Button(bulk, text="Apply", command=lambda: self.bulk_set("storage")).grid(row=0, column=8)
        self.show_all_items = tk.BooleanVar(value=False)
        ttk.Checkbutton(bulk, text="Show all items, including ones you don't have", variable=self.show_all_items,
                        command=self.refresh_items).grid(row=1, column=0, columnspan=9, sticky="w", pady=(6, 0))

        ttk.Label(it, style="Muted.TLabel", wraplength=820, text=(
            f"Click a row to edit one item, or Ctrl/Shift-click (or Select all) to change many at "
            f"once. You can carry up to {CARRY_MAX} of each item, and the bag holds a set number of "
            f"items in total (Bag space above). Extras belong in the Storage Box at Mario's Pad.")).grid(
            row=5, column=0, columnspan=6, sticky="w", pady=(8, 0))

        # Equipment bag & key items
        eq = ttk.Frame(nb, padding=12)
        nb.add(eq, text="Equipment Bag & Key Items")
        self.eq_tree = self._make_tree(eq, (("id", "ID", 45), ("name", "Item", 170), ("type", "Type", 90),
                                            ("who", "Who can equip", 170), ("owned", "Owned", 70),
                                            ("worn", "Equipped by", 170)))
        self.eq_tree.bind("<<TreeviewSelect>>", self.on_equipment_select)

        sel = ttk.LabelFrame(eq, text="Selected item", padding=8)
        sel.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        self.eq_selected = tk.StringVar(value="Pick one row to equip or unequip it.")
        ttk.Label(sel, textvariable=self.eq_selected, width=30).grid(row=0, column=0, sticky="w")
        ttk.Label(sel, text="Equip on:").grid(row=0, column=1, sticky="e", padx=(8, 4))
        self.equip_on = tk.StringVar()
        self.equip_on_box = ttk.Combobox(sel, textvariable=self.equip_on, state="readonly", width=22)
        self.equip_on_box.grid(row=0, column=2, sticky="w")
        ttk.Button(sel, text="Equip", command=self.equip_selected).grid(row=0, column=3, padx=4)
        ttk.Label(sel, text="Unequip from:").grid(row=0, column=4, sticky="e", padx=(12, 4))
        self.unequip_from = tk.StringVar()
        self.unequip_box = ttk.Combobox(sel, textvariable=self.unequip_from, state="readonly", width=12)
        self.unequip_box.grid(row=0, column=5, sticky="w")
        ttk.Button(sel, text="Unequip", command=self.unequip_selected).grid(row=0, column=6, padx=4)

        bulk = ttk.LabelFrame(eq, text="Selected items", padding=8)
        bulk.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        ttk.Button(bulk, text="Select all", command=lambda: self.eq_tree.selection_set(
            self.eq_tree.get_children())).grid(row=0, column=0)
        ttk.Button(bulk, text="Clear", command=lambda: self.eq_tree.selection_set(())).grid(row=0, column=1, padx=4)
        self.eq_count = tk.StringVar(value="0 selected")
        ttk.Label(bulk, textvariable=self.eq_count, width=12).grid(row=0, column=2, padx=(4, 12))
        ttk.Label(bulk, text="Set owned to").grid(row=0, column=3)
        self.eq_qty = tk.StringVar(value="1")
        ttk.Spinbox(bulk, from_=0, to=SHARED_MAX, textvariable=self.eq_qty, width=6).grid(row=0, column=4, padx=4)
        ttk.Button(bulk, text="Apply", command=self.bulk_owned).grid(row=0, column=5)
        ttk.Button(bulk, text="Max owned", command=lambda: self.bulk_owned(maximum=True)).grid(row=0, column=6, padx=(12, 0))
        self.show_all_gear = tk.BooleanVar(value=False)
        ttk.Checkbutton(bulk, text="Show all equipment and key items, including ones you don't have",
                        variable=self.show_all_gear, command=self.refresh_equipment).grid(
            row=1, column=0, columnspan=7, sticky="w", pady=(6, 0))

        ttk.Label(eq, style="Muted.TLabel", wraplength=820, text=(
            f"Limits: 1 of each item only one character can wear (e.g. Hammer), up to {SHARED_MAX} of "
            f"gear everyone can wear (e.g. Work Pants), and 1 of each key item. You can't own fewer "
            "copies than are being worn. Equipping here also updates the Characters tab.")).grid(
            row=3, column=0, columnspan=6, sticky="w", pady=(8, 0))
        # Walkthrough
        wk = ttk.Frame(nb, padding=12)
        nb.add(wk, text="Walkthrough")
        prog = ttk.LabelFrame(wk, text="Your progress (from this save)", padding=10)
        prog.grid(row=0, column=0, columnspan=6, sticky="ew")
        self.walk_now = tk.StringVar()
        ttk.Label(prog, textvariable=self.walk_now, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        self.walk_btn = self.primary_button(prog, "Open this chapter's guide", self.open_current_chapter)
        self.walk_btn.grid(row=0, column=3, sticky="e", padx=(12, 0))
        ttk.Label(prog, text="Star Pieces").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.star_bar = ttk.Progressbar(prog, maximum=7, length=260)
        self.star_bar.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))
        self.star_text = tk.StringVar()
        ttk.Label(prog, textvariable=self.star_text, style="Muted.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Label(prog, text="Hidden treasures").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.treasure_bar = ttk.Progressbar(prog, maximum=HIDDEN_TREASURES, length=260)
        self.treasure_bar.grid(row=2, column=1, sticky="w", padx=8, pady=(4, 0))
        self.treasure_text = tk.StringVar()
        ttk.Label(prog, textvariable=self.treasure_text, style="Muted.TLabel").grid(row=2, column=2, sticky="w", pady=(4, 0))
        prog.columnconfigure(2, weight=1)

        self.walk_tree = self._make_tree(wk, (("ch", "Chapter", 90), ("goal", "Goal", 300), ("status", "Status", 160),
                                              ("guide", "Guide", 200)), row=1, height=8)
        self.walk_tree.bind("<Double-1>", lambda e: self.open_selected_chapter())

        row = ttk.Frame(wk)
        row.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(row, text="Open selected chapter", command=self.open_selected_chapter).pack(side="left")
        ttk.Button(row, text="Full walkthrough (Game8)", command=lambda: webbrowser.open(WALKTHROUGH_URL)).pack(
            side="left", padx=6)
        ttk.Label(row, text="Hidden treasure chest:").pack(side="left", padx=(18, 4))
        self.chest_pick = tk.StringVar(value="1")
        ttk.Spinbox(row, from_=1, to=HIDDEN_TREASURES, textvariable=self.chest_pick, width=5).pack(side="left")
        ttk.Button(row, text="Show location (IGN)", command=self.open_chest).pack(side="left", padx=4)
        ttk.Button(row, text="All hidden treasures", command=lambda: webbrowser.open(TREASURE_URL)).pack(side="left")
        ttk.Label(wk, style="Muted.TLabel", wraplength=820, justify="left", text=(
            "Guides open in your web browser. The walkthrough is by Game8 and the hidden treasure guide is "
            "by IGN. Your current chapter is worked out from the Star Pieces in this save; the hidden "
            f"treasure count comes from the save too (the game doesn't record which of the {HIDDEN_TREASURES} "
            "you've found, only how many).")).grid(row=3, column=0, columnspan=6, sticky="w", pady=(10, 0))
        # Cheats
        ct = ttk.Frame(nb, padding=12)
        nb.add(ct, text="Cheats")
        banner = ttk.Frame(ct, style="Banner.TFrame", padding=10)
        banner.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 8))
        ttk.Label(banner, text="⚠  Experimental: cheats can crash the game or break your save",
                  style="BannerTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(banner, style="Banner.TLabel", wraplength=640, justify="left", text=(
            "A code only works for the exact game version it was made for (its build ID) and may behave "
            "differently between emulators. Back up your save before using cheats, and turn a cheat off "
            "if anything looks wrong.")).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(banner, text="Read the cheat guide", command=self.show_cheat_guide).grid(
            row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))
        banner.columnconfigure(0, weight=1)
        top = ttk.LabelFrame(ct, text="Game & emulator", padding=8)
        top.grid(row=1, column=0, columnspan=6, sticky="ew")
        self.cheat_target = tk.StringVar()
        ttk.Label(top, textvariable=self.cheat_target, wraplength=820, justify="left").grid(
            row=0, column=0, columnspan=5, sticky="w")
        ttk.Label(top, text="Game build ID:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.build_id = tk.StringVar()
        self.build_box = ttk.Combobox(top, textvariable=self.build_id, width=22)
        self.build_box.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        self.build_box.bind("<<ComboboxSelected>>", lambda e: self.load_cheats())
        self.build_box.bind("<FocusOut>", lambda e: self.load_cheats())
        self.build_note = tk.StringVar()
        ttk.Label(top, textvariable=self.build_note, style="Muted.TLabel").grid(row=1, column=2, sticky="w", padx=6, pady=(6, 0))
        ttk.Button(top, text="Detect again", command=self.detect_cheat_target).grid(row=1, column=3, padx=4, pady=(6, 0))

        self.cheat_tree = self._make_tree(ct, (("on", "On", 45), ("name", "Cheat", 260), ("kind", "Type", 95),
                                               ("tested", "Tested on", 200), ("installed", "In emulator", 100)),
                                          row=2, height=6)
        self.cheat_tree.bind("<Double-1>", lambda e: self.toggle_cheats())

        acts = ttk.Frame(ct)
        acts.grid(row=3, column=0, columnspan=6, sticky="w", pady=(8, 0))
        for text, cmd in (("Turn on/off", self.toggle_cheats), ("Add cheat…", self.add_cheat),
                          ("Import cheat file…", self.import_cheats), ("Edit…", self.edit_cheat),
                          ("Delete", self.delete_cheats), ("Select all", lambda: self.cheat_tree.selection_set(
                              self.cheat_tree.get_children())), ("Open cheats folder", self.open_cheat_folder)):
            ttk.Button(acts, text=text, command=cmd).pack(side="left", padx=(0, 4))

        inst = ttk.Frame(ct)
        inst.grid(row=4, column=0, columnspan=6, sticky="w", pady=(8, 0))
        self.primary_button(inst, "Install to emulator", self.install_cheats).pack(side="left")
        ttk.Button(inst, text="Remove from emulator", command=self.uninstall_cheats).pack(side="left", padx=6)
        ttk.Button(inst, text="Export for Switch (SD card)…", command=self.export_cheats).pack(side="left")
        ttk.Button(inst, text="Find cheats online", command=lambda: webbrowser.open(CHEATS_URL)).pack(side="left", padx=6)
        ttk.Label(ct, style="Muted.TLabel", wraplength=820, justify="left", text=(
            "Cheats change the game while it runs. They aren't saved in your save file. Add or import "
            "codes in Atmosphère format ([Cheat name] followed by lines of 8-digit hex codes), turn on the "
            "ones you want, then click Install to emulator and restart the game. Codes only work for "
            "the game version they were made for, so check the build ID. Your cheat list is kept by "
            "this app in its cheats folder, filed by game version, so you can share it or remove cheats from the emulator and install them again later.")).grid(
            row=5, column=0, columnspan=6, sticky="w", pady=(10, 0))
        nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def _make_tree(self, parent, cols, row=0, height=12):
        tree = ttk.Treeview(parent, columns=[c[0] for c in cols], show="headings", height=height)
        for col, txt, w in cols:
            tree.heading(col, text=txt, command=lambda c=col: self.sort_by(tree, c))
            tree.column(col, width=w, anchor="w")
        tree.grid(row=row, column=0, columnspan=6, sticky="nsew", pady=(8, 0) if row else 0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        sb.grid(row=row, column=6, sticky="ns", pady=(8, 0) if row else 0)
        tree.configure(yscrollcommand=sb.set)
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(5, weight=1)
        return tree

    # ---------- folder & slots ----------
    def set_folder(self, folder):
        self.root_dir.set(folder or "")
        if folder:
            self.settings["save_folder"] = folder
            store_settings(self.settings)
        self.refresh_slots()
        self.detect_cheat_target()

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.root_dir.get() or os.path.expanduser("~"),
                                    title="Pick your Super Mario RPG save folder (or any folder above it)")
        if not d:
            return
        found = resolve_save_folder(os.path.normpath(d))
        if not found:
            messagebox.showerror("No save found", f"No Super Mario RPG save files ({SLOT_PREFIX}…) "
                                 "were found in that folder or the folders inside it.")
            return
        self.set_folder(found)

    def redetect(self):
        found = autodetect()
        if found:
            self.set_folder(found)
        else:
            messagebox.showinfo("Not found", "Couldn't find a save automatically. Use Browse… "
                                "to pick the folder that contains your save.")

    def copies(self):
        return save_copies(self.root_dir.get()) if self.root_dir.get() else []

    def refresh_slots(self):
        self.update_backup_count()
        copies = self.copies()
        self.slot_files = []
        if not copies:
            self.slot_box["values"] = []
            self.slot.set("")
            self.data = None
            self.status.set("No save found. Use Browse… to pick your save folder.")
            return
        self.slot_files = sorted(n for n in os.listdir(copies[0])
                                 if n.startswith(SLOT_PREFIX) and n[len(SLOT_PREFIX):].isdigit())
        labels = []
        for n in self.slot_files:
            num = n[len(SLOT_PREFIX):]
            kind = SLOT_NAMES.get(num, f"File {num}")
            try:
                d = load_save(os.path.join(copies[0], n))
                h, m = divmod(d.get("_play_time", 0) // 60, 60)
                labels.append(f"{kind}  —  {n}  —  {d.get('_map_name', '?')}  —  "
                              f"{h}h {m:02d}m  —  saved {' '.join(d.get('_save_date', '').split())}")
            except Exception:
                labels.append(f"{kind}  —  {n}  —  (unreadable)")
        self.slot_box["values"] = labels
        if labels:
            self.slot_box.current(0)
            self.load_slot()

    def slot_file(self):
        i = self.slot_box.current()
        return self.slot_files[i] if 0 <= i < len(self.slot_files) else None

    def load_slot(self):
        name = self.slot_file()
        if not name:
            return
        try:
            self.data = load_save(os.path.join(self.copies()[0], name))
            self.loaded = copy.deepcopy(self.data)
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return
        d = self.data
        for key, (v, _, _) in self.general_vars.items():
            v.set(str(d.get(key, 0)))
        h, m = divmod(d.get("_play_time", 0) // 60, 60)
        self.info.set(f"Location: {d.get('_map_name')}     Chapter: {d.get('_chapter_number')}     "
                      f"Play time: {h}h {m:02d}m     Saved: {d.get('_save_date')}\n"
                      f"Star Pieces: {star_count(d.get('_star_pieces', 0))} / 7   "
                      "(earned from bosses; not editable)")

        self.chars = [dict(p) for p in d["_player_work"]]
        self.orig_chars = [dict(p) for p in d["_player_work"]]
        names = [f"{i}: {p['_name']}" + ("" if self.joined(p) else "  (not joined yet)")
                 for i, p in enumerate(self.chars) if p.get("_name")]
        self.char_box["values"] = names
        self._char_index = None
        if names:
            self.char_box.current(0)
            self.show_char()

        im = d["_item_manager"]
        self.items = ordered_counts(im["_item_list"])
        self.order = list(self.items)
        self.known_recovery = set(ordered_counts(im["_normal_menu_heal_item_list"]))
        self.known_battle = set(ordered_counts(im["_normal_menu_battle_item_list"]))
        self.storage = list(im["_storage_box_list"])
        self.equipment = [i for i in im["_equipment_item_list"] if i]
        self.key_items = [i for i in im["_important_item_list"] if i]
        self.refresh_items(keep=())
        self.refresh_equipment()
        self.refresh_walkthrough()
        self.status.set(f"Loaded {name}. Close the game/emulator before saving.")

    # ---------- characters ----------
    def store_char(self):
        if self._char_index is None:
            return True
        p = self.chars[self._char_index]
        for key, (v, lo, hi) in self.char_vars.items():
            try:
                val = int(v.get())
            except ValueError:
                messagebox.showerror("Invalid value", f"{p['_name']}: '{v.get()}' is not a number.")
                return False
            p[key] = max(lo, min(hi, val))
        p["_hp"] = min(p["_hp"], p["_hp_max"])
        for slot, v in self.gear_vars.items():
            if v.get():
                p[slot] = int(v.get().split()[0])
        return True

    def show_char(self):
        if not self.store_char():
            return
        self._char_index = int(self.char_sel.get().split(":")[0])
        p = self.chars[self._char_index]
        self.max_char_btn.configure(text=f"Max out {p['_name']}")
        cid = p.get("_id", self._char_index)
        for key, (v, _, _) in self.char_vars.items():
            v.set(str(p.get(key, 0)))
        for slot, box in self.gear_boxes.items():
            current = p.get(slot, 0)
            options = [0] + [i for i in EQUIP_IDS if GEAR[i][0] == slot and cid in GEAR[i][1]]
            if current not in options:
                options.append(current)
            box["values"] = [gear_label(i) for i in options]
            self.gear_vars[slot].set(gear_label(current))
        self.update_totals()

    def update_totals(self):
        if self._char_index is None:
            return
        p = dict(self.chars[self._char_index])
        for key, (v, _, _) in self.char_vars.items():
            try:
                p[key] = int(v.get())
            except ValueError:
                pass
        for slot, v in self.gear_vars.items():
            if v.get():
                p[slot] = int(v.get().split()[0])
        t = self.equip_totals(p, self.orig_chars[self._char_index])
        self.totals.set("With equipment:  " + "   ".join(
            f"{n} {t.get('_equip' + k, '?')}" for n, k in zip(("Atk", "Def", "MgAtk", "MgDef", "Spd"), STAT_KEYS)))

    def max_general(self, key=None):
        """Set one General field (or all of them except play time) to its maximum."""
        for k, (v, lo, hi) in self.general_vars.items():
            if (key is None and k != "_play_time") or k == key:
                v.set(str(hi))
        fp_max = self.general_vars["_max_flower_point"][0].get()
        if key in (None, "_current_flower_point"):
            self.general_vars["_current_flower_point"][0].set(fp_max)   # current FP can't exceed max

    def max_character(self, everyone=False):
        """Max out level, EXP, HP and stats for the shown character, or for everyone."""
        if not self.data or not self.store_char():
            return
        targets = [n for n, p in enumerate(self.chars) if p.get("_name")] if everyone else [self._char_index]
        for n in targets:
            for key, _, lo, hi in CHAR_FIELDS:
                self.chars[n][key] = hi
        if self._char_index is not None:
            for key, (v, _, _) in self.char_vars.items():
                v.set(str(self.chars[self._char_index][key]))
            self.update_totals()
        who = "all characters" if everyone else self.chars[targets[0]]["_name"]
        self.status.set(f"Maxed out {who} (not saved yet).")

    @staticmethod
    def gear_stats(p):
        total = [0] * 5
        for slot in (WEAPON, ARMOR, ACCESSORY):
            for n, v in enumerate(GEAR.get(p.get(slot, 0), (None, None, (0,) * 5))[2]):
                total[n] += v
        return total

    def equip_totals(self, p, orig):
        """New stored 'with equipment' values: old value + base-stat change + gear change."""
        new_gear, old_gear = self.gear_stats(p), self.gear_stats(orig)
        out = {}
        for n, stat in enumerate(STAT_KEYS):
            delta = (p[stat] - orig[stat]) + (new_gear[n] - old_gear[n])
            for prefix in ("_equip", "_equip_change"):
                k = prefix + stat
                if k in orig:
                    out[k] = max(0, orig[k] + delta)
        return out

    # ---------- items ----------
    def stored(self, i):
        return self.storage[i] if 0 <= i < len(self.storage) else 0

    def refresh_items(self, keep=None):
        keep = set(self.tree.selection()) if keep is None else {str(i) for i in keep}
        self.tree.delete(*self.tree.get_children())
        if self.show_all_items.get():
            shown = set(CONSUMABLE_RANGE)
        else:
            shown = set(self.items) | {i for i in CONSUMABLE_RANGE if self.stored(i)}
        for i in sorted(shown):
            self.tree.insert("", "end", iid=str(i),
                             values=(i, item_name(i), self.menu_label(i), self.items.get(i, 0), self.stored(i)))
        self.tree.selection_set([k for k in keep if self.tree.exists(k)])
        self.apply_sort(self.tree)
        self.on_item_select(None)
        self.update_bag_count()

    def bag_capacity(self):
        """The save keeps one slot per carried item in a fixed-size list (1,200 in this game)."""
        return len(self.data["_item_manager"]["_item_list"]) if self.data else 1200

    def update_bag_count(self):
        used, cap = sum(self.items.values()), self.bag_capacity()
        over = used > cap
        self.bag_count.set(f"{used:,} / {cap:,} items" +
                           (f"   ·   {used - cap:,} too many to save" if over else f"   ·   {cap - used:,} free"))
        self.bag_label.configure(style="Alert.TLabel" if over else "Muted.TLabel")
        self.bag_bar.configure(maximum=cap, value=min(used, cap),
                               style="Over.Horizontal.TProgressbar" if over else "Horizontal.TProgressbar")

    def recovery(self, i):
        """Which menu an item is in: as the game filed it in this save, else the default."""
        if i in self.known_recovery:
            return True
        if i in self.known_battle:
            return False
        return is_recovery(i)

    def menu_label(self, i):
        if i in FIELD_ONLY:
            return "Recovery (menu only)"
        return "Recovery" if self.recovery(i) else "Battle"

    def item_order(self):
        """Owned items in the game's own order (as stored in the save). New items go right
        after the item with the next-lower ID; the game re-sorts them when it next saves."""
        order = [i for i in self.order if i in self.items]
        for i in sorted(set(self.items) - set(order)):
            pos = max((n + 1 for n, j in enumerate(order) if j < i), default=0)
            order.insert(pos, i)
        return order

    def on_item_select(self, _):
        sel = self.tree.selection()
        self.sel_count.set(f"{len(sel)} selected")
        if len(sel) == 1:
            self.show_item(int(sel[0]))

    def select_all_items(self):
        self.tree.selection_set(self.tree.get_children())

    def bulk_set(self, what):
        sel = [int(s) for s in self.tree.selection()]
        if not sel:
            messagebox.showinfo("Nothing selected", "Select one or more items first "
                                "(Ctrl/Shift-click, or Select all).")
            return
        limit = CARRY_MAX if what == "carried" else STORAGE_MAX
        try:
            n = max(0, min(limit, int((self.bulk_qty if what == "carried" else self.bulk_box).get())))
        except ValueError:
            messagebox.showerror("Invalid", "The amount must be a number.")
            return
        for i in sel:
            if what == "carried":
                if n:
                    self.items[i] = n
                else:
                    self.items.pop(i, None)
            elif i < len(self.storage):
                self.storage[i] = n
        self.refresh_items(keep=sel)
        label = "carried" if what == "carried" else "in the Storage Box"
        self.status.set(f"Set {len(sel)} item{'s' if len(sel) != 1 else ''} to {n} {label} (not saved yet).")

    def on_pick(self, _):
        self.show_item(int(self.item_pick.get().split()[0]))

    def show_item(self, i):
        self.item_pick.set(item_label(i))
        self.item_qty.set(str(self.items.get(i, 0)))
        self.item_box.set(str(self.stored(i)))

    def set_item(self):
        if not self.item_pick.get():
            messagebox.showerror("Pick an item", "Choose an item first.")
            return
        i = int(self.item_pick.get().split()[0])
        try:
            q = max(0, min(CARRY_MAX, int(self.item_qty.get())))
            s = max(0, min(STORAGE_MAX, int(self.item_box.get())))
        except ValueError:
            messagebox.showerror("Invalid", "Quantities must be numbers.")
            return
        if q:
            self.items[i] = q
        else:
            self.items.pop(i, None)
        if i < len(self.storage):
            self.storage[i] = s
        self.refresh_items()
        if str(i) in self.tree.get_children():
            self.tree.selection_set(str(i))
            self.tree.see(str(i))
        self.show_item(i)

    def max_items(self):
        for i in self.items:
            self.items[i] = CARRY_MAX
        self.refresh_items()

    # ---------- equipment bag ----------
    def joined(self, p):
        return p.get("_id") in self.data.get("_party_order", [])

    def worn_gear(self):
        """(character index, item) pairs that must be in the bag: gear worn by party members,
        plus gear changed in this editor. Characters who haven't joined yet have starting
        gear that the bag doesn't contain."""
        pairs = []
        for n, (p, orig) in enumerate(zip(self.chars, self.orig_chars)):
            for slot in (WEAPON, ARMOR, ACCESSORY):
                i = p.get(slot, 0)
                if i and (self.joined(p) or i != orig.get(slot, 0)):
                    pairs.append((n, i))
        return pairs

    def equipped_ids(self):
        return [i for _, i in self.worn_gear()]

    def char_label(self, n):
        p = self.chars[n]
        return p["_name"] + ("" if self.joined(p) else " (not joined yet)")

    def can_wear(self, i):
        """Indexes of characters who can equip item i."""
        allowed = GEAR.get(i, (None, ()))[1]
        return [n for n, p in enumerate(self.chars) if p.get("_name") and p.get("_id", n) in allowed]

    def on_tab_changed(self, _):
        tab = self.nb.tab(self.nb.select(), "text")
        if self.data and tab.startswith("Equipment"):
            self.store_char()          # pick up gear changed on the Characters tab
            self.refresh_equipment()
        if tab == "Cheats" and not self.settings.get("cheats_warning_seen"):
            self.after(50, self.cheat_notice)

    def cheat_notice(self):
        """Shown once, the first time someone opens the Cheats tab."""
        win = tk.Toplevel(self)
        win.title("Cheats are experimental")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        body = ttk.Frame(win, padding=16)
        body.pack(fill="both")
        ttk.Label(body, text="⚠  Cheats are experimental", style="Warn.TLabel").pack(anchor="w")
        ttk.Label(body, wraplength=460, justify="left", text=(
            "Cheats change the game while it runs. A code made for a different game version, or one "
            "that doesn't suit your emulator, can do nothing, crash the game, or corrupt your save.\n\n"
            "• Back up your save first (Back up now… at the top).\n"
            "• Only use codes made for your game's build ID.\n"
            "• Turn a cheat off and restore a backup if anything goes wrong.")).pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(win, padding=(16, 0, 16, 16))
        row.pack(fill="x")

        def done():
            self.settings["cheats_warning_seen"] = True
            store_settings(self.settings)
            win.destroy()

        self.primary_button(row, "I understand", done).pack(side="right")
        ttk.Button(row, text="Read the cheat guide", command=lambda: (done(), self.show_cheat_guide())).pack(
            side="right", padx=6)
        win.protocol("WM_DELETE_WINDOW", done)
        self.center(win)

    def show_cheat_guide(self):
        win = tk.Toplevel(self)
        win.title("Cheat guide")
        win.geometry("720x600")
        win.transient(self)
        frame = ttk.Frame(win, padding=(12, 12, 12, 0))
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", font=("Segoe UI", 10), padx=12, pady=10, relief="flat")
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("h", font=("Segoe UI", 12, "bold"), spacing1=12, spacing3=4)
        text.tag_configure("warn", font=("Segoe UI", 10, "bold"), foreground=self.palette["warn"])
        for kind, line in CHEAT_GUIDE:
            text.insert("end", line + "\n", kind)
        text.configure(state="disabled")
        row = ttk.Frame(win, padding=12)
        row.pack(fill="x")
        ttk.Button(row, text="Close", command=win.destroy).pack(side="right")
        ttk.Button(row, text="Full guide online", command=lambda: webbrowser.open(CHEAT_GUIDE_URL)).pack(
            side="right", padx=6)
        self.center(win)

    def max_owned(self, i):
        """1 of each key item and character-only gear; up to SHARED_MAX of gear anyone wears."""
        if i in GEAR and len(GEAR[i][1]) == len(ALL):
            return SHARED_MAX
        return 1

    def owned(self, i):
        return (1 if i in self.key_items else 0) if i in KEY_IDS else self.equipment.count(i)

    def refresh_equipment(self, keep=None):
        keep = set(self.eq_tree.selection()) if keep is None else {str(i) for i in keep}
        self.eq_tree.delete(*self.eq_tree.get_children())
        wearers = {}
        for n, i in self.worn_gear():
            wearers.setdefault(i, []).append(self.chars[n]["_name"])
        names = {1: "Mario", 2: "Mallow", 3: "Geno", 4: "Bowser", 5: "Peach"}
        everything = self.show_all_gear.get()
        for i in EQUIP_IDS + KEY_IDS:
            have = self.owned(i)
            if not (everything or have or i in wearers):
                continue
            if i in KEY_IDS:
                kind, who, tag = "Key item", "—", "key"
            else:
                slot, allowed, _ = GEAR[i]
                kind = SLOT_LABELS[slot]
                who = "Everyone" if len(allowed) == len(ALL) else ", ".join(names[c] for c in allowed)
                tag = "worn" if i in wearers else "" if have else "none"
            self.eq_tree.insert("", "end", iid=str(i), tags=(tag,) if tag else (),
                                values=(i, item_name(i), kind, who, f"{have} / {self.max_owned(i)}",
                                        ", ".join(wearers.get(i, [])) or "—"))
        self.eq_tree.selection_set([k for k in keep if self.eq_tree.exists(k)])
        self.apply_sort(self.eq_tree)
        self.on_equipment_select(None)

    def on_equipment_select(self, _):
        sel = self.eq_tree.selection()
        self.eq_count.set(f"{len(sel)} selected")
        self.equip_on_box["values"] = []
        self.unequip_box["values"] = []
        self.equip_on.set("")
        self.unequip_from.set("")
        if len(sel) != 1:
            self.eq_selected.set("Pick one row to equip or unequip it.")
            return
        i = int(sel[0])
        if i in KEY_IDS:
            self.eq_selected.set(f"{item_name(i)}  (key item)")
            return
        slot = GEAR[i][0]
        worn_by = [n for n, j in self.worn_gear() if j == i]
        spare = max(0, self.owned(i) - len(worn_by))
        self.eq_selected.set(f"{item_name(i)}  ({spare} spare)")
        options = [f"{n}: {self.char_label(n)}" for n in self.can_wear(i) if self.chars[n].get(slot) != i]
        self.equip_on_box["values"] = options
        self.equip_on.set(options[0] if options else "")
        wearing = [f"{n}: {self.chars[n]['_name']}" for n in worn_by]
        self.unequip_box["values"] = wearing
        self.unequip_from.set(wearing[0] if wearing else "")

    def set_gear(self, n, slot, item):
        """Change one character's gear, keeping the bag and the Characters tab in sync."""
        p, orig = self.chars[n], self.orig_chars[n]
        old = p.get(slot, 0)
        # Starting gear of a character who hasn't joined isn't in the bag; keep it when removed.
        if (old and not self.joined(p) and old == orig.get(slot, 0)
                and self.owned(old) < self.max_owned(old)):
            self.equipment.append(old)
        p[slot] = item
        if n == self._char_index:
            self.gear_vars[slot].set(gear_label(item))
            self.update_totals()

    def equip_selected(self):
        self.store_char()
        sel = self.eq_tree.selection()
        if len(sel) != 1 or not self.equip_on.get():
            messagebox.showinfo("Equip", "Pick one piece of equipment and a character to equip it on.")
            return
        i, n = int(sel[0]), int(self.equip_on.get().split(":")[0])
        slot = GEAR[i][0]
        worn_by = [w for w, j in self.worn_gear() if j == i]
        if self.owned(i) - len(worn_by) <= 0:
            if self.owned(i) < self.max_owned(i):
                self.equipment.append(i)            # none spare: add a copy, within the limit
            else:
                w = worn_by[0]
                if not messagebox.askyesno(
                        "Take it from someone?",
                        f"You already own the most {item_name(i)} allowed ({self.max_owned(i)}), and "
                        f"{self.chars[w]['_name']} is wearing one. Move it to {self.chars[n]['_name']}?"):
                    return
                self.set_gear(w, slot, 0)
        self.set_gear(n, slot, i)
        self.refresh_equipment(keep=[i])
        self.status.set(f"{self.chars[n]['_name']} now has {item_name(i)} equipped (not saved yet).")

    def unequip_selected(self):
        self.store_char()
        sel = self.eq_tree.selection()
        if len(sel) != 1 or not self.unequip_from.get():
            messagebox.showinfo("Unequip", "Pick one item that someone is wearing.")
            return
        i, n = int(sel[0]), int(self.unequip_from.get().split(":")[0])
        self.set_gear(n, GEAR[i][0], 0)
        self.refresh_equipment(keep=[i])
        self.status.set(f"Unequipped {item_name(i)} from {self.chars[n]['_name']} (not saved yet).")

    def set_owned(self, i, n):
        """Set how many of an item you own, within its limit and never below the number worn.
        Returns the number actually set."""
        n = max(0, min(self.max_owned(i), n))
        if i in KEY_IDS:
            if n and i not in self.key_items:
                self.key_items.append(i)
            elif not n and i in self.key_items:
                self.key_items.remove(i)
            return n
        n = max(n, self.equipped_ids().count(i))
        while self.equipment.count(i) < n:
            self.equipment.append(i)
        while self.equipment.count(i) > n:     # drop the last copies first
            del self.equipment[len(self.equipment) - 1 - self.equipment[::-1].index(i)]
        return n

    def bulk_owned(self, maximum=False):
        self.store_char()
        sel = [int(s) for s in self.eq_tree.selection()]
        if not sel:
            messagebox.showinfo("Nothing selected", "Select one or more rows first "
                                "(Ctrl/Shift-click, or Select all).")
            return
        try:
            want = None if maximum else int(self.eq_qty.get())
        except ValueError:
            messagebox.showerror("Invalid", "The amount must be a number.")
            return
        key_target = 1 if maximum else min(1, max(0, want))
        if not self._key_warned and any(i in KEY_IDS and self.owned(i) != key_target for i in sel):
            if messagebox.askyesno("Change key items?", "Key items are tied to story progress. "
                                   "Adding one early or removing one you still need can block the "
                                   "story. Change key items anyway?"):
                self._key_warned = True
            else:
                sel = [i for i in sel if i not in KEY_IDS]
        limited = []
        for i in sel:
            target = self.max_owned(i) if maximum else want
            got = self.set_owned(i, target)
            if got != target:
                limited.append(f"{item_name(i)}: {got}")
        self.refresh_equipment(keep=sel)
        self.status.set(f"Updated {len(sel)} item{'s' if len(sel) != 1 else ''} (not saved yet).")
        if limited and not maximum:
            messagebox.showinfo("Limits applied", "Some items were set to their limit, or to the "
                                "number being worn:\n\n" + "\n".join(limited[:15]) +
                                ("\n…" if len(limited) > 15 else ""))

    # ---------- themes ----------
    def theme_mode(self):
        mode = self.settings.get("theme", "System")
        if mode == "System":
            return "dark" if system_prefers_dark() else "light"
        return mode.lower()

    def on_theme_pick(self, _=None):
        self.settings["theme"] = self.theme_choice.get()
        store_settings(self.settings)
        self.apply_theme()

    def apply_theme(self):
        mode = self.theme_mode()
        p = self.palette = PALETTES[mode]
        style = self.style
        if mode == "dark":
            style.theme_use("clam")
            style.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                            bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"],
                            troughcolor=p["bg"], selectbackground=p["select"], selectforeground=p["fg"],
                            insertcolor=p["fg"], focuscolor=p["accent"])
            style.map(".", foreground=[("disabled", p["faint"])])
            style.configure("TButton", background=p["surface"], foreground=p["fg"], padding=(8, 3),
                            bordercolor=p["border"])
            style.map("TButton", background=[("pressed", p["border"]), ("active", p["hover"])])
            for w in ("TEntry", "TCombobox", "TSpinbox"):
                style.configure(w, fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"],
                                background=p["surface"], bordercolor=p["border"])
                style.map(w, fieldbackground=[("readonly", p["field"]), ("disabled", p["bg"])],
                          foreground=[("readonly", p["fg"])], background=[("active", p["hover"])],
                          selectbackground=[("readonly", p["field"])], selectforeground=[("readonly", p["fg"])])
            style.configure("TCheckbutton", background=p["bg"], foreground=p["fg"], indicatorbackground=p["field"])
            style.map("TCheckbutton", background=[("active", p["bg"])],
                      indicatorbackground=[("selected", p["accent"]), ("active", p["hover"])])
            style.configure("TLabelframe", background=p["bg"], bordercolor=p["border"])
            style.configure("TLabelframe.Label", background=p["bg"], foreground=p["muted"])
            style.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
            style.configure("TNotebook.Tab", background=p["surface"], foreground=p["muted"], bordercolor=p["border"])
            style.map("TNotebook.Tab", background=[("selected", p["bg"]), ("active", p["hover"])])
            style.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                            bordercolor=p["border"], rowheight=22)
            style.configure("Treeview.Heading", background=p["surface"], foreground=p["fg"], bordercolor=p["border"],
                            relief="flat")
            style.map("Treeview.Heading", background=[("active", p["hover"])])
            style.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", "#ffffff")])
            style.configure("Vertical.TScrollbar", background=p["hover"], troughcolor=p["bg"], gripcount=0,
                            lightcolor=p["hover"], darkcolor=p["hover"], arrowcolor=p["fg"], bordercolor=p["bg"])
            style.map("Vertical.TScrollbar", background=[("active", p["border"])])
            style.configure("Horizontal.TProgressbar", background=p["tag_on"], troughcolor=p["field"],
                            bordercolor=p["border"], lightcolor=p["tag_on"], darkcolor=p["tag_on"])
        else:
            style.theme_use(self.base_theme)
        self._style_common()
        # Plain tk widgets don't follow ttk styles: set them directly, now and for new ones.
        for opt, value in (("*TCombobox*Listbox.background", p["field"]), ("*TCombobox*Listbox.foreground", p["fg"]),
                           ("*TCombobox*Listbox.selectBackground", p["select"]),
                           ("*TCombobox*Listbox.selectForeground", "#ffffff")):
            self.option_add(opt, value)
        self.configure(bg=p["bg"])
        self._recolor(self)
        for tree, tags in ((self.eq_tree, ("worn", "key", "none")), (self.cheat_tree, ("on", "off"))):
            for tag in tags:
                tree.tag_configure(tag, foreground=p["tag_" + tag])
        self.walk_tree.tag_configure("on", foreground=p["tag_on"])
        self.walk_tree.tag_configure("off", foreground=p["faint"])
        self.theme_window(self)

    def _style_common(self):
        p, style = self.palette, self.style
        font = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        style.configure("TNotebook", tabmargins=(6, 8, 6, 0))
        style.configure("TNotebook.Tab", padding=(20, 8), font=(font, 11))
        style.map("TNotebook.Tab", font=[("selected", (font, 11, "bold"))],
                  foreground=[("selected", p["accent"]), ("active", p["accent"])],
                  expand=[("selected", (2, 4, 2, 0))])
        style.configure("Muted.TLabel", foreground=p["muted"])
        style.configure("Faint.TLabel", foreground=p["faint"])
        style.configure("Warn.TLabel", foreground=p["warn"], font=(font, 12, "bold"))
        style.configure("Alert.TLabel", foreground=p["warn"], font=(font, 9, "bold"))
        style.configure("Over.Horizontal.TProgressbar", background=p["warn"], lightcolor=p["warn"],
                        darkcolor=p["warn"])
        style.configure("Banner.TFrame", background=p["banner"])
        style.configure("Banner.TLabel", background=p["banner"], foreground=p["fg"])
        style.configure("BannerTitle.TLabel", background=p["banner"], foreground=p["warn"], font=(font, 11, "bold"))

    def _recolor(self, widget):
        p = self.palette
        for w in widget.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.configure(bg=p["bg"])
            elif isinstance(w, (tk.Text, tk.Listbox)):
                w.configure(bg=p["field"], fg=p["fg"], selectbackground=p["select"], selectforeground="#ffffff",
                            highlightbackground=p["border"], highlightcolor=p["accent"])
                if isinstance(w, tk.Text):
                    w.configure(insertbackground=p["fg"])
            self._recolor(w)

    def theme_window(self, win):
        """Color a window to match the theme, including the Windows title bar."""
        p = self.palette
        if win is not self:
            win.configure(bg=p["bg"])
            self._recolor(win)
        if sys.platform != "win32":
            return
        try:
            import ctypes
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
            value = ctypes.c_int(1 if self.theme_mode() == "dark" else 0)
            for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 11 / older Windows 10)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), 4) == 0:
                    break
            # Redraw the frame so the title bar changes right away.
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
        except Exception:
            pass

    # ---------- walkthrough ----------
    def current_chapter(self):
        """Index into CHAPTERS of the chapter you're on: one past the Star Pieces you have."""
        stars = star_count(self.data.get("_star_pieces", 0)) if self.data else 0
        return min(stars, len(CHAPTERS) - 1)

    def refresh_walkthrough(self):
        self.walk_tree.delete(*self.walk_tree.get_children())
        if not self.data:
            self.walk_now.set("Load a save to see your progress.")
            return
        stars = star_count(self.data.get("_star_pieces", 0))
        now = self.current_chapter()
        found = self.data.get("_hidden_treasure_counter", 0)
        title = CHAPTERS[now][0]
        self.walk_now.set(f"You're on {title}: {CHAPTERS[now][1]}" if now < 7 else
                          "All 7 Star Pieces collected! Next: the post-game content.")
        self.star_bar["value"] = stars
        self.star_text.set(f"{stars} / 7")
        self.treasure_bar["value"] = min(found, HIDDEN_TREASURES)
        self.treasure_text.set(f"{found} / {HIDDEN_TREASURES} found")
        for n, (ch, goal, _) in enumerate(CHAPTERS):
            status = "✔ Done" if n < now else "▶ You are here" if n == now else "Upcoming"
            self.walk_tree.insert("", "end", iid=str(n), tags=("on",) if n == now else ("off",) if n > now else (),
                                  values=(ch, goal, status, "Game8 · double-click to open"))
        self.walk_tree.tag_configure("on", foreground=self.palette["tag_on"])
        self.walk_tree.tag_configure("off", foreground=self.palette["faint"])
        self.walk_tree.selection_set(str(now))
        self.walk_tree.see(str(now))
        self.apply_sort(self.walk_tree)

    def open_current_chapter(self):
        webbrowser.open(CHAPTERS[self.current_chapter()][2])

    def open_selected_chapter(self):
        sel = self.walk_tree.selection()
        if sel:
            webbrowser.open(CHAPTERS[int(sel[0])][2])

    def open_chest(self):
        try:
            n = max(1, min(HIDDEN_TREASURES, int(self.chest_pick.get())))
        except ValueError:
            n = 1
        webbrowser.open(f"{TREASURE_URL}#Hidden_Treasure_Chest_{n}")

    # ---------- sorting ----------
    def sort_by(self, tree, col):
        """Click a column heading to sort by it; click again to reverse."""
        current, reverse = self._sort.get(tree, (None, False))
        self._sort[tree] = (col, not reverse if current == col else False)
        self.apply_sort(tree)

    def apply_sort(self, tree):
        if tree not in self._sort:
            return
        col, reverse = self._sort[tree]

        def key(iid):
            value = str(tree.set(iid, col))
            number = re.match(r"-?\d+", value)
            if number:
                return (0, int(number.group()), value.lower())
            return (1 if value not in ("", "—") else 2, 0, value.lower())

        rows = sorted(tree.get_children(), key=key, reverse=reverse)
        if reverse:   # keep empty values last either way
            rows = [r for r in rows if key(r)[0] != 2] + [r for r in rows if key(r)[0] == 2]
        for n, iid in enumerate(rows):
            tree.move(iid, "", n)
        for c in tree["columns"]:
            text = tree.heading(c, "text").rstrip(" ▲▼")
            tree.heading(c, text=text + ((" ▼" if reverse else " ▲") if c == col else ""))

    # ---------- cheats ----------
    def load_cheat_library(self):
        """Move cheats saved by older versions (one cheats.json in the settings folder) into the
        per-build library folders."""
        old = os.path.join(os.path.dirname(SETTINGS_PATH), "cheats.json")
        if not os.path.exists(old):
            return
        try:
            data = json.load(open(old, encoding="utf-8"))
            for bid, cheats in data.items():
                have = {c["name"]: c for c in read_library(bid)}
                for c in cheats:
                    have.setdefault(c["name"], dict(c, description="",
                                                    tested={t: "Untested" for t in TEST_TARGETS}))
                write_library(bid, list(have.values()))
                on = self.settings.setdefault("cheats_on", {}).setdefault(bid, [])
                on.extend(c["name"] for c in cheats if c.get("on") and c["name"] not in on)
            store_settings(self.settings)
            os.replace(old, old + ".migrated")
        except (OSError, ValueError, KeyError):
            pass

    def store_cheat_library(self):
        bid = self.current_build()
        if not bid:
            return
        try:
            write_library(bid, self.cheats)
        except OSError as e:
            messagebox.showerror("Couldn't save cheats", str(e))
            return
        self.settings.setdefault("cheats_on", {})[bid] = [c["name"] for c in self.cheats if c.get("on")]
        store_settings(self.settings)

    def current_build(self):
        bid = self.build_id.get().strip().upper()
        return bid if re.fullmatch(r"[0-9A-F]{16}", bid) else ""

    def detect_cheat_target(self):
        ensure_known_folders()
        self.emulator = emulator_for(self.root_dir.get())
        found = detect_build_ids(self.emulator)
        known = [b for b in found if b in KNOWN_BUILDS] + [b for b in found if b not in KNOWN_BUILDS]
        stored = [b for b in library_builds() if b not in known]
        self.build_box["values"] = known + stored
        if known:
            self.build_id.set(known[0])
        elif not self.current_build() and stored:
            self.build_id.set(stored[0])
        if self.emulator:
            self.cheat_target.set(f"Emulator: {self.emulator['name']}   ·   cheats go in:\n"
                                  f"{self.emulator['cheat_dir']}")
        else:
            self.cheat_target.set("This save isn't inside an emulator folder (for example, a save dumped "
                                  "from a Switch). Use Export for Switch (SD card) to install cheats with "
                                  "Atmosphère.")
        self.load_cheats()

    def load_cheats(self):
        bid = self.current_build()
        self.cheats = read_library(bid) if bid else []
        on = set(self.settings.get("cheats_on", {}).get(bid, []))
        for c in self.cheats:
            c["on"] = c["name"] in on
        if not bid:
            self.build_note.set("Enter the 16-character build ID (Ryujinx: right-click the game → Manage Cheats).")
        elif bid in KNOWN_BUILDS:
            self.build_note.set(f"Super Mario RPG {KNOWN_BUILDS[bid]}, found in your emulator's log")
        elif bid in (self.build_box["values"] or ()):
            self.build_note.set("Found in your emulator's log or your cheat library")
        else:
            self.build_note.set("Entered by hand")
        self.refresh_cheats()

    def installed_names(self):
        bid, emu = self.current_build(), self.emulator
        if not bid or not emu:
            return set()
        path = os.path.join(emu["cheat_dir"], bid + ".txt")
        try:
            return {c["name"] for c in parse_cheats(open(path, encoding="utf-8").read())}
        except (OSError, ValueError):
            return set()

    def refresh_cheats(self, keep=None):
        keep = set(self.cheat_tree.selection()) if keep is None else {str(k) for k in keep}
        self.cheat_tree.delete(*self.cheat_tree.get_children())
        installed = self.installed_names()
        short = {"Ryujinx": "Ryujinx", "yuzu family": "yuzu", "Switch": "Switch"}
        for n, c in enumerate(self.cheats):
            marks = {"Untested": "?", "Works": "✓", "Doesn't work": "✗"}      # plain symbols draw cleanly in Tk
            tested = " · ".join(f"{short[t]} {marks[c.get('tested', {}).get(t, 'Untested')]}" for t in TEST_TARGETS)
            self.cheat_tree.insert("", "end", iid=str(n), tags=("on" if c.get("on") else "off",), values=(
                "✔" if c.get("on") else "", c["name"], "Master code" if c.get("master") else "Cheat",
                tested, "Installed" if c["name"] in installed else "—"))
        self.cheat_tree.selection_set([k for k in keep if self.cheat_tree.exists(k)])
        self.apply_sort(self.cheat_tree)

    def open_cheat_folder(self):
        if self.need_build():
            return
        folder = build_folder(self.current_build())
        os.makedirs(folder, exist_ok=True)
        open_folder(folder)

    def selected_cheats(self):
        return sorted(int(s) for s in self.cheat_tree.selection())

    def need_build(self):
        if self.current_build():
            return False
        messagebox.showinfo("Build ID needed", "Enter your game's 16-character build ID first. Cheats only "
                            "work for the exact game version they were made for.\n\nRyujinx shows it at the "
                            "top of the Manage Cheats window (right-click the game).")
        return True

    def toggle_cheats(self):
        sel = self.selected_cheats()
        if not sel:
            return
        turn_on = not all(self.cheats[n].get("on") for n in sel)
        for n in sel:
            self.cheats[n]["on"] = turn_on
        self.store_cheat_library()
        self.refresh_cheats(keep=sel)
        self.status.set(f"Turned {'on' if turn_on else 'off'} {len(sel)} cheat{'s' if len(sel) != 1 else ''}. "
                        "Click Install to emulator to apply.")

    def add_cheats(self, new, source):
        names = {c["name"]: n for n, c in enumerate(self.cheats)}
        replaced = [c["name"] for c in new if c["name"] in names]
        if replaced and not messagebox.askyesno("Replace cheats?", "You already have cheats with these "
                                                "names:\n\n" + "\n".join(replaced[:12]) + "\n\nReplace them?"):
            new = [c for c in new if c["name"] not in names]
        for c in new:
            c.setdefault("on", False)
            c.setdefault("description", "")
            c.setdefault("tested", {t: "Untested" for t in TEST_TARGETS})
            if c["name"] in names:
                self.cheats[names[c["name"]]] = c
            else:
                self.cheats.append(c)
        self.store_cheat_library()
        self.refresh_cheats()
        self.status.set(f"Added {len(new)} cheat{'s' if len(new) != 1 else ''} from {source}. Turn on the "
                        "ones you want, then Install to emulator.")

    def import_cheats(self):
        if self.need_build():
            return
        path = filedialog.askopenfilename(title="Import an Atmosphère cheat file",
                                          filetypes=[("Cheat files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            new = parse_cheats(open(path, encoding="utf-8-sig", errors="replace").read())
        except (OSError, ValueError) as e:
            messagebox.showerror("Can't import", str(e))
            return
        if not new:
            messagebox.showinfo("No cheats", "That file doesn't contain any cheats.")
            return
        stem = os.path.splitext(os.path.basename(path))[0].upper()
        if re.fullmatch(r"[0-9A-F]{16}", stem) and stem != self.current_build():
            if not messagebox.askyesno("Different game version?", f"This file is named for build ID {stem}, "
                                       f"but the build ID selected is {self.current_build()}. Cheats for a "
                                       "different version usually don't work. Import anyway?"):
                return
        # A library folder carries descriptions and test results next to the cheat file.
        info = os.path.join(os.path.dirname(path), "info.json")
        if os.path.exists(info):
            try:
                details = {c["name"]: c for c in json.load(open(info, encoding="utf-8")).get("cheats", [])}
                for c in new:
                    d = details.get(c["name"], {})
                    c["description"] = d.get("description", "")
                    c["tested"] = {t: d.get("tested", {}).get(t, "Untested") for t in TEST_TARGETS}
            except (OSError, ValueError, KeyError):
                pass
        self.add_cheats(new, os.path.basename(path))

    def cheat_dialog(self, cheat=None):
        """Add/edit dialog. Returns the new cheat dict, or None if cancelled."""
        win = tk.Toplevel(self)
        win.title("Edit cheat" if cheat else "Add cheat")
        win.geometry("600x600")
        win.transient(self)
        win.grab_set()
        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)
        cheat = cheat or {}
        fields = {}
        for key, label in (("name", "Name"), ("description", "What it does")):
            ttk.Label(body, text=label).pack(anchor="w", pady=(6, 0) if key != "name" else 0)
            fields[key] = tk.StringVar(value=cheat.get(key, ""))
            ttk.Entry(body, textvariable=fields[key], width=70).pack(anchor="w", fill="x")
        master = tk.BooleanVar(value=bool(cheat.get("master")))
        ttk.Checkbutton(body, text="Master code (needed by some cheats; always on)", variable=master).pack(
            anchor="w", pady=(8, 0))
        tested_box = ttk.LabelFrame(body, text="Tested on", padding=6)
        tested_box.pack(fill="x", pady=(8, 0))
        tested = {}
        for col, target in enumerate(TEST_TARGETS):
            ttk.Label(tested_box, text=target).grid(row=0, column=col * 2, sticky="w", padx=(0 if col == 0 else 14, 4))
            tested[target] = tk.StringVar(value=cheat.get("tested", {}).get(target, "Untested"))
            ttk.Combobox(tested_box, textvariable=tested[target], values=TEST_STATES, state="readonly",
                         width=12).grid(row=0, column=col * 2 + 1)
        ttk.Label(body, text="Code (one instruction per line, 8-digit hex groups)").pack(anchor="w", pady=(8, 0))
        code = tk.Text(body, height=10, font=("Consolas", 10), wrap="none")
        code.pack(fill="both", expand=True)
        if cheat.get("lines"):
            code.insert("1.0", "\n".join(cheat["lines"]))
        result = {}

        def ok():
            label = fields["name"].get().strip()
            if not label or any(ch in label for ch in "[]{}"):
                messagebox.showerror("Name needed", "Give the cheat a name (without [ ] or { }).", parent=win)
                return
            try:
                parsed = parse_cheats(f"[{label}]\n" + code.get("1.0", "end"))
            except ValueError as e:
                messagebox.showerror("Invalid code", str(e).replace("Line ", "Code line ", 1), parent=win)
                return
            result["cheat"] = {"name": label, "lines": parsed[0]["lines"], "master": master.get(),
                               "description": fields["description"].get().strip(),
                               "tested": {t: v.get() for t, v in tested.items()},
                               "on": bool(cheat.get("on")) if cheat else master.get()}
            win.destroy()

        row = ttk.Frame(win, padding=(12, 0, 12, 12))
        row.pack(fill="x")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="right")
        self.primary_button(row, "Save cheat", ok).pack(side="right", padx=6)
        self.center(win)
        self.wait_window(win)
        return result.get("cheat")

    def add_cheat(self):
        if self.need_build():
            return
        c = self.cheat_dialog()
        if c:
            self.add_cheats([c], "the editor")

    def edit_cheat(self):
        sel = self.selected_cheats()
        if len(sel) != 1:
            messagebox.showinfo("Edit", "Pick one cheat to edit.")
            return
        c = self.cheat_dialog(self.cheats[sel[0]])
        if c:
            self.cheats[sel[0]] = c
            self.store_cheat_library()
            self.refresh_cheats(keep=sel)

    def delete_cheats(self):
        sel = self.selected_cheats()
        if not sel or not messagebox.askyesno("Delete cheats", f"Delete {len(sel)} cheat"
                                              f"{'s' if len(sel) != 1 else ''} from your library?"):
            return
        self.cheats = [c for n, c in enumerate(self.cheats) if n not in sel]
        self.store_cheat_library()
        self.refresh_cheats(keep=())

    def write_enabled_file(self, bid, on_names):
        """Ryujinx turns cheats on from enabled.txt ("BUILDID-<Name Cheat>" per line). Keep any
        lines that aren't ours."""
        path = self.emulator.get("enabled_file")
        if not path:
            return
        ours = {f"{bid}-<{c['name']} Cheat>" for c in self.cheats}
        try:
            lines = [l.strip() for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
        except OSError:
            lines = []
        lines = [l for l in lines if l not in ours] + [f"{bid}-<{n} Cheat>" for n in on_names]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

    def install_cheats(self):
        if self.need_build():
            return
        if not self.emulator:
            messagebox.showinfo("No emulator", "This save isn't inside an emulator folder. Use Export for "
                                "Switch (SD card) instead.")
            return
        bid = self.current_build()
        on = [c for c in self.cheats if c.get("on")]
        path = os.path.join(self.emulator["cheat_dir"], bid + ".txt")
        try:
            if on:
                os.makedirs(self.emulator["cheat_dir"], exist_ok=True)
                # Ryujinx and the yuzu family read [Name] sections; master codes are just cheats there.
                text = format_cheats([dict(c, master=False) for c in on])
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            elif os.path.exists(path):
                os.remove(path)
            self.write_enabled_file(bid, [c["name"] for c in on])
        except OSError as e:
            messagebox.showerror("Install failed", str(e))
            return
        self.refresh_cheats()
        extra = ("" if self.emulator["enabled_file"] else "\n\nIn your emulator, make sure the "
                 f"'{CHEAT_MOD_NAME}' add-on is enabled for Super Mario RPG.")
        messagebox.showinfo("Cheats installed", f"{len(on)} cheat{'s' if len(on) != 1 else ''} installed "
                            f"for {self.emulator['name']}.\n\nRestart the game for the changes to take "
                            f"effect.{extra}")
        self.status.set(f"Installed {len(on)} cheats to {self.emulator['cheat_dir']}")

    def uninstall_cheats(self):
        if not self.emulator or self.need_build():
            return
        bid = self.current_build()
        path = os.path.join(self.emulator["cheat_dir"], bid + ".txt")
        try:
            if os.path.exists(path):
                os.remove(path)
            self.write_enabled_file(bid, [])
        except OSError as e:
            messagebox.showerror("Remove failed", str(e))
            return
        self.refresh_cheats()
        self.status.set("Removed this app's cheats from the emulator. Your cheat list is kept.")

    def export_cheats(self):
        if self.need_build():
            return
        on = [c for c in self.cheats if c.get("on")]
        if not on:
            messagebox.showinfo("Nothing to export", "Turn on at least one cheat first.")
            return
        sd = filedialog.askdirectory(title="Pick your Switch SD card (or a folder to copy to it later)")
        if not sd:
            return
        folder = os.path.join(sd, "atmosphere", "contents", TITLE_ID, "cheats")
        path = os.path.join(folder, self.current_build() + ".txt")
        if os.path.exists(path) and not messagebox.askyesno("Replace file?", f"{path}\nalready exists. Replace it?"):
            return
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(format_cheats(on))
        except OSError as e:
            messagebox.showerror("Export failed", str(e))
            return
        messagebox.showinfo("Exported", f"Saved {len(on)} cheats to:\n{path}\n\nOn the Switch, Atmosphère "
                            "loads them when the game starts. Use the cheat menu (e.g. EdiZon or Breeze) to "
                            "turn individual cheats on or off.")

    # ---------- saving ----------
    def apply(self):
        d = self.data
        for key, (v, lo, hi) in self.general_vars.items():
            try:
                d[key] = max(lo, min(hi, int(v.get())))
            except ValueError:
                raise ValueError(f"General: '{v.get()}' is not a number.")
        d["_current_flower_point"] = min(d["_current_flower_point"], d["_max_flower_point"])

        if not self.store_char():
            raise ValueError("Fix the character values first.")
        for p, orig in zip(self.chars, self.orig_chars):
            p.update(self.equip_totals(p, orig))
        d["_player_work"] = self.chars

        # Everything worn must also be in the equipment bag.
        worn = self.equipped_ids()
        for i in set(worn):
            while self.equipment.count(i) < worn.count(i):
                self.equipment.append(i)

        im = d["_item_manager"]
        size = len(im["_item_list"])
        # One master order; each menu list is that order filtered to its own items.
        order = self.item_order()
        expand = lambda keep: [i for i in order if keep(i) for _ in range(self.items[i])]
        heal = expand(self.recovery)
        battle = expand(lambda i: not self.recovery(i))
        if len(heal) + len(battle) > size:
            raise ValueError(f"You're carrying {len(heal) + len(battle):,} items, but the save only has room "
                             f"for {size:,} in total (one slot per item). Lower some Carried amounts, or move "
                             "the extra to the Storage Box, which has no shared limit.")
        if len(self.equipment) > len(im["_equipment_item_list"]):
            raise ValueError("Too many pieces of equipment.")
        im["_item_list"] = pad(expand(lambda i: True), size)
        im["_normal_menu_heal_item_list"] = pad(heal, size)
        im["_normal_menu_battle_item_list"] = pad(battle, size)
        im["_battle_menu_item_list"] = pad(expand(lambda i: i not in FIELD_ONLY), size)
        im["_storage_box_list"] = list(self.storage)
        im["_equipment_item_list"] = pad(self.equipment, len(im["_equipment_item_list"]))
        if len(self.key_items) > len(im["_important_item_list"]):
            raise ValueError("Too many key items.")
        im["_important_item_list"] = pad(self.key_items, len(im["_important_item_list"]))
        # Per-ID totals of everything owned (bag + equipment + key items).
        totals = [0] * len(im["_all_item_list"])
        for key in ("_item_list", "_equipment_item_list", "_important_item_list"):
            for i in im[key]:
                if 0 < i < len(totals):
                    totals[i] += 1
        im["_all_item_list"] = totals

    def save(self):
        if not self.data:
            return
        try:
            self.apply()
        except ValueError as e:
            messagebox.showerror("Can't save", str(e))
            return
        name = self.slot_file()
        targets = [name]
        mirror = SLOT_PREFIX + MIRROR_SLOT
        if name != mirror and self.is_mirrored(name):
            targets.append(mirror)
        changes = describe_changes(self.loaded, self.data)
        if not changes:
            messagebox.showinfo("Nothing to save", "You haven't changed anything in this slot.")
            return
        if not self.confirm_changes(changes, targets):
            return
        # Warn only when the save has no up-to-date backup: none exists, or the game has
        # written to the save since the newest one. If the files on disk are exactly what
        # this editor last saved, back them up quietly so each edit can still be undone.
        dest = self.current_backup()
        choice = None
        if dest:
            backup_note = f"Your up-to-date backup is:\n{dest}"
        elif self.unchanged_since_last_save():
            choice = "backup"
        else:
            choice = self.backup_warning()
            if choice is None:
                return
            backup_note = "No backup was made."
        try:
            if not dest and choice == "backup":
                dest = os.path.basename(self.make_backup("before edit"))
                backup_note = f"The old files were backed up as:\n{dest}"
            for c in self.copies():
                for t in targets:
                    dump_save(self.data, os.path.join(c, t))
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.settings.setdefault("last_saved", {})[self.root_dir.get()] = self.fingerprint()
        store_settings(self.settings)
        self.status.set(f"Saved {', '.join(targets)}." + (f" Backup: {dest}" if dest else " No backup made."))
        idx = self.slot_box.current()
        self.refresh_slots()
        self.slot_box.current(idx)
        self.load_slot()
        messagebox.showinfo("Saved", f"Saved!\n\n{backup_note}")

    def backup_warning(self):
        """Warn that there's no up-to-date backup. Returns "backup", "skip" or None (cancel)."""
        newest = self.list_backups()[:1]
        if newest:
            when = backup_time(newest[0])
            stamp = f"{when:%B} {when.day}, {when.year} at {when.hour % 12 or 12}:{when:%M %p}"
            reason = (f"Your newest backup is from {stamp} "
                      f"({age_text(datetime.now() - when)} ago), and your save has changed since then. "
                      "You've played or edited it.") if when else (
                      "Your newest backup doesn't match your current save. It has changed since then.")
        else:
            reason = "You don't have any backups of this save yet."
        win = tk.Toplevel(self)
        win.title("Back up first?")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        body = ttk.Frame(win, padding=16)
        body.pack(fill="both")
        ttk.Label(body, text="⚠  Your save isn't backed up", style="Warn.TLabel").pack(anchor="w")
        ttk.Label(body, text=reason + "\n\nMake a backup now so you can undo this edit if "
                  "something goes wrong?", wraplength=440, justify="left").pack(anchor="w", pady=(8, 0))
        result = {"choice": None}

        def pick(choice):
            result["choice"] = choice
            win.destroy()

        row = ttk.Frame(win, padding=(16, 0, 16, 16))
        row.pack(fill="x")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(row, text="Save without a backup", command=lambda: pick("skip")).pack(side="right", padx=6)
        self.primary_button(row, "Back up and save", lambda: pick("backup")).pack(side="right")
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>", lambda e: pick("backup"))
        self.center(win)
        self.wait_window(win)
        return result["choice"]

    def center(self, win):
        """Place a pop-up window in the middle of the editor window (and theme it)."""
        self.theme_window(win)
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        if win.winfo_width() > 1:
            w, h = max(w, win.winfo_width()), max(h, win.winfo_height())
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 3
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def primary_button(self, parent, text, command):
        """A green button for the main 'save' action."""
        return tk.Button(parent, text=text, command=command, bg="#2e7d32", fg="white",
                         activebackground="#1b5e20", activeforeground="white", relief="flat",
                         font=("Segoe UI", 10, "bold"), padx=14, pady=3, cursor="hand2",
                         borderwidth=0, highlightthickness=0)

    def confirm_changes(self, changes, targets):
        """Modal listing every change; returns True if the user chooses to save."""
        win = tk.Toplevel(self)
        win.title("Review changes")
        win.geometry("620x460")
        win.transient(self)
        win.grab_set()
        where = " (both copies)" if len(self.copies()) > 1 else ""
        ttk.Label(win, padding=(10, 10, 10, 4), wraplength=590, justify="left", text=(
            f"{len(changes)} change{'s' if len(changes) != 1 else ''} will be written to "
            f"{' and '.join(targets)}{where}.\n"
            "Make sure the game/emulator is closed.")).pack(anchor="w")
        frame = ttk.Frame(win, padding=(10, 0))
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", height=14, font=("Segoe UI", 10), padx=8, pady=6)
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("head", font=("Segoe UI", 10, "bold"), spacing1=6)
        section = None
        for group, line in changes:
            if group != section:
                text.insert("end", group + "\n", "head")
                section = group
            text.insert("end", "   • " + line + "\n")
        text.configure(state="disabled")
        result = {"ok": False}

        def ok():
            result["ok"] = True
            win.destroy()

        row = ttk.Frame(win, padding=10)
        row.pack(fill="x")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="right")
        self.primary_button(row, "Save these changes", ok).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        self.center(win)
        self.wait_window(win)
        return result["ok"]

    def is_mirrored(self, name):
        """True if the game's backup copy (005) is identical to this slot on disk."""
        src = os.path.join(self.copies()[0], name)
        mirror = os.path.join(self.copies()[0], SLOT_PREFIX + MIRROR_SLOT)
        if not os.path.exists(mirror):
            return False
        with open(src, "rb") as a, open(mirror, "rb") as b:
            return a.read() == b.read()

    # ---------- backups ----------
    def backup_name(self, copy):
        return os.path.basename(copy) if copy != self.root_dir.get() else SINGLE_LAYOUT

    def make_backup(self, note=""):
        copies = self.copies()
        if not copies:
            raise RuntimeError("No save folder to back up.")
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        note = re.sub(r'[\\/:*?"<>|]', "", note).strip()[:60]
        dest = os.path.join(BACKUP_DIR, f"{stamp} {note}".strip())
        n = 2
        while os.path.exists(dest):
            dest = os.path.join(BACKUP_DIR, f"{stamp} {note} ({n})".strip())
            n += 1
        for c in copies:
            shutil.copytree(c, os.path.join(dest, self.backup_name(c)))
        with open(os.path.join(dest, "source.txt"), "w", encoding="utf-8") as f:
            f.write(self.root_dir.get() + "\n")
        self.update_backup_count()
        return dest

    def fingerprint(self):
        """SHA-256 of every save file in this folder, keyed by copy/file name."""
        out = {}
        for c in self.copies():
            for f in sorted(os.listdir(c)):
                if f.startswith(SLOT_PREFIX):
                    with open(os.path.join(c, f), "rb") as fh:
                        out[f"{self.backup_name(c)}/{f}"] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def unchanged_since_last_save(self):
        """True if the save on disk is exactly what this editor last wrote (the game hasn't
        saved over it since)."""
        last = self.settings.get("last_saved", {}).get(self.root_dir.get())
        return bool(last) and last == self.fingerprint() and bool(self.list_backups())

    def current_backup(self):
        """Name of the newest backup identical to the save on disk now, or None."""
        copies = self.copies()
        current = {}
        for c in copies:
            for f in os.listdir(c):
                if f.startswith(SLOT_PREFIX):
                    with open(os.path.join(c, f), "rb") as fh:
                        current[(self.backup_name(c), f)] = fh.read()
        if not current:
            return None
        for name in self.list_backups():
            base = os.path.join(BACKUP_DIR, name)
            try:
                saved = {(sub, f) for sub in {k[0] for k in current}
                         for f in os.listdir(os.path.join(base, sub)) if f.startswith(SLOT_PREFIX)}
                if saved != set(current):
                    continue
                if all(open(os.path.join(base, sub, f), "rb").read() == data
                       for (sub, f), data in current.items()):
                    return name
            except OSError:
                continue
        return None

    def list_backups(self):
        if not os.path.isdir(BACKUP_DIR):
            return []
        return sorted((n for n in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, n))),
                      reverse=True)

    def update_backup_count(self):
        n = len(self.list_backups())
        self.backup_count.set(f"{n} backup{'s' if n != 1 else ''} in {BACKUP_DIR}")

    def backup_now(self):
        if not self.copies():
            messagebox.showerror("No save", "Pick a save folder first.")
            return
        note = simpledialog.askstring("Back up now", "Optional note for this backup "
                                      "(e.g. 'before Bowser's Keep'):", parent=self)
        if note is None:
            return
        try:
            dest = self.make_backup(note)
        except Exception as e:
            messagebox.showerror("Backup failed", str(e))
            return
        self.status.set(f"Backup created: {os.path.basename(dest)}")
        messagebox.showinfo("Backed up", f"Backup created:\n{os.path.basename(dest)}")

    def open_backups(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        open_folder(BACKUP_DIR)

    def restore_backup(self, name):
        src = os.path.join(BACKUP_DIR, name)
        copies = self.copies()
        missing = [c for c in copies if not os.path.isdir(os.path.join(src, self.backup_name(c)))]
        if missing or not copies:
            raise RuntimeError("This backup was made from a different kind of save folder "
                               "and can't be restored here.")
        self.make_backup("before restore")
        for c in copies:
            s = os.path.join(src, self.backup_name(c))
            for f in os.listdir(c):           # replace the save files, keep anything else
                if f.startswith(SLOT_PREFIX):
                    os.remove(os.path.join(c, f))
            for f in os.listdir(s):
                if f.startswith(SLOT_PREFIX):
                    shutil.copy2(os.path.join(s, f), os.path.join(c, f))

    def restore_dialog(self):
        backups = self.list_backups()
        if not backups:
            messagebox.showinfo("No backups", "There are no backups yet.")
            return
        win = tk.Toplevel(self)
        win.title("Restore a backup")
        win.geometry("580x400")
        win.transient(self)
        ttk.Label(win, text="Newest first. Restoring replaces your current save "
                  "(a backup of it is made first).", padding=8).pack(anchor="w")
        lb = tk.Listbox(win, activestyle="dotbox")
        lb.pack(fill="both", expand=True, padx=8)
        for b in backups:
            lb.insert("end", b)
        lb.selection_set(0)
        row = ttk.Frame(win, padding=8)
        row.pack(fill="x")

        def chosen():
            s = lb.curselection()
            return backups[s[0]] if s else None

        def do_restore():
            b = chosen()
            if not b or not messagebox.askyesno(
                    "Restore", f"Make sure the game/emulator is closed.\n\nRestore '{b}'?", parent=win):
                return
            try:
                self.restore_backup(b)
            except Exception as e:
                messagebox.showerror("Restore failed", str(e), parent=win)
                return
            win.destroy()
            self.refresh_slots()
            self.status.set(f"Restored backup: {b}")
            messagebox.showinfo("Restored", f"Restored:\n{b}")

        def do_delete():
            b = chosen()
            if not b or not messagebox.askyesno(
                    "Delete backup", f"Permanently delete backup '{b}'?", parent=win):
                return
            shutil.rmtree(os.path.join(BACKUP_DIR, b), ignore_errors=True)
            i = backups.index(b)
            backups.pop(i)
            lb.delete(i)
            self.update_backup_count()

        ttk.Button(row, text="Restore selected", command=do_restore).pack(side="left")
        ttk.Button(row, text="Delete selected", command=do_delete).pack(side="left", padx=4)
        ttk.Button(row, text="Close", command=win.destroy).pack(side="right")
        self.center(win)


if __name__ == "__main__":
    if sys.platform == "win32":
        try:   # own taskbar entry and icon, instead of grouping under Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dlrdev.SuperMarioRPGSwitchSaveEditor")
        except Exception:
            pass
    Editor(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
