# Research notes

Sourced findings behind the design. Collected 2026-07-12 from the MO2
`basic_games` source, MO2/USVFS docs, and the TFW Nexus modding community, plus
direct inspection of the local install.

## MO2 Basic Games framework

- Support for a non-Bethesda game = **one Python class** subclassing `BasicGame`
  (which is itself a full `mobase.IPluginGame`). No JSON/metadata authoring path
  exists — the subclass is the only model.
  <https://github.com/ModOrganizer2/modorganizer-basic_games>
- File goes in `<MO2>\plugins\basic_games\games\game_<name>.py`; imports use
  `from ..basic_game import BasicGame`.
- **Required** attributes: `Name`, `Author`, `Version`, `GameName`,
  `GameShortName`, `GameBinary`, `GameDataPath`. Everything else (store IDs,
  docs/saves/ini paths, Nexus name) is optional.
- `GameDataPath` → `dataDirectory()` = `gameDirectory().absoluteFilePath(<path>)`.
  This is the root USVFS overlays enabled mods onto.
- `GameSteamId` enables auto-detection in the new-instance wizard (`detectGame()`
  matches the ID against detected Steam installs → `setGamePath()`).
- Placeholders in string attributes: `%GAME_PATH%`, `%DOCUMENTS%`,
  `%GAME_DOCUMENTS%`, `%USERPROFILE%`.
- **PyQt5 vs PyQt6** is the #1 silent-failure gotcha. MO2 2.5.x/2.6 = PyQt6
  (matches the locally installed 2.5.2). Older MO2 = PyQt5.
- Extra features (`BasicModDataChecker`, save-game info) register inside an
  overridden `init(self, organizer)` via `self._register_feature(...)`.

**UE templates in the repo** (our models):
- `game_readyornot.py` (UE4): `GameDataPath = "ReadyOrNot/Content/Paks"`, shipping
  exe + launcher pattern.
- `game_silenthill2remake.py` (UE5): `GameDataPath = "%GAME_PATH%"` + a
  `BasicModDataChecker` that relocates loose `.pak` into
  `SHProto/Content/Paks/~mod`.
- `inzoi.py` (UE5, present in the *local* install): `%GAME_PATH%` +
  ModDataChecker routing paks to `BlueClient/Content/Paks/~mods`, plus
  `executableForcedLoads()` for the UE4SS `dwmapi.dll`.

## UE4/UE5 modding through MO2

- IoStore mods = `.pak + .utoc + .ucas` trio sharing one base name. UE
  auto-mounts any pak found under `<Project>/Content/Paks/` (incl. subfolders) at
  start-up — no loader needed for content/asset paks.
  <https://gbatemp.net/threads/how-to-unpack-pack-utoc-ucas-in-unreal-engine-4-5-games.666431/>
- **Blueprint / "Logic" mods** need **RE-UE4SS** (its `BPModLoaderMod` scans
  `Content\Paks\LogicMods`). Logic mods must **not** use the `_P` suffix.
  <https://pwmodding.wiki/docs/developers/ue4ss-modding/logic-mods/introduction>
- **USVFS** = process-local overlay via API hooking; only visible to processes MO2
  launches (and children). Game must be launched through MO2.
  <https://github.com/ModOrganizer2/usvfs> ·
  <https://vivanewvegas.moddinglinked.com/mo2.html>
- MO2 virtualizes only the data dir → files needed in the game root / Binaries
  (loader DLLs, bypass) need **Root Builder**.
  <https://github.com/Kezyma/ModOrganizer-Plugins>
- Signed/encrypted games: AES-256 encrypts the pak index, RSA signs paks; a
  hook-based **signature-check bypass** loaded via a proxy DLL (dsound/version)
  permits unsigned paks. <https://www.nexusmods.com/site/mods/1416>
- **No real load order** for loose paks — mount order is by name / `_P` suffix /
  numeric prefixes, not the MO2 left pane. (Oblivion Remastered's plugin loads in
  reverse-alphabetical order and numbers pak groups to force order.)

## The Forever Winter specifics

- **Steam App ID `2828860`**, UE **5.4.2**, dev Fun Dog Studios.
  <https://store.steampowered.com/app/2828860/>
- **Nexus** is the hub (~100+ mods); **no Thunderstore** community found.
  <https://www.nexusmods.com/games/theforeverwinter>
- Mods = IoStore `.pak/.utoc/.ucas` trios (+ UE4SS script/Blueprint mods).
- **Content pak install path:** `…\Windows\ForeverWinter\Content\Paks\Mods`
  (**created manually**; absent on stock install).
  <https://www.nexusmods.com/theforeverwinter/mods/56>
- **Blueprint mods:** `…\Content\Paks\LogicMods` (exists, empty on stock install).
- **Signed paks → Signature Bypass required:** every pak has a `.sig`. The bypass
  is a proxy `dsound.dll` (or `version.dll` if you need in-game voice) + `bitfix\`,
  copied into `Binaries\Win64`; it disables the signature check. Game "generally
  must be launched directly via `ForeverWinter-Win64-Shipping.exe`."
  <https://www.nexusmods.com/theforeverwinter/mods/57>
- **RE-UE4SS:** UE5.4-capable build; `ue4ss\` + `dwmapi.dll` go next to the
  shipping exe in `Binaries\Win64`. <https://www.nexusmods.com/theforeverwinter/mods/61>
- **TFWWorkbench:** community framework container placed in `Content\Paks\Mods`;
  common dependency. <https://www.nexusmods.com/theforeverwinter/mods/77>
- **A Vortex extension already exists** (Nexus mod 121) that auto-installs UE4SS +
  Signature Bypass + TFWWorkbench. **No MO2 usage/discussion was found** — this
  plugin is first-of-kind.

## Verified locally (this machine, 2026-07-12)

| Fact | Value |
|---|---|
| Game root | `D:\SteamLibrary\steamapps\common\The Forever Winter` |
| Shipping exe | `Windows\ForeverWinter\Binaries\Win64\ForeverWinter-Win64-Shipping.exe` |
| EOS launcher | `Windows\ForeverWinter.exe` |
| Paks | `Windows\ForeverWinter\Content\Paks\` — signed (`.sig` present), IoStore |
| `LogicMods\` | present, empty; no UE4SS / bypass installed by default |
| Documents | `%LOCALAPPDATA%\ForeverWinter\` |
| Ini | `…\Saved\Config\Windows\GameUserSettings.ini` (no `Game.ini`) |
| Saves | `…\Saved\SaveGames\*.sav` (settings) + hashed `<guid>.dat` (progress) |
| MO2 installs | `C:\Modding\MO2` and `F:\Modding\MO2` — both v2.5.2, PyQt6, `basic_games` bundled (62 games) |
| MO2 instances present | Cyberpunk 2077 (basic_games already in active use) |

> Caveats from the research pass: the `ForeverWinter.uproject` name is inferred
> from the module name; the Signature Bypass and Vortex Nexus pages returned HTTP
> 403 to direct fetch (behavior corroborated via search snippets); Thunderstore
> absence is a negative finding, not a proof.
