# Super Mario RPG Switch Save Editor

A desktop save editor for **Super Mario RPG** (Nintendo Switch, 2023 remake, title ID `0100BC0018138000`). It works with saves from a real Switch and from any Switch emulator.

## Features

- **General:** Coins, Frog Coins, Flower Points, Wine Coins and play time. Star Pieces are shown read-only (collected / 7).
- **Characters:** level, EXP, HP and all five stats for Mario, Mallow, Geno, Bowser and Peach.
- **Equipment:** change each character's weapon, armor and accessory. Only gear that character can wear is listed, along with its stat bonuses, and the in-game "with equipment" stats are updated for you.
- **Items:** every consumable listed by name. Change quantities, add new items, or max everything to 99.
- **Equipment bag & key items:** see everything you own, and add or remove spare gear.
- **Review before saving:** a window lists every change ("Coins: 210 → 9999", "Mario Weapon: Hammer → Super Hammer"…) before anything is written.
- **Backups:** an automatic backup before every save and every restore, plus unlimited manual backups with notes and one-click restore.
- **Safe by design:** anything you don't edit is written back byte-for-byte as the game wrote it.

## Download

- **Windows:** download `Super Mario RPG Save Editor.exe` from the [Releases](../../releases) page and double-click it. You don't need to install Python.
- **Any OS (from source):** install [Python 3.8+](https://www.python.org/downloads/) and run `python smr_save_editor.py`. On Windows you can also double-click `Open Save Editor.bat`. Tkinter comes with the standard Windows and macOS installers. On Linux, install `python3-tk`.

> **Always close the game or emulator before saving or restoring.** If it's running, it can overwrite your edits when it next saves.

## Instructions by system

The save files are identical on every system. The only difference is where they live and how you reach them. The editor tries to **auto-detect** your save. If it can't, click **Browse…** and pick the save folder, or any folder above it, and the editor searches inside.

### Ryujinx (Windows / macOS / Linux)

1. In Ryujinx, right-click **Super Mario RPG** → **Open User Save Directory**. That shows you where the save is.
2. Close Ryujinx.
3. Open the editor. It usually finds the save by itself. If not, Browse to the folder from step 1. The folder that contains the `0` and `1` subfolders is the one to pick.
4. Edit and save. Ryujinx keeps two copies (`0` and `1`), and the editor writes both.

Default locations:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\Ryujinx\bis\user\save\<number>\` |
| Windows (portable build) | `<Ryujinx folder>\portable\bis\user\save\<number>\` |
| macOS | `~/Library/Application Support/Ryujinx/bis/user/save/<number>/` |
| Linux | `~/.config/Ryujinx/bis/user/save/<number>/` |

### yuzu family: yuzu, suyu, sudachi, citron, eden, torzu

1. In the emulator, right-click **Super Mario RPG** → **Open Save Data Location**.
2. Close the emulator.
3. Open the editor. It usually finds the save by itself. If not, Browse to that folder (it ends in `0100BC0018138000`).
4. Edit and save.

Default locations (replace `<emulator>` with `yuzu`, `suyu`, `sudachi`, `citron`, `eden` or `torzu`):

| OS | Path |
|---|---|
| Windows | `%APPDATA%\<emulator>\nand\user\save\0000000000000000\<user id>\0100BC0018138000\` |
| Linux | `~/.local/share/<emulator>/nand/user/save/0000000000000000/<user id>/0100BC0018138000/` |

### Android emulators (eden, citron, sudachi, etc.)

The editor is a desktop app, so move the save to a PC and back:

1. Export the save with the emulator's save-data option (where your emulator has one), or copy the `nand/user/save/…/0100BC0018138000` folder from the emulator's data folder on your phone.
2. Copy the files to a PC, open that folder in the editor, edit and save.
3. Copy the edited files back to the same folder on the phone, then start the game.

### Real Nintendo Switch (homebrew required)

You need a Switch that can run homebrew, plus a save manager such as [JKSV](https://github.com/J-D-K/JKSV) or [Checkpoint](https://github.com/BernardoGiordano/Checkpoint).

1. **Back up on the Switch:** open JKSV (or Checkpoint), select your user → **Super Mario RPG** → **New backup**. It's saved to the SD card:
   - JKSV: `sd:/JKSV/Super Mario RPG/<backup name>/`
   - Checkpoint: `sd:/switch/Checkpoint/saves/0x0100BC0018138000 Super Mario RPG/<backup name>/`
2. **Copy that backup folder to your PC.** Keep an untouched copy somewhere as well.
3. **Edit:** open the folder in the editor (Browse…), make your changes, and save.
4. **Copy the edited folder back** to the same place on the SD card.
5. **Restore on the Switch:** in JKSV or Checkpoint, select that backup → **Restore**, then start the game.

> **Notes:**
> - **Cloud saves:** Nintendo Switch Online cloud saves can't be edited directly. Edit the save on the console, and if you use cloud backup, upload the edited save afterwards.
> - **Switch 2:** the save format is the same. If your Switch 2 can run a save manager, the steps are the same. Otherwise there's no way to get the save off the console.

## Save files

| File | What it is |
|---|---|
| `SMR_Save_Ver0011000` | Autosave |
| `SMR_Save_Ver0011002` | Slot 1 |
| `SMR_Save_Ver0011003` | Slot 2 |
| `SMR_Save_Ver0011004` | Slot 3 |
| `SMR_Save_Ver0011005` | The game's backup copy of the last save. The editor updates it together with that slot when the two match. |
| `SMR_Save_Ver0011_image` | Save thumbnail (not edited) |

The files are plain JSON text encoded as UTF-16 LE. They have no checksum or encryption.

## Backups

Backups are stored in the `backups` folder next to the editor (or next to the `.exe`). Each backup is a dated folder holding a full copy of your save. **Back up now…** lets you add a note. **Restore a backup…** lists them newest first, and you can delete old ones there. A backup is made automatically before every save and before every restore, so a restore can always be undone.

## Notes and limits

- Key items and story flags aren't editable, because changing them can break progress.
- Star Pieces are bit flags set by story events (one bit per star), so they're read-only.
- Characters who haven't joined your party yet show as "(not joined yet)". You can still edit them.
- Stats for the post-game weapons (Sage Stick, Stella 023, Wonder Chomp) come from community sources and may be slightly off. The game recalculates them when you re-equip in-game.
- **Keep a backup of your save before editing.** Use at your own risk.

## Item IDs

The save stores every item as a number from 0 to 167. Stats are the bonuses each piece of equipment adds.

#### Weapons

| ID | Name | Who can equip | Stats |
|---:|---|---|---|
| 1 | Hammer | Mario | Atk +10 |
| 2 | Super Hammer | Mario | Atk +40 |
| 3 | Masher | Mario | Atk +50 |
| 4 | Lucky Hammer | Mario | — |
| 5 | Ultra Hammer | Mario | Atk +70 |
| 6 | NokNok Shell | Mario | Atk +20 |
| 7 | Troopa Shell | Mario | Atk +50 |
| 8 | Lazy Shell (weapon) | Mario | Atk +90 |
| 9 | Punch Glove | Mario | Atk +30 |
| 10 | Mega Glove | Mario | Atk +60 |
| 11 | Froggie Stick | Mallow | Atk +20 |
| 12 | Ribbit Stick | Mallow | Atk +50 |
| 13 | Cymbals | Mallow | Atk +30 |
| 14 | Sonic Cymbal | Mallow | Atk +70 |
| 15 | Whomp Glove | Mallow | Atk +35 |
| 16 | Sticky Glove | Mallow | Atk +60 |
| 17 | Finger Shot | Geno | Atk +12 |
| 18 | Hand Gun | Geno | Atk +24 |
| 19 | Hand Cannon | Geno | Atk +45 |
| 20 | Star Gun | Geno | Atk +57 |
| 21 | Double Punch | Geno | Atk +35 |
| 22 | Chomp Shell | Bowser | Atk +9 |
| 23 | Chomp | Bowser | Atk +10 |
| 24 | Spiked Link | Bowser | Atk +30 |
| 25 | Hurly Gloves | Bowser | Atk +20 |
| 26 | Drill Claw | Bowser | Atk +40 |
| 27 | Slap Glove | Peach | Atk +40 |
| 28 | Super Slap | Peach | Atk +70 |
| 29 | Parasol | Peach | Atk +50 |
| 30 | War Fan | Peach | Atk +60 |
| 31 | Frying Pan | Peach | Atk +90 |
| 158 | Sage Stick | Mallow | Atk +80, Mg Atk +15 |
| 159 | Stella 023 | Geno | Atk +62 |
| 160 | Wonder Chomp | Bowser | Atk +57 |

#### Armor

| ID | Name | Who can equip | Stats |
|---:|---|---|---|
| 32 | Shirt | Mario | Def +6, Mg Def +6 |
| 33 | Thick Shirt | Mario | Def +12, Mg Def +8 |
| 34 | Mega Shirt | Mario | Def +18, Mg Def +10 |
| 35 | Happy Shirt | Mario | Def +24, Mg Def +12 |
| 36 | Sailor Shirt | Mario | Def +30, Mg Def +15 |
| 37 | Fluffy Shirt | Mario | Def +36, Mg Def +18 |
| 38 | Fire Shirt | Mario | Def +42, Mg Def +21 |
| 39 | Hero Shirt | Mario | Def +48, Mg Def +24 |
| 40 | Pants | Mallow | Def +6, Mg Def +3 |
| 41 | Thick Pants | Mallow | Def +12, Mg Def +6 |
| 42 | Mega Pants | Mallow | Def +18, Mg Def +9 |
| 43 | Work Pants | All | Atk +10, Def +15, Mg Atk +10, Mg Def +5, Spd +5 |
| 44 | Happy Pants | Mallow | Def +24, Mg Def +12 |
| 45 | Sailor Pants | Mallow | Def +30, Mg Def +15 |
| 46 | Fluffy Pants | Mallow | Def +36, Mg Def +18 |
| 47 | Fire Pants | Mallow | Def +42, Mg Def +21 |
| 48 | Prince Pants | Mallow | Def +48, Mg Def +24 |
| 49 | Mega Cape | Geno | Def +6, Mg Def +3 |
| 50 | Happy Cape | Geno | Def +12, Mg Def +6 |
| 51 | Sailor Cape | Geno | Def +18, Mg Def +9 |
| 52 | Fluffy Cape | Geno | Def +24, Mg Def +12 |
| 53 | Fire Cape | Geno | Def +30, Mg Def +15 |
| 54 | Star Cape | Geno | Def +36, Mg Def +18 |
| 55 | Happy Shell | Bowser | Def +6, Mg Def +3 |
| 56 | Courage Shell | Bowser | Def +12, Mg Def +6 |
| 57 | Fire Shell | Bowser | Def +18, Mg Def +9 |
| 58 | Heal Shell | Bowser | Def +24, Mg Def +12 |
| 59 | Lovely Dress | Peach | Def +24, Mg Def +12 |
| 60 | Sailor Dress | Peach | Def +30, Mg Def +15 |
| 61 | Fluffy Dress | Peach | Def +36, Mg Def +18 |
| 62 | Fire Dress | Peach | Def +42, Mg Def +21 |
| 63 | Royal Dress | Peach | Def +48, Mg Def +24 |
| 64 | Super Suit | All | Atk +50, Def +50, Mg Atk +50, Mg Def +50, Spd +30 |
| 65 | Lazy Shell (armor) | All | Atk -50, Def +127, Mg Atk -50, Mg Def +127, Spd -50 |

#### Accessories

| ID | Name | Who can equip | Stats |
|---:|---|---|---|
| 66 | Jump Shoes | Mario | Def +1, Mg Atk +5, Mg Def +1, Spd +2 |
| 67 | Zoom Shoes | All | Def +5, Mg Def +5, Spd +10 |
| 68 | Antidote Pin | All | Def +2, Mg Def +2 |
| 69 | Wake-Up Pin | All | Def +3, Mg Def +3 |
| 70 | Trueform Pin | All | Def +4, Mg Def +4 |
| 71 | Fearless Pin | All | Def +5, Mg Def +5 |
| 72 | Safety Badge | All | Def +5, Mg Def +5 |
| 73 | Nurture Ring | Peach | — |
| 74 | Safety Ring | All | Def +5, Mg Def +5, Spd +5 |
| 75 | Signal Ring | All | — |
| 76 | Jinx Belt | All | Atk +27, Def +27, Spd +12 |
| 77 | Defense Scarf | All | Def +15, Mg Def +15 |
| 78 | Attack Scarf | Mario | Atk +30, Def +30, Mg Atk +30, Mg Def +30, Spd +30 |
| 79 | Feather | All | Def +5, Mg Def +5, Spd +20 |
| 80 | Troopa Medal | All | Spd +20 |
| 81 | Ghost Medal | All | — |
| 82 | Booster's Charm | All | Atk +7, Def +7, Mg Atk +7, Mg Def +7, Spd -5 |
| 83 | Quartz Charm | All | — |
| 84 | Exp. Booster | All | — |
| 85 | Coin Trick | Mario | — |
| 86 | Flower Ring | All | — |
| 161 | Enduring Brooch | All | — |
| 162 | Teamwork Band | All | — |
| 167 | Echo Signal Ring | All | Spd +10 |

#### Consumable items

| ID | Name | Type |
|---:|---|---|
| 87 | Mushroom | Usable in field + battle |
| 88 | Mid Mushroom | Usable in field + battle |
| 89 | Max Mushroom | Usable in field + battle |
| 90 | Yoshi Candy | Usable in field + battle |
| 91 | Tadpola Cola | Usable in field + battle |
| 92 | Frogleg Cola | Usable in field + battle |
| 93 | Finless Cola | Usable in field + battle |
| 94 | Croaka Cola | Usable in field + battle |
| 95 | Thropher Cookie | Usable in field + battle |
| 96 | Honey Syrup | Usable in field + battle |
| 97 | Maple Syrup | Usable in field + battle |
| 98 | Royal Syrup | Usable in field + battle |
| 99 | Flower Tab | Field only |
| 100 | Flower Jar | Field only |
| 101 | Flower Box | Field only |
| 102 | Pick Me Up | Battle item |
| 103 | Cleansing Juice | Battle item |
| 104 | Party Cleanse | Battle item |
| 105 | Bracer | Battle item |
| 106 | Energizer | Battle item |
| 107 | Party Bracer | Battle item |
| 108 | Party Energizer | Battle item |
| 109 | Yoshi-Ade | Battle item |
| 110 | Red Essence | Battle item |
| 111 | Pure Water | Battle item |
| 112 | Poison Mushroom | Battle item |
| 113 | Sleepy Bomb | Battle item |
| 114 | Fright Bomb | Battle item |
| 115 | Fire Bomb | Battle item |
| 116 | Ice Bomb | Battle item |
| 117 | Rock Candy | Battle item |
| 118 | Star Egg | Battle item |
| 119 | Mystery Egg | Battle item |
| 120 | Lamb's Lure | Battle item |
| 121 | Sheep Attack | Battle item |
| 122 | See Ya | Battle item |
| 123 | Earlier Times | Battle item |
| 124 | Yoshi Cookie | Battle item |
| 125 | Goodie Bag | Battle item |
| 126 | Lucky Jewel | Usable in field + battle |
| 127 | Wilt Shroom | Usable in field + battle |
| 128 | Rotten Mush | Usable in field + battle |
| 129 | Moldy Mush | Usable in field + battle |
| 130 | Mushroom (Triplets) | Usable in field + battle |

#### Key items (view-only)

| ID | Name |
|---:|---|
| 131 | Special Frog Coin |
| 132 | Wallet |
| 133 | Cricket Pie |
| 134 | Cricket Jam |
| 135 | Carbo Cookie |
| 136 | Alto Card |
| 137 | Tenor Card |
| 138 | Soprano Card |
| 139 | Bright Card |
| 140 | Microbomb |
| 141 | Fireworks |
| 142 | Shiny Stone |
| 143 | Elder Key |
| 144 | Room Key |
| 145 | Shed Key |
| 146 | Temple Key |
| 147 | Castle Key 1 |
| 148 | Castle Key 2 |
| 149 | Beetle Box (empty) |
| 150 | Beetle Box |
| 151 | Dry Bones Flag |
| 152 | Greaper Flag |
| 153 | Boo Flag |
| 154 | Seed |
| 155 | Fertilizer |
| 163 | Crystal Shard |
| 164 | Stay Voucher |
| 165 | Extra-Shiny Stone |
| 166 | Monster Trophy |
IDs 156 and 157 are unused.

## Credits

- Item IDs and names: [Echocolat/SMR-save-edit-scripts](https://github.com/Echocolat/SMR-save-edit-scripts)
- Equipment stats: [Nintendo Life](https://www.nintendolife.com/guides/super-mario-rpg-all-weapons-list), [Gamer Guides](https://gamerguides.com/super-mario-rpg-2023/guide/getting-started/basics/all-armor-in-super-mario-rpg), [Samurai Gamers](https://samurai-gamers.com/super-mario-rpg-remake/weapons-list-19/) and the [Super Mario Wiki](https://www.mariowiki.com/)

## License

[MIT](LICENSE)

Not affiliated with or endorsed by Nintendo. Super Mario RPG is a trademark of Nintendo.
