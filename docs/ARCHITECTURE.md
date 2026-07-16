# Architecture & design decisions

How Mod Organizer 2 manages mods, why The Forever Winter is an awkward fit, and
the specific choices this plugin makes.

## The pieces

```
 Steam library
   └─ common\The Forever Winter\           ← game root  (MO2 "gameDirectory")
      ├─ Windows\
      │  ├─ ForeverWinter.exe              ← EOS launcher wrapper  (GameLauncher)
      │  └─ ForeverWinter\
      │     ├─ Binaries\Win64\
      │     │  ├─ ForeverWinter-Win64-Shipping.exe   ← real game exe (GameBinary)
      │     │  ├─ dsound.dll + bitfix\     ← Signature Bypass  (MANUAL — see below)
      │     │  └─ ue4ss\ + dwmapi.dll      ← RE-UE4SS, if you use Blueprint/Lua mods
      │     └─ Content\Paks\               ← GameDataPath (USVFS overlay root)
      │        ├─ pakchunk*-Windows.pak/.ucas/.utoc(+.sig)   ← signed base game
      │        ├─ Mods\                    ← content pak mods land here
      │        └─ LogicMods\               ← Blueprint mods (UE4SS) land here
```

## How MO2 delivers mods: USVFS

MO2 does **not** copy mods into the game. It uses **USVFS** (User-Space Virtual
File System), a process-local overlay built with API hooking. When you launch the
game *through MO2*, USVFS merges every enabled mod's files on top of the
directory the plugin declares as `dataDirectory()` (our `GameDataPath`). The game
sees a combined view; the real folder on disk is never touched.

Two consequences drive almost every design decision here:

1. **Process-local.** The overlay only exists for processes MO2 starts (and their
   children). Launch from Steam/Explorer → stock game. *You must launch through
   MO2.*
2. **Data-directory-scoped.** USVFS overlays the *data directory only*. Anything a
   mod needs outside that directory — DLLs in `Binaries\Win64`, config in the game
   root — is invisible to USVFS and must be a real file (or delivered by the
   [Root Builder](https://github.com/Kezyma/ModOrganizer-Plugins) plugin).

## Why TFW is awkward

| Trait | Consequence |
|---|---|
| **Signed paks** (`.sig` on every pakchunk, enforced) | Unsigned mod paks are rejected. A **Signature Bypass** proxy DLL in `Binaries\Win64` is mandatory. |
| Bypass lives in `Binaries\Win64` | Outside `Content\Paks` → outside USVFS → can't be a normal MO2 mod. |
| Proxy DLLs load at process start | Even Root Builder / forced-load timing is unreliable → prefer a **manual** real-file install. |
| **IoStore / Zen** format | Mods are `.pak+.utoc+.ucas` trios; MO2 overlays files but never repackages. Format must match the game. |
| **EOS wrapper** launch path | Launching the shipping exe directly under MO2 may fail entitlement checks; may need to launch the wrapper and rely on child-process injection. |
| Extra `Windows\` nesting | Every path is one level deeper than generic UE templates assume. |

## Design decisions

### GameDataPath = `Windows/ForeverWinter/Content/Paks`
Modeled on the **Ready or Not** plugin (`ReadyOrNot/Content/Paks`), adjusted for
TFW's extra `Windows\` layer. MO2's data pane will show the base-game pakchunks
(cosmetic); enabled mods overlay their `Mods\…` files on top.

Alternative considered — **Silent Hill 2 Remake** style: `GameDataPath =
"%GAME_PATH%"` + a checker that moves paks into the full nested
`…/Content/Paks/~mod`. Equivalent result; we chose the narrower data root because
it keeps MO2's view scoped to the Paks folder.

### Mod folder = `Mods\` (not `~mods`)
TFW's Nexus community installs content paks into `Content\Paks\Mods` (the folder
is created manually on a stock install). UE auto-mounts any pak beneath
`Content\Paks`, so the exact subfolder name is a convention, not a requirement —
we follow the community's. Blueprint mods go in `LogicMods\` (requires UE4SS).
The `TheForeverWinterModDataChecker` relocates bare pak trios into `Mods\` and
unwraps single-folder archives.

### Signature Bypass is a documented prerequisite, not plugin-managed
Because of the outside-VFS + early-load problem, the plugin deliberately does not
try to inject the bypass. Recommended: install `dsound.dll` + `bitfix\` into
`Binaries\Win64` manually, once. Advanced alternative: a **Root Builder** mod
whose `Root\Windows\ForeverWinter\Binaries\Win64\` contains the bypass, *with
exclusions* so Root Builder doesn't cache the multi-GB `Content\Paks` data. A
third, experimental path — MO2 `executableForcedLoads()` to inject the DLL — is
noted in the plan but unproven for a signature-check proxy.

### Launch target = shipping exe, wrapper as fallback
`GameBinary` is the shipping exe (what actually mounts paks; the bypass guide
recommends launching it directly). `executables()` also exposes the EOS wrapper
for the case where a direct shipping launch is blocked by entitlement checks.

## <a name="load-order"></a>Load order

**MO2's left-pane priority controls pak mount order as of v0.2.0.** `mappings()`
deploys each enabled mod's trio as `<Name>_<N>_P.{pak,utoc,ucas}` where
`N = MO2 priority + 1`. Higher priority → higher `N` → higher mount Order → wins.

The filename is the only channel to the engine, and it reads exactly one part of
it. UE derives a pak's Order from:

- the **path bucket** — everything under `Content\Paks\` is `3`; and
- for a pak ending `_P.pak`, the **token between the last two underscores**: if it
  is numeric and ≥ 1, `ChunkVersionNumber = N + 1`, otherwise `1`. Then
  `PakOrder += 100 * ChunkVersionNumber`, and that same value is handed to the
  IoStore container mount — so the `.pak` name decides `.utoc` Order.

So `Foo_5_P.pak` lands at Order 603, and beats `Foo_2_P.pak` at 303.

> ### A numeric PREFIX does nothing. It never did.
>
> `03_AllSkills_P.pak` parses the token `"AllSkills"` — not numeric — and lands at
> Order **103**, identical to `07_Foo_P.pak`. Every prefixed mod ties, and the winner
> falls to a tiebreak: pak discovery sorts **descending**
> (`FoundPakFiles.Sort(TGreater<FString>())`), and both resolvers favour the
> **last-mounted** container, so the alphabetically **lowest** name wins — the exact
> opposite of what a prefix scheme intends.
>
> Measured 2026-07-16, all carrying the same package, winner read from the live table
> via TFWWorkbench's `DumpDataTables`: `03_AllSkills_P` beat `06_`/`07_` fixtures, and
> `05_A` beat `06_B`. **The prefix controlled nothing while appearing to work.**
> Do not reintroduce it — and do not copy the FF7 Remake plugin's ascending prefix
> here: that is a *legacy PakFile* game, where the rule genuinely differs.

**Confirmed in-game**, same day: `ZZ_ConflictTestB_7_P` (Order 803) beat
`ZZ_ConflictTestA_6_P` (Order 703), 48 rows to 0 — *despite* B sorting alphabetically
later, so it mounted first and lost the tiebreak. Only Order can produce that.

Mechanism verified against UE 5.4 source (`FPakPlatformFile::Mount`,
`FFileIoStore::Mount`/`Resolve`). Blueprint mods under `LogicMods\` are left alone —
no `_P`, no number; UE4SS orders those itself.
