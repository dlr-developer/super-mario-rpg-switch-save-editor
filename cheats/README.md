# 🎮 Cheat library

> [!WARNING]
> Cheats are **experimental**. A code only works for the exact game version it was made for, and a mismatched code can crash the game or corrupt your save. **Back up your save first.** See the [cheat guide](../docs/CHEATS.md).

Cheats are filed by **game**, then by **game version (build ID)**:

```
cheats/
└── 0100BC0018138000 - Super Mario RPG/
    └── v1.0.0 - E968832CADE2AD7C/
        ├── E968832CADE2AD7C.txt   ← all cheats for this version (Atmosphère format)
        ├── info.json              ← what each cheat does, who made it, where it was tested
        └── README.md              ← a readable table of the above
```

## Why only by version?

| What | Needs its own folder? | Why |
|---|---|---|
| **Game version (build ID)** | ✅ Yes | Codes point at memory addresses that move with every game update |
| Emulator (Ryujinx, yuzu family) or Switch | ❌ No | They all run the same Atmosphère cheat format, so one file works everywhere. Each cheat records where it was **tested** instead: ✅ works · ❌ doesn't work · ❔ untested |
| Switch firmware | ❌ No | Cheats talk to the game, not the system |

## Using a cheat file

- **With the editor:** on the **Cheats** tab, click **Import cheat file…** and pick the `.txt` inside the version folder. The descriptions and test results in `info.json` come along too.
- **By hand:** copy the `.txt` into your emulator's cheat folder. The [cheat guide](../docs/CHEATS.md#where-the-files-go) lists where that is.

## Adding cheats

Cheats you add in the editor are filed here automatically, in the right version folder, along with their descriptions and test results. To share them, commit the folder or open a pull request. Please fill in **What it does** and **Tested on** for every cheat.
