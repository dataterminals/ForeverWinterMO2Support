# Plan

Where this stands and what it takes to get from "plugin loads" to "mods
demonstrably work through MO2, with load order and a clean install story."

## Current state (v0.1.0)

- [x] Repo scaffolded; plugin authored against the locally-installed
      `basic_games` API (MO2 2.5.2, PyQt6).
- [x] Verified-on-disk facts baked in: Steam App ID `2828860`, the `Windows\`
      nesting, shipping exe + EOS wrapper paths, `Content\Paks` data root, save /
      ini / documents locations, signed paks.
- [x] `TheForeverWinterModDataChecker` normalises Nexus archives into `Mods\`.
- [x] **Validated end-to-end on 2026-07-12 — it works.** See results below.

## Validation results (2026-07-12)

Ran Phases 1–3 on the live install. Outcome: **a content asset-replacement mod,
enabled in MO2, renders in-game.** The full pipeline (detect → plugin → install
to `Mods\` → shipping-exe launch → signature bypass → USVFS overlay → in-game) is
proven.

Confirmed facts (previously open questions):

- **Launch target:** the **shipping exe launches directly under MO2** and boots
  fine — EOS/entitlement did **not** block it. `GameBinary` (shipping) stays the
  default; the EOS-wrapper entry is just a fallback we didn't need.
- **`GameDataPath = Content/Paks` is fine for MO2 itself** — MO2 handled the large
  data dir and settled to ~35 MB / Responding once launch finished.
- **The slow/"frozen" launch was the Root Builder plugin**, not this plugin. Its
  log showed `Generating root mod build data` / `Updating cache` / `Checking for
  updates to backup files`, churning the ~60 GB game folder before the game
  started. See Phase 4 — for TFW (manual bypass, no root-mods) Root Builder has
  nothing useful to do and should be excluded/disabled for this instance.

Still to do: the negative-control check (launch from Steam → confirm mod is
absent, proving nothing was written to the game folder) and the Root Builder
cleanup.

## Phase 1 — Plugin loads & game is detected

**Goal:** TFW appears in MO2's game list and an instance can be created.

1. Run `scripts/install-plugin.ps1` (copies the plugin into `C:\Modding\MO2` and
   `F:\Modding\MO2`).
2. Restart MO2 → *Create new instance* → confirm **The Forever Winter** is offered
   and auto-resolves to `…\common\The Forever Winter`.
3. If it does **not** appear: check `%LOCALAPPDATA%\ModOrganizer\…\logs\` for a
   plugin load error. Most likely cause = PyQt5/PyQt6 mismatch or an import typo.

**Exit criteria:** instance created, game root correct, no plugin errors in log.

## Phase 2 — Content pak mod installs cleanly

**Goal:** a real Nexus content pak, installed through MO2, lands in `Mods\`.

1. Install the **Signature Bypass** (Nexus mod 57) into `Binaries\Win64` manually.
   Launch from Steam once to confirm the game still boots with the bypass present.
2. In MO2, install a small known content pak (e.g. a UI or texture mod).
3. Confirm the mod-data checker put the trio under `Mods\` (check the mod's file
   tree in MO2's right pane, *Filetree* tab). Fix checker globs if a real archive
   layout slips through.

**Exit criteria:** mod shows as valid; its `.pak/.utoc/.ucas` sit under `Mods\`.

## Phase 3 — Mods actually load in-game (the real test)

**Goal:** prove USVFS + the bypass deliver the mod to the running game.

1. Launch **The Forever Winter** (shipping exe entry) **from MO2**.
   - If it refuses to boot → switch to the *EOS launcher* entry and retry.
   - Watch for the EOS/entitlement failure mode; note which entry works.
2. Confirm the test mod is visibly active in-game.
3. **Negative control:** launch the game from Steam directly → confirm it is
   *unmodded* (proves USVFS did the overlay and nothing was written to disk).

**Exit criteria:** mod visible when launched via MO2, absent when launched via
Steam. This is the make-or-break milestone.

## Phase 4 — Binaries payload via Root Builder (optional, quality-of-life)

**Goal:** manage the Signature Bypass (and UE4SS) inside MO2 instead of manually.

1. Install the Root Builder MO2 plugin.
2. Package the bypass as a mod with
   `Root\Windows\ForeverWinter\Binaries\Win64\{dsound.dll, bitfix\}`.
3. Add Root Builder **exclusions** for `Content\Paks` so it doesn't cache the
   multi-GB base data (the Oblivion Remastered plugin documents this exact trap).
4. Decide: is Root Builder more reliable than the manual copy given the early-DLL
   load timing? If not, keep manual as the recommended path and treat this as
   advanced/optional.

## Phase 5 — Load order (enhancement)

**Goal:** make MO2's left-pane priority control pak mount order.

- Implement `IPluginFileMapper.mappings()` (FF7 Remake pattern) to deploy each
  enabled mod's `.pak/.utoc/.ucas` into `Content\Paks\Mods\` with a numeric
  filename prefix derived from MO2 priority — preserving the shared base name
  across the trio.
- Until then, document naming-based ordering (`_P` suffix / prefixes) as the
  supported mechanism.

## Phase 6 — Polish & release

- Save-game handling decision (see open questions): the real progress save is a
  hashed `<guid>.dat`, which `GameSaveExtension="sav"` won't capture.
- Author a short wiki-style install guide; consider upstreaming
  `game_theforeverwinter.py` to `modorganizer-basic_games` if it proves out.
- Version bump, tag, done.

## Open questions (need a live machine / testing)

1. **PyQt binding** — confirm the installed `plugins\basic_games\basic_game.py`
   imports PyQt6 (it does on 2.5.2 per our read). A wrong binding = silent load
   failure. ✅ mostly resolved, re-verify if MO2 updates.
2. **Launch injection** — does the shipping exe boot directly under MO2 with EOS,
   or must we launch the wrapper? *Only a live test answers this.*
3. **Root Builder reliability** for the early-loading bypass DLL vs. a plain manual
   copy.
4. **Mod folder convention** — `Mods\` chosen; confirm no TFW mod expects loose
   paks directly in `Content\Paks` or a different subfolder.
5. **Save management** — track `.sav` settings only, or handle the `<guid>.dat`
   progress save specially, or leave save profiles off?
6. **Scope** — content paks only, or also UE4SS Lua/Blueprint (LogicMods)? The
   latter pulls in the RE-UE4SS payload and more Binaries\Win64 juggling.

## Non-goals (for now)

- Repackaging/re-signing mods (MO2 overlays files; it does not build paks).
- Replacing the community Vortex extension — this is an alternative for MO2 users.
- Anything that writes into the game folder as a side effect.
