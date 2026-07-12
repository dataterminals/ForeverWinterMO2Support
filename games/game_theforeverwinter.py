# The Forever Winter — Mod Organizer 2 support plugin (Basic Games framework)
#
# Drop this file into:  <MO2>\plugins\basic_games\games\game_theforeverwinter.py
#
# Target: MO2 2.5.x  (PyQt6 / mobase). On an older PyQt5 build, change the
#         PyQt6 imports below to PyQt5.
#
# ---------------------------------------------------------------------------
# IMPORTANT — read before expecting mods to load:
#
# The Forever Winter ships *signed* paks (every pakchunk*-Windows.pak has a
# matching .sig, and the engine enforces the signature). An unsigned mod pak
# will be silently rejected UNLESS a community "Signature Bypass" proxy DLL
# (dsound.dll + a bitfix\ folder) is present in:
#     <game>\Windows\ForeverWinter\Binaries\Win64\
# That folder is OUTSIDE the directory MO2 virtualizes, so the bypass must be a
# real file there (install it manually, or via the Root Builder plugin). This
# plugin manages the content paks; it does not install the bypass. See README.
# ---------------------------------------------------------------------------
#
# LOAD ORDER
# ----------
# Unreal mounts loose paks by filename, so raw mod names give you no real load
# order. To make MO2's left-pane priority mean something, this plugin does NOT
# rely on the plain USVFS overlay. Instead it uses IPluginFileMapper: every
# enabled mod's pak trio is mapped into Content\Paks\Mods\ with a zero-padded
# numeric prefix derived from MO2 priority (00_, 01_, ...). Higher MO2 priority
# => higher number => mounts later => wins conflicts. GameDataPath is therefore
# a dead placeholder ("_ROOT"); all real placement happens in mappings().

import mobase
from pathlib import Path
from typing import Iterable, List

from PyQt6.QtCore import QFileInfo

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame

# Paths relative to the Steam game root. Note TFW's extra "Windows" platform
# layer that the generic UE templates (Ready or Not, Silent Hill 2) lack.
_PAKS_ROOT = ("Windows", "ForeverWinter", "Content", "Paks")
_MODS_SUBFOLDER = "Mods"          # loose content paks (community convention)
_LOGICMODS_SUBFOLDER = "LogicMods"  # UE4SS Blueprint / "Logic" mods

# IoStore (Zen) mod payloads travel as a trio sharing one base name.
_IOSTORE_EXTS = (".pak", ".utoc", ".ucas")


class TheForeverWinterModDataChecker(BasicModDataChecker):
    """Validates archive layout and strips junk. Placement into the game is done
    by TheForeverWinterGame.mappings(), which finds pak files anywhere in the
    mod, so this checker is permissive: a mod is valid if it carries pak files
    at its root or a Mods\\ / LogicMods\\ folder."""

    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "*.pak",
                    "*.utoc",
                    "*.ucas",
                    _MODS_SUBFOLDER,
                    _LOGICMODS_SUBFOLDER,
                    "meta.ini",
                ],
                delete=[
                    "*.txt",
                    "*.md",
                    "README",
                    "readme",
                    "*.url",
                    "icon.png",
                    "LICENSE",
                    "license",
                    "manifest.json",
                    "*.pdb",
                ],
            )
        )


class TheForeverWinterGame(BasicGame, mobase.IPluginFileMapper):
    Name = "The Forever Winter Support Plugin"
    Author = "dataterminals"
    Version = "0.2.0"
    Description = (
        "Adds The Forever Winter (Fun Dog Studios, UE5) support to Mod "
        "Organizer 2. Manages content pak mods (.pak/.utoc/.ucas) and maps "
        "them into Content\\Paks\\Mods with a load-order prefix driven by MO2 "
        "priority. Requires a manually-installed Signature Bypass in "
        "Binaries\\Win64 — see the README."
    )

    GameName = "The Forever Winter"
    GameShortName = "theforeverwinter"
    GameNexusName = "theforeverwinter"
    GameSteamId = 2828860

    GameBinary = "Windows/ForeverWinter/Binaries/Win64/ForeverWinter-Win64-Shipping.exe"
    GameLauncher = "Windows/ForeverWinter.exe"

    # Placeholder: the plain overlay is intentionally aimed at a dead path so it
    # does nothing; mappings() below performs the real, load-order-aware
    # placement into Content\Paks\Mods. (Also avoids MO2 scanning the ~60 GB
    # Content\Paks folder.)
    GameDataPath = "_ROOT"

    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/ForeverWinter"
    GameIniFiles = ["%GAME_DOCUMENTS%/Saved/Config/Windows/GameUserSettings.ini"]
    GameSavesDirectory = "%GAME_DOCUMENTS%/Saved/SaveGames"
    GameSaveExtension = "sav"

    GameSupportURL = "https://github.com/dataterminals/ForeverWinterMO2Support"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        if not BasicGame.init(self, organizer):
            return False
        self._register_feature(TheForeverWinterModDataChecker())
        return True

    def executables(self) -> "list[mobase.ExecutableInfo]":
        game_dir = self.gameDirectory()
        return [
            # Default: shipping exe. Confirmed to launch directly under MO2.
            mobase.ExecutableInfo(
                "The Forever Winter",
                QFileInfo(game_dir, self.binaryName()),
            ),
            # Fallback: EOS wrapper, if a direct shipping launch is ever blocked.
            mobase.ExecutableInfo(
                "The Forever Winter (EOS launcher)",
                QFileInfo(game_dir, self.getLauncherName()),
            ),
        ]

    # --- Load-order mapping -------------------------------------------------

    def _paks_dir(self) -> Path:
        return Path(self.gameDirectory().absolutePath(), *_PAKS_ROOT)

    def _active_mod_paths(self) -> "Iterable[Path]":
        """Enabled mods, in ascending MO2 priority (index 0 = lowest priority,
        mounts first, loses conflicts)."""
        mods_parent = Path(self._organizer.modsPath())
        mod_list = self._organizer.modList()
        for name in mod_list.allModsByProfilePriority():
            if mod_list.state(name) & mobase.ModState.ACTIVE:
                yield mods_parent / name

    def mappings(self) -> "List[mobase.Mapping]":
        mods_dir = self._paks_dir() / _MODS_SUBFOLDER
        logic_dir = self._paks_dir() / _LOGICMODS_SUBFOLDER
        mod_paths = list(self._active_mod_paths())

        # Zero-padded so the numeric prefix sorts correctly (min width 2).
        width = max(2, len(str(max(len(mod_paths) - 1, 0))))

        result: "List[mobase.Mapping]" = [
            # Ensure the target exists and let Overwrite drop-ins reach it.
            mobase.Mapping(
                self._organizer.overwritePath(),
                str(mods_dir),
                True,   # isDirectory
                True,   # createTarget
            )
        ]

        for priority, mod_path in enumerate(mod_paths):
            prefix = str(priority).zfill(width) + "_"
            for f in mod_path.rglob("*"):
                if not f.is_file() or f.suffix.lower() not in _IOSTORE_EXTS:
                    continue
                parts_lower = [p.lower() for p in f.parts]
                if _LOGICMODS_SUBFOLDER.lower() in parts_lower:
                    # Blueprint mods: keep the name; UE4SS orders these itself.
                    dest = logic_dir / f.name
                else:
                    # Content paks: prefix with MO2 priority to force mount order.
                    dest = mods_dir / (prefix + f.name)
                result.append(mobase.Mapping(str(f), str(dest), False))

        return result


def createPlugin() -> mobase.IPlugin:
    return TheForeverWinterGame()
