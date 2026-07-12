# The Forever Winter — Mod Organizer 2 support plugin (Basic Games framework)
#
# Drop this file into:  <MO2>\plugins\basic_games\games\game_theforeverwinter.py
#
# Target: MO2 2.5.x  (PyQt6 / mobase). If you are on an older PyQt5 build of MO2,
#         change the PyQt6 imports below to PyQt5.
#
# ---------------------------------------------------------------------------
# IMPORTANT — read before expecting mods to load:
#
# The Forever Winter ships *signed* paks (every pakchunk*-Windows.pak has a
# matching .sig, and the engine enforces the signature). An unsigned mod pak
# will be silently rejected UNLESS a community "Signature Bypass" proxy DLL
# (dsound.dll + a bitfix\ folder) is present in:
#     <game>\Windows\ForeverWinter\Binaries\Win64\
#
# That folder is the game's *binaries* directory, which is OUTSIDE the data
# directory MO2 virtualizes (Content\Paks). MO2's USVFS therefore cannot
# deliver the bypass DLL on its own, and proxy DLLs load so early in process
# start-up that virtualizing them is unreliable anyway. So the Signature
# Bypass (and RE-UE4SS, if you use Blueprint/Lua mods) must be installed as
# REAL files in Binaries\Win64 — either manually (recommended, see README) or
# via the Root Builder MO2 plugin. This plugin manages the *content paks*; it
# does not and cannot install the bypass for you.
# ---------------------------------------------------------------------------

import fnmatch

import mobase
from PyQt6.QtCore import QFileInfo

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame

# Relative to the Steam game root (D:\...\common\The Forever Winter). Note the
# extra "Windows" platform layer that the generic UE templates (Ready or Not,
# Silent Hill 2) do NOT have — TFW nests everything one level deeper.
_PROJECT_PAKS = "Windows/ForeverWinter/Content/Paks"

# The subfolder under Content\Paks that TFW's community installs content pak
# mods into. UE auto-mounts any pak/utoc/ucas found beneath Content\Paks,
# including this subfolder. Blueprint/"Logic" mods go in LogicMods (needs UE4SS).
_MODS_SUBFOLDER = "Mods"
_LOGICMODS_SUBFOLDER = "LogicMods"

# IoStore (Zen) mod payloads always travel as a trio sharing one base name.
_PAK_GLOBS = ("*.pak", "*.utoc", "*.ucas", "*.sig")


class TheForeverWinterModDataChecker(BasicModDataChecker):
    """Normalises downloaded mod archives so their pak files end up where the
    game expects them.

    A well-formed MO2 mod for TFW has, at its root, a ``Mods`` folder (content
    paks) and/or a ``LogicMods`` folder (Blueprint mods). Nexus archives, though,
    frequently ship the bare ``.pak/.utoc/.ucas`` trio at the archive root, or
    wrapped in a single junk folder. This checker relocates loose trios into
    ``Mods\\`` so that — with ``GameDataPath`` pointed at ``Content\\Paks`` — the
    files virtualise to ``Content\\Paks\\Mods\\`` when the game runs under MO2.
    """

    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
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
                move={
                    # Bare pak trios dropped at the mod root -> Content\Paks\Mods
                    "*.pak": _MODS_SUBFOLDER + "/",
                    "*.utoc": _MODS_SUBFOLDER + "/",
                    "*.ucas": _MODS_SUBFOLDER + "/",
                    "*.sig": _MODS_SUBFOLDER + "/",
                },
            )
        )

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # Let the Simple Installer unwrap a single root folder for us.
        parent = filetree.parent()
        if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
            return self.FIXABLE

        check_return = super().dataLooksValid(filetree)

        # A single unknown wrapper folder that itself contains a pak trio is
        # fixable — we hoist the trio out of it in fix().
        if (
            check_return is self.INVALID
            and len(filetree) == 1
            and is_directory(folder := filetree[0])
            and any(
                any(fnmatch.fnmatch(entry.name(), g) for g in _PAK_GLOBS)
                for entry in folder
            )
        ):
            return self.FIXABLE

        return check_return

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        filetree = super().fix(filetree)

        # Hoist a pak trio out of a single wrapper folder, then into Mods\.
        if (
            self.dataLooksValid(filetree) is self.FIXABLE
            and len(filetree) == 1
            and is_directory(folder := filetree[0])
        ):
            for entry in list(folder):
                if entry.isFile() and any(
                    fnmatch.fnmatch(entry.name(), g) for g in _PAK_GLOBS
                ):
                    filetree.move(entry, _MODS_SUBFOLDER + "/")
            if not any(e.isFile() for e in folder):
                filetree.remove(folder)

        return filetree


class TheForeverWinterGame(BasicGame):
    Name = "The Forever Winter Support Plugin"
    Author = "dataterminals"
    Version = "0.1.0"
    Description = (
        "Adds The Forever Winter (Fun Dog Studios, UE5) support to Mod "
        "Organizer 2. Manages content pak mods (.pak/.utoc/.ucas) via USVFS. "
        "Requires a manually-installed Signature Bypass in Binaries\\Win64 — "
        "see the plugin's README."
    )

    GameName = "The Forever Winter"
    GameShortName = "theforeverwinter"
    GameNexusName = "theforeverwinter"
    GameSteamId = 2828860

    # Launch target. The shipping exe is what actually mounts paks; the Nexus
    # Signature Bypass guide recommends launching it directly. If EOS/entitlement
    # refuses a direct launch under MO2, launch the GameLauncher (EOS wrapper)
    # instead — USVFS injects into child processes.
    GameBinary = "Windows/ForeverWinter/Binaries/Win64/ForeverWinter-Win64-Shipping.exe"
    GameLauncher = "Windows/ForeverWinter.exe"

    # USVFS overlay root. Enabled mods' contents overlay onto Content\Paks (so a
    # mod carrying Mods\foo.pak virtualises to Content\Paks\Mods\foo.pak).
    GameDataPath = _PROJECT_PAKS

    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/ForeverWinter"
    GameIniFiles = ["%GAME_DOCUMENTS%/Saved/Config/Windows/GameUserSettings.ini"]
    GameSavesDirectory = "%GAME_DOCUMENTS%/Saved/SaveGames"
    # NOTE: the .sav files here are settings/options. Actual character progress
    # is a hashed <guid>.dat (EOS/offline), which MO2 save-profiles will not
    # capture. Save management is intentionally light-touch for now.
    GameSaveExtension = "sav"

    GameSupportURL = (
        "https://github.com/dataterminals/ForeverWinterMO2Support"
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        if not super().init(organizer):
            return False
        self._register_feature(TheForeverWinterModDataChecker())
        return True

    def executables(self) -> "list[mobase.ExecutableInfo]":
        game_dir = self.gameDirectory()
        return [
            # Default: shipping exe (mounts paks; direct launch per bypass guide).
            mobase.ExecutableInfo(
                "The Forever Winter",
                QFileInfo(game_dir, self.binaryName()),
            ),
            # Fallback: EOS wrapper, in case a direct shipping launch is blocked.
            mobase.ExecutableInfo(
                "The Forever Winter (EOS launcher)",
                QFileInfo(game_dir, self.getLauncherName()),
            ),
        ]


def createPlugin() -> mobase.IPlugin:
    return TheForeverWinterGame()
