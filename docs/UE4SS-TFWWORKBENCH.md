# UE4SS & TFWWorkbench under MO2

Answers [`PLAN.md`](PLAN.md) open question 6 (*"content paks only, or also UE4SS
Lua/Blueprint?"*) with a live test: **it works, and it is worth supporting** — but two
prerequisites are non-obvious, and both fail *silently* or with a misleading error.

Verified end-to-end on the dev box **2026-07-16** with UE4SS `v3.0.1-894-g2172883` +
TFWWorkbench `0.2.1` (the pin from
[tfworkbench-compat-research](https://github.com/dataterminals/tfworkbench-compat-research)).

> **Scope: this describes the `feature/load-order-mapper` plugin (v0.2.0+).** §3's Overwrite
> path depends on `mappings()` and `GameDataPath = "_ROOT"`, which exist only on that branch.
> On `main` (`GameDataPath = Content/Paks`, no `mappings()`) Overwrite overlays the data
> directory by the ordinary USVFS route, so the tree goes one level deeper —
> `overwrite\Mods\TFWWorkbench\DataTable\…`. §1 and §2 apply to both.

---

## Summary

| # | Prerequisite | Fails how |
|---|---|---|
| 1 | **Root Builder must be ENABLED** | Silently. Nothing deploys; no error anywhere. |
| 2 | **TFWWorkbench's `DataTable\` tree must be pre-created in Overwrite** | Lua stack trace at `main.lua:100`, blaming a nil that is three call frames from the real cause. |

Neither is discoverable from the game, the logs, or the mod's README.

---

## 1. Root Builder is required — and earlier advice here said to disable it

UE4SS and the Signature Bypass live in `Binaries\Win64`, **outside** the directory USVFS
overlays. Only Root Builder can deliver them (see
[`ARCHITECTURE.md`](ARCHITECTURE.md)). Once you add UE4SS/TFWWorkbench, three of your mods
are `Root\` mods and Root Builder stops being optional.

> ⚠️ **Stale advice, now corrected.** [`PLAN.md`](PLAN.md) has recorded since 2026-07-12:
> *"for TFW (manual bypass, no root-mods) Root Builder has nothing useful to do and should
> be excluded/disabled for this instance."*
>
> That was right **for a content-paks-only setup**. It is **wrong the moment you add UE4SS**,
> and it caused a real multi-hour debugging session on 2026-07-16: Root Builder was disabled
> per that note, so UE4SS never reached the game, and **nothing logged a single complaint.**

Check `%LOCALAPPDATA%\ModOrganizer\<instance>\ModOrganizer.ini`:

```ini
[PluginPersistance]
RootBuilder\enabled=true          ; and the five RootBuilder <Tool>\enabled keys
```

MO2 only writes these keys once they have been changed from default — so an instance where
Root Builder has never been touched has **no such lines at all**. Their presence set to
`false` means someone turned it off deliberately.

### The cost this advice was avoiding is real

The original note was reacting to a genuine problem: Root Builder in copy mode caches the
whole game folder. On the dev box that backup is **48.4 GB** of real file copies under
`<MO2>\plugins\data\RootBuilder\<mangled-game-path>\Backup\`. Do
[`PLAN.md`](PLAN.md) Phase 4 step 3 — add exclusions for `Content\Paks` — rather than
disabling the plugin.

> **Also check what your baseline captured.** Root Builder snapshots "vanilla" the first time
> it builds. If the bypass was already installed manually, `dsound.dll` / `bitfix\` get
> recorded *as base-game files* — and a Clear then restores them into the game folder
> permanently, outside MO2's control. Verified on the dev box: its Backup contains all three.

---

## 2. TFWWorkbench cannot create its own directories under MO2

TFWWorkbench keeps its JSON mod data in a tree under `Content\Paks\Mods\TFWWorkbench\`. On
first run it tries to build that tree itself — with `os.execute`:

```lua
-- Scripts/main.lua:88  (TFWWorkbench 0.2.1)
local success, result, code = os.execute(string.format("mkdir \"%s\\TFWWorkbench\"",
    dirs.Game.Content.Paks.Mods.__absolute_path))
```

`os.execute` spawns a **cmd.exe child process**. Under MO2 that child dies instantly:

```
[Lua] [TFWWorkbench:main] No such directory …\Content\Paks\Mods/TFWWorkbench
[Lua] [TFWWorkbench:main] Creating directory …\Content\Paks\Mods/TFWWorkbench
[Lua] [TFWWorkbench] Failed to create directory: exit - -1073741819
Error: [Lua::call_function] lua_pcall returned LUA_ERRRUN =>
    …\Scripts\main.lua:100: attempt to index a nil value (local 'modDir')
stack traceback:
    …\Scripts\main.lua:100: in upvalue 'CreateModChildDirs'
    …\Scripts\main.lua:289: in function <…\Scripts\main.lua:286>
```

`-1073741819` is `0xC0000005` — **STATUS_ACCESS_VIOLATION**. The spawned process crashes;
`os.execute` returns falsy; `FindOrCreateModDir()` returns `nil`; and
`CreateModChildDirs(nil)` then dereferences it at line 100. **The reported error is three
frames downstream of the real fault**, which is why this reads as a TFWWorkbench bug rather
than an environment one.

> **Verified:** the crash, the exit code, and the causal chain to `main.lua:100`.
> **Inferred:** *why* the child crashes. The likely mechanism is USVFS hooking
> `CreateProcess` and injecting into the cmd.exe child. Not proven — what is proven is that
> **spawning a shell from UE4SS Lua under MO2 access-violates**, reproducibly.

This is MO2-specific. The same TFWWorkbench build on a plain, non-MO2 install creates its
tree without complaint — which is why
[ForeverWinterModSetup](https://github.com/dataterminals/ForeverWinterModSetup) (the no-MO2
path) never hit this.

### The fix: pre-create the tree, and `os.execute` is never needed

If the tree already exists, `GetModDir()` returns it and the `os.execute` path is never
entered. The remaining calls inside `CreateModChildDirs` then degrade to harmless no-ops —
a crashed `if exist` probe returns falsy, which **skips** the mkdir rather than erroring.

Create this under **MO2's Overwrite folder** (see §3 for why):

```
<instance>\overwrite\
└─ TFWWorkbench\
   └─ DataTable\            ← SINGULAR. Upstream's README says "DataTables"; the code disagrees.
      ├─ Item\
      ├─ ItemValue\
      ├─ CraftingRecipe\
      ├─ CraftingGroup\
      ├─ VendorData\
      ├─ WeaponsDetailsData\
      ├─ WeaponPartStatsData\
      └─ Dumps\             ← output dir, nested INSIDE DataTable\
```

PowerShell, against the instance's `overwrite\`:

```powershell
$ow = "<instance>\overwrite"
@("Item","ItemValue","CraftingRecipe","CraftingGroup",
  "VendorData","WeaponsDetailsData","WeaponPartStatsData","Dumps") |
  ForEach-Object { New-Item -ItemType Directory -Force -Path "$ow\TFWWorkbench\DataTable\$_" }
```

The list is not arbitrary — it is `Settings.ModChildDirs` in TFWWorkbench's own
`Scripts/Settings.lua`. Read it there if a future release changes it.

> **Why pre-creation is required and not just faster:** TFWWorkbench snapshots the directory
> tree *before* creating its own children, so even a tree built successfully on first launch
> is not read until the **second**. Pre-creating makes the first launch work.

---

## 3. Why the tree must go in Overwrite specifically

Not a workaround — it is the channel this plugin deliberately provides:

```python
# games/game_theforeverwinter.py — mappings()
mobase.Mapping(
    self._organizer.overwritePath(),
    str(mods_dir),          # …\Content\Paks\Mods
    True,                   # isDirectory
    True,                   # createTarget
)
```

Overwrite is mapped **as a whole directory** onto `Content\Paks\Mods\`, so arbitrary
structure inside it reaches the game.

A normal MO2 mod **will not work** for this. The same `mappings()` filters to pak trios:

```python
if not f.is_file() or f.suffix.lower() not in _IOSTORE_EXTS:
    continue
```

`_IOSTORE_EXTS` is `(".pak", ".utoc", ".ucas")` — so a mod containing only empty directories
maps **nothing at all**, silently. Overwrite is the only route for non-pak structure.

Consequence worth stating plainly: **this tree is not junk in Overwrite — do not "clean" it.**
That inverts the usual MO2 advice, and it is a direct result of this plugin's design.

### Overwrite will also collect UE4SS's own output

With Root Builder's `redirect=true`, anything the game writes into its root lands in
`overwrite\Root\…`. So Overwrite ends up holding two unrelated things at once:

```
overwrite\
├─ TFWWorkbench\DataTable\…                        ← input  (you create this)
└─ Root\Windows\ForeverWinter\Binaries\Win64\
   ├─ ue4ss\UE4SS.log                              ← output (the game writes this)
   └─ bitfix.txt
```

Because Overwrite is *also* mapped onto `Content\Paks\Mods\`, that `Root\` subtree surfaces
at `Content\Paks\Mods\Root\…` at runtime. Harmless — it contains no paks, and UE mounts by
pak file — but it looks alarming and is worth knowing before you go hunting.

---

## Verifying it worked

Read the log MO2 catches at
`<instance>\overwrite\Root\Windows\ForeverWinter\Binaries\Win64\ue4ss\UE4SS.log`.

A healthy first launch:

```
UE4SS - v3.0.1 Beta #0 - Git SHA #2172883                          ← your pinned build
Mod 'TFWWorkbench' has enabled.txt, starting mod.
[TFWWorkbench] Registered Lua functions for mod                    ← main.dll loaded
[Lua] [TFWWorkbench:main:CollectData] Collecting data from …\DataTable\Item
                                                    (… all 7 collect folders …)
[Lua] [TFWWorkbench:main:LoadDataTableAssets] Successfully loaded data table asset
```

All **7** collect folders on the *first* launch is the signal the pre-create worked
(7 sources + `Dumps` as output = the 8 dirs above).

### Log-reading traps

| Trap | Reality |
|---|---|
| Grepping `Starting C++ mod` to prove main.dll loaded | **Appears in ZERO logs**, including provably-working ones. Guaranteed false negative. Use **`[TFWWorkbench] Registered Lua functions for mod`** — no `[Lua]` prefix ⇒ emitted by `main.dll`. |
| Grepping bare `0x7f` for the load error | Matches inside every `0x7ff6…` address the scanner prints. Search the bracketed **`[0x7f]`**. |
| `[PS] Failed to find FUObjectHashTables::Get()` | Benign scanner noise — present in known-good logs. |
| `DumpFile: …json` lines ⇒ files were written | No. That is the `DataTable:new` **constructor** announcing a path. The write is in `DumpDataTable()`, which the normal flow never calls. 20 `DumpFile:` lines and 0 files on disk is **correct**. |
| Trusting a `UE4SS.log` you found | Check its paths resolve on *your* machine. Mod archives ship their packager's logs, and Overwrite never self-clears — a foreign log can sit there looking authoritative indefinitely. Identify a local build by hashing `UE4SS.dll`, not by reading a log. |

---

## Scope recommendation

Support it. The plugin already routes `LogicMods\` correctly and already exposes the
Overwrite channel these mods need; what was missing was **documentation of two silent
prerequisites**, not code. Nothing here requires a plugin change.

Open, if this is ever upstreamed: pre-creating a third-party mod's directory tree is
arguably the plugin's job (a `mappings()` entry, or `createTarget` on a synthesized path)
rather than the user's. Deliberately left manual for now — it hard-codes another mod's
internal layout, and TFWWorkbench 0.2.1 is unmaintained (5 releases, all Jan 2026).
