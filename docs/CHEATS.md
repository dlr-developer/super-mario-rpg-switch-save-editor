# 🎮 Cheat guide

> [!WARNING]
> **Cheats are experimental.** A code made for a different game version, or one that doesn't suit your emulator, can do nothing, crash the game, or corrupt your save. **Back up your save before using cheats.** The editor's **Back up now…** button does this in one click.

- [How cheats work](#how-cheats-work)
- [Will a code work for me?](#will-a-code-work-for-me)
- [Using cheats with the editor](#using-cheats-with-the-editor)
- [The cheat library](#the-cheat-library)
- [Where the files go](#where-the-files-go)
- [Code format](#code-format)
- [Making your own cheats](#making-your-own-cheats)
- [Troubleshooting](#troubleshooting)

---

## How cheats work

While the game runs, everything it keeps track of (HP, coins, items, the next bonus flower) is a number stored somewhere in memory. A cheat is a short list of instructions such as *"write 9999 at this address"*. The emulator, or Atmosphère on a real Switch, has a small cheat engine that repeats those instructions many times a second, so the value stays locked even when the game tries to change it.

| | Save editor | Cheats |
|---|---|---|
| Changes | Your save file, once | The game's memory, continuously |
| Lasts | Permanently | Only while the cheat is on* |
| Tied to a game version | No | **Yes** (build ID) |
| Can do | Coins, stats, items, gear | Also things a save can't hold: infinite HP in battle, EXP multipliers, damage changes |

\* If you save the game while a cheat is on, whatever it changed (like 9999 coins) is saved too.

---

## Will a code work for me?

### Game version (build ID)

Every code is written for **one exact build** of the game. After an update, the game's code moves around and old addresses point at the wrong data.

| Game version | Build ID |
|---|---|
| v1.0.0 | `E968832CADE2AD7C` |

The Cheats tab reads your build ID from Ryujinx's log. You can also see it in Ryujinx under right-click → **Manage Cheats**. Cheat files are named after the build ID, for example `E968832CADE2AD7C.txt`.

### Emulator or console

All of these use the same **Atmosphère cheat format**:

| Where | Supported | Notes |
|---|---|---|
| Ryujinx and its forks (Ryubing, Nextendo, …) | ✅ | The editor installs cheats and switches them on automatically |
| yuzu family: yuzu, suyu, sudachi, citron, eden, torzu | ✅ | Enable the **SMR Save Editor Cheats** add-on once in the game's properties |
| Real Switch with Atmosphère | ✅ | Use **Export for Switch (SD card)** |
| Android emulators | ✅ | Copy the exported file to the emulator's `load` folder yourself |

Most codes work everywhere, but emulators don't behave identically, so **test a code before relying on it**.

---

## Using cheats with the editor

1. **Back up your save:** click **Back up now…** at the top of the window.
2. **Get a code** made for your build ID, for example from [CheatSlips](https://www.cheatslips.com/game/super-mario-rpg), or make your own (see below).
3. On the **Cheats** tab, click **Import cheat file…**, or **Add cheat…** and paste the code.
4. **Turn on** the cheats you want: double-click a row, or select rows and click **Turn on/off**.
5. Click **Install to emulator** (or **Export for Switch (SD card)…**).
6. **Restart the game.** Cheats are loaded when the game starts.

To stop a cheat, turn it off and click **Install to emulator** again, or click **Remove from emulator**. Your list stays in the app either way.

---

## The cheat library

Every cheat you add in the editor is saved in the **`cheats`** folder next to the app, filed by game version:

```
cheats/0100BC0018138000 - Super Mario RPG/v1.0.0 - E968832CADE2AD7C/
    E968832CADE2AD7C.txt   info.json   README.md
```

Only the game version gets its own folder. Emulators and Switch firmware don't, because one code file works on all of them. Instead, each cheat records where it was **tested**: Ryujinx, the yuzu family and Switch, each marked ✅ works, ❌ doesn't work or ❔ untested. Set these in **Add cheat…** / **Edit…**. **Open cheats folder** on the Cheats tab takes you there. See [cheats/README.md](../cheats/README.md) for the full layout.

---

## Where the files go

| Where | File |
|---|---|
| Ryujinx | `mods\contents\0100bc0018138000\SMR Save Editor Cheats\cheats\<build ID>.txt`, plus a line per cheat in `mods\contents\0100bc0018138000\cheats\enabled.txt` |
| yuzu family | `load\0100BC0018138000\SMR Save Editor Cheats\cheats\<build ID>.txt` |
| Switch | `atmosphere/contents/0100BC0018138000/cheats/<build ID>.txt` on the SD card |

The editor only ever writes its own cheat file and its own lines in `enabled.txt`, so cheats you installed another way are left alone.

---

## Code format

```
[Cheat name]
04000000 01234567 0000270F

{Master code name}
580F0000 01AABBCC
```

*These are format examples, not real codes for this game.*

- `[Name]` starts a cheat, and the lines below it are its instructions.
- `{Name}` is a **master code**. Some cheats need it turned on too.
- Each instruction is groups of **8 hexadecimal digits**.

How a simple line reads, using `04000000 01234567 0000270F`:

| Part | Meaning |
|---|---|
| `0` (first digit) | Instruction type: write a value to memory |
| `4` | Write 4 bytes |
| `0` | In the game's main program area |
| `01234567` | At this address |
| `0000270F` | The value: hex `270F` = 9999 |

Real cheats often chain several lines. For example, they read where the party data currently lives, add an offset, and write there, because a lot of game data moves around between sessions.

---

## Making your own cheats

The usual way to find a value is a **memory search** on a Switch running Atmosphère with a tool such as **Breeze** or **EdiZon SE**:

1. **Search for a number you can see.** You have 1,592 coins, so search memory for `1592`. You'll get thousands of matches.
2. **Change it in game.** Buy something so you have 1,500, then search the previous matches for `1500`.
3. **Repeat** until only a few addresses are left.
4. **Test** each one by editing or freezing it. The one that changes your coins on screen is the right one.
5. **Make it reliable.** If the address changes after a restart, run a **pointer search** to find a fixed path to the value.
6. **Save it as a cheat.** The tool writes the Atmosphère code. Import that file into the editor.

On emulators the same idea works with Cheat Engine attached to the emulator, but you have to convert the PC's memory addresses into the Switch's addresses, which is harder.

Behaviour changes (for example *"always get the Attack Up bonus after a battle"*) aren't stored values a memory search can find. They mean disassembling the game's code (with a tool like Ghidra), finding the instruction that makes the choice, and patching it. That's advanced reverse-engineering.

---

## Troubleshooting

| Problem | What to try |
|---|---|
| The cheat does nothing | Check the build ID matches your game version. Restart the game after installing. On yuzu-family emulators, make sure the **SMR Save Editor Cheats** add-on is enabled. |
| Ryujinx says *"no executable matches its BuildId"* | The code was made for a different game version. |
| The game crashes or freezes | Close it, turn the cheat off, click **Install to emulator**, and restore your backup from **Restore a backup…**. |
| Stats or items look wrong after saving | Restore the backup you made before using the cheat. |
