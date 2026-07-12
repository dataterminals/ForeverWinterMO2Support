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

## <a name="load-order"></a>Load order — the honest version

Loose IoStore paks have **no MO2-driven load order**. UE mounts paks by name;
MO2's left-pane priority does *not* translate into pak mount priority. Conflicts
between two paks that touch the same asset are resolved by:

- the **`_P` patch suffix** (a `_P` pak mounts over non-`_P` paks), and
- **alphabetical / numeric-prefix** naming.

A future enhancement (see [`docs/PLAN.md`](PLAN.md)) can bridge MO2 priority →
pak mount order by deploying each enabled mod's paks with a numeric filename
prefix via `IPluginFileMapper` (the approach the FF7 Remake plugin uses). Until
then: **rename conflicting paks** rather than relying on the MO2 order.
