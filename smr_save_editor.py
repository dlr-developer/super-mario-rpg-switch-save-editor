"""Super Mario RPG (Nintendo Switch, 2023) save editor.

Save files are UTF-16 LE JSON with no checksum. Works with saves from any
emulator (Ryujinx-style folders "0"/"1", or yuzu-style single folder) and
with saves dumped from a real Switch (e.g. with JKSV).

Item IDs/names: Echocolat/SMR-save-edit-scripts (data/ids.json).
Equipment stats: Nintendo Life, Gamer Guides, Samurai Gamers, Super Mario Wiki.
"""
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "Super Mario RPG Switch Save Editor"
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
BACKUP_DIR = os.path.join(APP_DIR, "backups")
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
    ("_experience", "Experience", 0, 9999999),
    ("_hp", "HP (current)", 0, 999),
    ("_hp_max", "HP (max)", 1, 999),
    ("_speed", "Speed", 0, 255),
    ("_attack", "Attack", 0, 255),
    ("_defence", "Defense", 0, 255),
    ("_magic_attack", "Magic Attack", 0, 255),
    ("_magic_defence", "Magic Defense", 0, 255),
]

ITEM_MAX_STACK = 99
CAT_HEAL = "Usable in field + battle"
CAT_FIELD = "Field only"
CAT_BATTLE = "Battle item"
CATEGORIES = [CAT_HEAL, CAT_FIELD, CAT_BATTLE]


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


def default_category(i):
    if i in (99, 100, 101):          # Flower Tab/Jar/Box raise max FP, used from the menu
        return CAT_FIELD
    if 87 <= i <= 98 or 126 <= i <= 130:
        return CAT_HEAL
    return CAT_BATTLE


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
    for base in (appdata, os.path.join(home, ".config"), os.path.join(home, ".local", "share"),
                 os.path.join(home, "Library", "Application Support")):
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
            out.append(("Items", f"{item_name(i)}: {a} → {b}{note}"))
    battle_old = set(ordered_counts(oi["_battle_menu_item_list"]))
    battle_new = set(ordered_counts(ni["_battle_menu_item_list"]))
    for i in sorted((battle_old ^ battle_new) & set(before) & set(after)):
        out.append(("Items", f"{item_name(i)}: {'now' if i in battle_new else 'no longer'} usable in battle"))

    before, after = ordered_counts(oi["_equipment_item_list"]), ordered_counts(ni["_equipment_item_list"])
    for i in sorted(set(before) | set(after)):
        a, b = before.get(i, 0), after.get(i, 0)
        if a != b:
            out.append(("Equipment bag", f"{item_name(i)}: {a} → {b}"))
    return out


class Editor(tk.Tk):
    def __init__(self, folder=None):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x660")
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
        self.items = {}   # consumable id -> [qty, category]
        self.equipment = []

        self._build_top()
        self._build_tabs()
        start = folder or self.settings.get("save_folder")
        start = resolve_save_folder(start) if start else None
        self.set_folder(start or autodetect())

    # ---------- layout ----------
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
        ttk.Button(btns, text="Save changes", command=self.save).pack(side="left", padx=(4, 0))

        bk = ttk.LabelFrame(top, text="Backups", padding=6)
        bk.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(bk, text="Back up now…", command=self.backup_now).pack(side="left")
        ttk.Button(bk, text="Restore a backup…", command=self.restore_dialog).pack(side="left", padx=4)
        ttk.Button(bk, text="Open backups folder", command=self.open_backups).pack(side="left")
        self.backup_count = tk.StringVar()
        ttk.Label(bk, textvariable=self.backup_count, foreground="#555").pack(side="left", padx=10)
        top.columnconfigure(1, weight=1)

        self.status = tk.StringVar(value="Close the game/emulator before saving or restoring.")
        ttk.Label(self, textvariable=self.status, foreground="#555", padding=(8, 0)).pack(
            side="bottom", fill="x", pady=4)

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # General
        gen = ttk.Frame(nb, padding=12)
        nb.add(gen, text="General")
        for r, (key, label, lo, hi) in enumerate(GENERAL_FIELDS):
            ttk.Label(gen, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Spinbox(gen, from_=lo, to=hi, textvariable=v, width=14).grid(row=r, column=1, sticky="w", padx=8)
            ttk.Label(gen, text=f"({lo}–{hi})", foreground="#888").grid(row=r, column=2, sticky="w")
            self.general_vars[key] = (v, lo, hi)
        self.info = tk.StringVar()
        ttk.Label(gen, textvariable=self.info, foreground="#555", justify="left").grid(
            row=len(GENERAL_FIELDS), column=0, columnspan=3, sticky="w", pady=(16, 0))

        # Characters
        ch = ttk.Frame(nb, padding=12)
        nb.add(ch, text="Characters")
        ttk.Label(ch, text="Character:").grid(row=0, column=0, sticky="w")
        self.char_sel = tk.StringVar()
        self.char_box = ttk.Combobox(ch, textvariable=self.char_sel, state="readonly", width=16)
        self.char_box.grid(row=0, column=1, sticky="w", padx=8)
        self.char_box.bind("<<ComboboxSelected>>", lambda e: self.show_char())
        self._char_index = None
        for r, (key, label, lo, hi) in enumerate(CHAR_FIELDS, start=1):
            ttk.Label(ch, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Spinbox(ch, from_=lo, to=hi, textvariable=v, width=14,
                        command=self.update_totals).grid(row=r, column=1, sticky="w", padx=8)
            ttk.Label(ch, text=f"({lo}–{hi})", foreground="#888").grid(row=r, column=2, sticky="w")
            self.char_vars[key] = (v, lo, hi)

        eqf = ttk.LabelFrame(ch, text="Equipped", padding=8)
        eqf.grid(row=1, column=3, rowspan=len(CHAR_FIELDS), sticky="nw", padx=(24, 0))
        self.gear_boxes = {}
        for r, slot in enumerate((WEAPON, ARMOR, ACCESSORY)):
            ttk.Label(eqf, text=SLOT_LABELS[slot]).grid(row=r * 2, column=0, sticky="w")
            v = tk.StringVar()
            box = ttk.Combobox(eqf, textvariable=v, state="readonly", width=46)
            box.grid(row=r * 2 + 1, column=0, sticky="w", pady=(0, 8))
            box.bind("<<ComboboxSelected>>", lambda e: self.update_totals())
            self.gear_vars[slot] = v
            self.gear_boxes[slot] = box
        self.totals = tk.StringVar()
        ttk.Label(eqf, textvariable=self.totals, foreground="#555", justify="left").grid(
            row=6, column=0, sticky="w")
        ttk.Label(ch, foreground="#555", wraplength=820, text=(
            "Only gear that character can wear is listed. Gear you don't own is added to your bag "
            "automatically. Stat changes and gear changes also update the 'with equipment' totals "
            "the menu shows. Switching characters keeps your unsaved edits.")).grid(
            row=len(CHAR_FIELDS) + 1, column=0, columnspan=4, sticky="w", pady=(12, 0))

        # Items
        it = ttk.Frame(nb, padding=12)
        nb.add(it, text="Items")
        self.tree = self._make_tree(it, (("id", "ID", 50), ("name", "Item", 200),
                                         ("qty", "Quantity", 80), ("cat", "Type", 200)))
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        ttk.Label(it, text="Item").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(it, text="Quantity").grid(row=1, column=1, sticky="w", pady=(10, 0))
        ttk.Label(it, text="Type").grid(row=1, column=2, sticky="w", pady=(10, 0))
        self.item_pick = tk.StringVar()
        self.item_qty = tk.StringVar()
        self.item_cat = tk.StringVar(value=CAT_HEAL)
        pick = ttk.Combobox(it, textvariable=self.item_pick, state="readonly", width=28,
                            values=[item_label(i) for i in CONSUMABLE_RANGE])
        pick.grid(row=2, column=0, sticky="w")
        pick.bind("<<ComboboxSelected>>", self.on_pick)
        ttk.Spinbox(it, from_=0, to=ITEM_MAX_STACK, textvariable=self.item_qty, width=8).grid(row=2, column=1, sticky="w", padx=4)
        ttk.Combobox(it, textvariable=self.item_cat, values=CATEGORIES, state="readonly", width=24).grid(row=2, column=2, sticky="w")
        ttk.Button(it, text="Set / Add", command=self.set_item).grid(row=2, column=3, padx=4)
        ttk.Button(it, text="Max all to 99", command=self.max_items).grid(row=2, column=4)
        ttk.Label(it, foreground="#555", wraplength=820, text=(
            "Pick a row (or choose an item from the list) and set its quantity. 0 removes it. "
            "For new items the type is filled in automatically. It decides which menu the item "
            "appears in.")).grid(row=3, column=0, columnspan=6, sticky="w", pady=(10, 0))

        # Equipment bag & key items
        eq = ttk.Frame(nb, padding=12)
        nb.add(eq, text="Equipment Bag & Key Items")
        self.eq_tree = self._make_tree(eq, (("id", "ID", 50), ("name", "Item", 220), ("kind", "Kind", 220)))
        ttk.Label(eq, text="Add equipment:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.eq_pick = tk.StringVar()
        ttk.Combobox(eq, textvariable=self.eq_pick, state="readonly", width=46,
                     values=[gear_label(i) for i in EQUIP_IDS]).grid(row=2, column=0, sticky="w")
        ttk.Button(eq, text="Add", command=self.add_equipment).grid(row=2, column=1, padx=4, sticky="w")
        ttk.Button(eq, text="Remove selected", command=self.remove_equipment).grid(row=2, column=2, sticky="w")
        ttk.Label(eq, foreground="#555", wraplength=820, text=(
            "Equipment added here goes into your bag. To wear it, use the Characters tab or equip "
            "it in-game. Equipped items can't be removed. Key items are view-only, because "
            "changing them can break story progress.")).grid(row=3, column=0, columnspan=6, sticky="w", pady=(10, 0))

    def _make_tree(self, parent, cols):
        tree = ttk.Treeview(parent, columns=[c[0] for c in cols], show="headings", height=12)
        for col, txt, w in cols:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        tree.grid(row=0, column=0, columnspan=6, sticky="nsew")
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        sb.grid(row=0, column=6, sticky="ns")
        tree.configure(yscrollcommand=sb.set)
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(5, weight=1)
        return tree

    # ---------- folder & slots ----------
    def set_folder(self, folder):
        self.root_dir.set(folder or "")
        if folder:
            self.settings["save_folder"] = folder
            store_settings(self.settings)
        self.refresh_slots()

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
        heal = ordered_counts(im["_normal_menu_heal_item_list"])
        battle_menu = set(ordered_counts(im["_battle_menu_item_list"]))
        self.items = {}
        for i, q in heal.items():
            self.items[i] = [q, CAT_HEAL if i in battle_menu else CAT_FIELD]
        for i, q in ordered_counts(im["_normal_menu_battle_item_list"]).items():
            self.items[i] = [q, CAT_BATTLE]
        self.equipment = [i for i in im["_equipment_item_list"] if i]
        self.refresh_items()
        self.refresh_equipment()
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
    def refresh_items(self):
        self.tree.delete(*self.tree.get_children())
        for i, (q, cat) in self.items.items():
            self.tree.insert("", "end", iid=str(i), values=(i, item_name(i), q, cat))

    def on_item_select(self, _):
        sel = self.tree.selection()
        if sel:
            i = int(sel[0])
            self.item_pick.set(item_label(i))
            self.item_qty.set(str(self.items[i][0]))
            self.item_cat.set(self.items[i][1])

    def on_pick(self, _):
        i = int(self.item_pick.get().split()[0])
        if i in self.items:
            self.item_qty.set(str(self.items[i][0]))
            self.item_cat.set(self.items[i][1])
        else:
            self.item_qty.set("1")
            self.item_cat.set(default_category(i))

    def set_item(self):
        if not self.item_pick.get():
            messagebox.showerror("Pick an item", "Choose an item first.")
            return
        i = int(self.item_pick.get().split()[0])
        try:
            q = max(0, min(ITEM_MAX_STACK, int(self.item_qty.get())))
        except ValueError:
            messagebox.showerror("Invalid", "Quantity must be a number.")
            return
        if q == 0:
            self.items.pop(i, None)
        else:
            self.items[i] = [q, self.item_cat.get()]
        self.refresh_items()
        if str(i) in self.tree.get_children():
            self.tree.selection_set(str(i))
            self.tree.see(str(i))

    def max_items(self):
        for v in self.items.values():
            v[0] = ITEM_MAX_STACK
        self.refresh_items()

    # ---------- equipment bag ----------
    def joined(self, p):
        return p.get("_id") in self.data.get("_party_order", [])

    def worn_gear(self):
        """(character, item) pairs that must be in the bag: gear worn by party members, plus
        gear changed in this editor. Characters who haven't joined yet have starting gear
        that the bag doesn't contain."""
        pairs = []
        for p, orig in zip(self.chars, self.orig_chars):
            for slot in (WEAPON, ARMOR, ACCESSORY):
                i = p.get(slot, 0)
                if i and (self.joined(p) or i != orig.get(slot, 0)):
                    pairs.append((p["_name"], i))
        return pairs

    def equipped_ids(self):
        return [i for _, i in self.worn_gear()]

    def refresh_equipment(self):
        self.eq_tree.delete(*self.eq_tree.get_children())
        wearers = {}
        for name, i in self.worn_gear():
            wearers.setdefault(i, []).append(name)
        shown = {}
        for n, i in enumerate(self.equipment):
            kind = SLOT_LABELS.get(GEAR.get(i, (None,))[0], "Equipment")
            k = shown.get(i, 0)
            if k < len(wearers.get(i, [])):
                kind += f" (worn by {wearers[i][k]})"
            shown[i] = k + 1
            self.eq_tree.insert("", "end", iid=f"e{n}", values=(i, item_name(i), kind))
        for n, i in enumerate(x for x in self.data["_item_manager"]["_important_item_list"] if x):
            self.eq_tree.insert("", "end", iid=f"k{n}", values=(i, item_name(i), "Key item"))

    def add_equipment(self):
        if not self.eq_pick.get():
            return
        if len(self.equipment) >= len(self.data["_item_manager"]["_equipment_item_list"]):
            messagebox.showerror("Full", "The equipment bag is full.")
            return
        self.equipment.append(int(self.eq_pick.get().split()[0]))
        self.refresh_equipment()

    def remove_equipment(self):
        self.store_char()
        sel = [s for s in self.eq_tree.selection() if s.startswith("e")]
        if not sel:
            return
        n = int(sel[0][1:])
        i = self.equipment[n]
        if self.equipment.count(i) <= self.equipped_ids().count(i):
            messagebox.showerror("Equipped", f"{item_name(i)} is being worn. Unequip it on the "
                                 "Characters tab first.")
            return
        del self.equipment[n]
        self.refresh_equipment()

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
        expand = lambda cats: [i for i, (q, c) in self.items.items() if c in cats for _ in range(q)]
        heal = expand((CAT_HEAL, CAT_FIELD))
        battle = expand((CAT_BATTLE,))
        if len(heal) + len(battle) > size:
            raise ValueError(f"Too many items in total (limit {size}).")
        if len(self.equipment) > len(im["_equipment_item_list"]):
            raise ValueError("Too many pieces of equipment.")
        im["_item_list"] = pad(heal + battle, size)
        im["_normal_menu_heal_item_list"] = pad(heal, size)
        im["_normal_menu_battle_item_list"] = pad(battle, size)
        im["_battle_menu_item_list"] = pad(expand((CAT_HEAL,)) + battle, size)
        im["_equipment_item_list"] = pad(self.equipment, len(im["_equipment_item_list"]))
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
        try:
            dest = self.make_backup("before edit")
            for c in self.copies():
                for t in targets:
                    dump_save(self.data, os.path.join(c, t))
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.status.set(f"Saved {', '.join(targets)}. Backup: {os.path.basename(dest)}")
        idx = self.slot_box.current()
        self.refresh_slots()
        self.slot_box.current(idx)
        self.load_slot()
        messagebox.showinfo("Saved", f"Saved!\n\nThe old files were backed up as:\n{os.path.basename(dest)}")

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
            f"{' and '.join(targets)}{where}. A backup of the current files is made first.\n"
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
        ttk.Button(row, text="Save these changes", command=ok).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
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


if __name__ == "__main__":
    Editor(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
