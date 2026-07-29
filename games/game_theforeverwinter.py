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
# Unreal gives loose mod paks no meaningful load order of their own. To make MO2's
# left-pane priority mean something, this plugin does NOT rely on the plain USVFS
# overlay; it uses IPluginFileMapper to map every enabled mod's pak trio into
# Content\Paks\Mods\ under a name the engine will act on. GameDataPath is therefore
# a dead placeholder ("_ROOT"); all real placement happens in mappings().
#
# The name is the ONLY channel to the engine, and only one part of it is read: the
# chunk-version token in "*_<N>_P.pak". Higher MO2 priority => higher N => higher
# mount Order => wins conflicts. See _iostore_name() for the derivation.
#
# CONFIRMED IN-GAME 2026-07-16. Two mods carrying the same package, winner read from
# the live table via TFWWorkbench's DumpDataTables:
#   ZZ_ConflictTestB_7_P (Order 803) beat ZZ_ConflictTestA_6_P (Order 703) — 48 rows
#   to 0 — even though B sorts alphabetically LATER, so it mounts FIRST and loses the
#   tiebreak. Only Order can produce that, so the chain MO2 priority -> _<N>_P ->
#   ChunkVersionNumber -> PakOrder -> IoStore order is real on this binary.
#
# An earlier development build (never released) used a zero-padded numeric PREFIX
# (00_, 01_, ...) on the theory that a higher number mounts later and wins. It was not
# backwards, it was INERT: the engine never reads a leading number, so every mod tied at
# Order 103 and the winner fell to a tiebreak favouring the alphabetically LOWEST name.
# Measured the same day: 03_AllSkills_P beat both 06_ and 07_ fixtures, and 05_A beat
# 06_B. The prefix controlled nothing while appearing to. Most community advice for UE
# pak load order recommends exactly this, and it does not work. DO NOT REINTRODUCE IT.

import mobase
from pathlib import Path
from typing import Iterable, List, Optional

from PyQt6.QtCore import QDir, QFileInfo

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame

# Paths relative to the Steam game root. Note TFW's extra "Windows" platform
# layer that the generic UE templates (Ready or Not, Silent Hill 2) lack.
_PAKS_ROOT = ("Windows", "ForeverWinter", "Content", "Paks")
_MODS_SUBFOLDER = "Mods"          # loose content paks (community convention)
_LOGICMODS_SUBFOLDER = "LogicMods"  # UE4SS Blueprint / "Logic" mods

# IoStore (Zen) mod payloads travel as a trio sharing one base name.
_IOSTORE_EXTS = (".pak", ".utoc", ".ucas")

# Placeholder data directory (relative to the game root). The plain USVFS
# overlay is aimed here so it does nothing useful; mappings() does the real,
# load-order-aware placement. MO2 errors if this directory is missing, so the
# plugin creates it — it stays empty and can be deleted any time.
_DATA_PLACEHOLDER = "_ROOT"

# TFWWorkbench keeps its JSON data in a tree under Content\Paks\Mods\TFWWorkbench\
# and builds that tree itself with os.execute("mkdir ..."). The cmd.exe child that
# spawns access-violates (0xC0000005) under MO2, so FindOrCreateModDir() returns
# nil and the failure surfaces frames later as "attempt to index a nil value".
# Pre-creating the tree makes GetModDir() succeed, so the os.execute path is never
# entered at all.
#
# It has to live in Overwrite: mappings() maps Overwrite wholesale onto Mods\, but
# filters everything else to _IOSTORE_EXTS, so a mod carrying only empty
# directories would map nothing. TFWWorkbench also snapshots the tree before
# creating children, so a tree it built itself is not read until the *next* launch
# — pre-creation is what makes the first launch work.
#
# Source of truth for this list is Settings.ModChildDirs in TFWWorkbench's own
# Scripts/Settings.lua; re-read it there if a future release changes it.
_TFWWORKBENCH_DIR = "TFWWorkbench"
# Singular: upstream's README says "DataTables", but its code says otherwise.
_TFWWORKBENCH_DATA_PARENT = "DataTable"
_TFWWORKBENCH_CHILD_DIRS = (
    "Item",
    "ItemValue",
    "CraftingRecipe",
    "CraftingGroup",
    "VendorData",
    "WeaponsDetailsData",
    "WeaponPartStatsData",
    "Dumps",
)

# Root Builder's folder. A mod puts everything destined for the game root under
# Root\, and Root Builder — not this plugin — deploys it. We must skip that whole
# subtree: it contains its own ue4ss\Mods\ folder, which would otherwise be
# mistaken for a content-pak Mods\ folder and copied into Content\Paks\Mods\.
_ROOT_BUILDER_FOLDER = "Root"

# Where a UE4SS Lua mod sits inside a Root Builder-style mod. Used to detect
# whether TFWWorkbench is actually present before creating its tree.
_UE4SS_MODS_REL = (
    _ROOT_BUILDER_FOLDER,
    "Windows",
    "ForeverWinter",
    "Binaries",
    "Win64",
    "ue4ss",
    "Mods",
)


def _is_root_builder_payload(f: Path, mod_path: Path) -> bool:
    """True if `f` lives under the mod's Root\\ folder, which Root Builder owns.

    Load-bearing: a Root-style mod (RE-UE4SS, TFWWorkbench, the bypass) carries
    Root\\...\\Win64\\ue4ss\\Mods\\, and without this check that inner Mods\\ reads
    as a content-pak Mods\\ folder — dumping UE4SS's Lua tree into Content\\Paks\\Mods\\.
    """
    try:
        parts = f.relative_to(mod_path).parts
    except ValueError:
        return False
    return bool(parts) and parts[0].lower() == _ROOT_BUILDER_FOLDER.lower()


def _iostore_name(f: Path, priority: int) -> str:
    """Destination filename encoding MO2 `priority` where the engine will read it.

    UE derives a pak's mount Order from exactly two things, neither of which is a
    leading number — a numeric *prefix* is inert:

      * the path bucket (everything under Content\\Paks\\ is 3), and
      * for a pak named "*_P.pak", the token between the LAST TWO underscores:
        numeric and >= 1 => ChunkVersionNumber = N + 1, otherwise 1.
        Then PakOrder += 100 * ChunkVersionNumber, and that same value is handed
        to the IoStore container mount.

    So "03_AllSkills_P.pak" parses "AllSkills" — not numeric — and lands at Order
    103, exactly like "07_Foo_P.pak". Every mod ties, and the winner falls to a
    tiebreak that runs opposite to intuition: pak discovery sorts DESCENDING, and
    both resolvers favour the last-mounted container, so the alphabetically
    LOWEST filename wins. That is why the old prefix scheme appeared to work
    backwards — it was not ordering anything; the tiebreak was.

    Appending "_<N>_P" puts our number in the slot the engine parses, so priority
    is decided by the PRIMARY key and the tiebreak is never consulted. N is
    1-based because the engine requires >= 1; "_0_P" silently falls back to
    ChunkVersionNumber 1 and collides with every unnumbered mod. Appending last
    also means a mod that already ships "Foo_3_P.pak" becomes "Foo_3_5_P.pak" —
    our N still wins the parse, so no sanitising is needed.
    """
    stem = f.stem[:-2] if f.stem.endswith("_P") else f.stem
    return f"{stem}_{priority + 1}_P{f.suffix}"


def _rel_under_folder(f: Path, mod_path: Path, folder: str) -> Optional[Path]:
    """Path of `f` relative to the first `folder` segment inside `mod_path`, or
    None if it isn't under one. Keeps mod-root files (meta.ini and friends) out
    of the game, and gives non-pak payloads a structure-preserving destination."""
    try:
        parts = f.relative_to(mod_path).parts
    except ValueError:
        return None
    for i, part in enumerate(parts):
        if part.lower() == folder.lower():
            rest = parts[i + 1 :]
            return Path(*rest) if rest else None
    return None


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
    Version = "0.2.1"
    Description = (
        "Adds The Forever Winter (Fun Dog Studios, UE5) support to Mod "
        "Organizer 2. Manages content pak mods (.pak/.utoc/.ucas) and maps "
        "them into Content\\Paks\\Mods with load order driven by MO2 priority "
        "(encoded as each pak's chunk-version token, the only part of a pak "
        "filename Unreal reads). Requires a manually-installed Signature "
        "Bypass in Binaries\\Win64 — see the README."
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
    # Content\Paks folder.) The folder is auto-created in mappings() because MO2
    # errors when its data directory does not exist.
    GameDataPath = _DATA_PLACEHOLDER

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
        loses conflicts). The index becomes N in _iostore_name(), so it must stay
        ascending: higher index => higher Order => wins."""
        mods_parent = Path(self._organizer.modsPath())
        mod_list = self._organizer.modList()
        for name in mod_list.allModsByProfilePriority():
            if mod_list.state(name) & mobase.ModState.ACTIVE:
                yield mods_parent / name

    def _tfwworkbench_active(self, mod_paths: "Iterable[Path]") -> bool:
        """True if an enabled mod ships the TFWWorkbench UE4SS mod."""
        return any(
            p.joinpath(*_UE4SS_MODS_REL, _TFWWORKBENCH_DIR).is_dir() for p in mod_paths
        )

    def _ensure_tfwworkbench_tree(self) -> None:
        """Pre-create TFWWorkbench's data tree in Overwrite so it never shells out
        to mkdir. See _TFWWORKBENCH_* above for why this is necessary."""
        base = (
            Path(self._organizer.overwritePath())
            / _TFWWORKBENCH_DIR
            / _TFWWORKBENCH_DATA_PARENT
        )
        for child in _TFWWORKBENCH_CHILD_DIRS:
            try:
                (base / child).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def dataDirectory(self) -> QDir:
        # MO2 opens this directory as soon as it resolves the game path — ~57ms
        # after, and long before it ever calls mappings() — so creating _ROOT
        # there left every startup logging
        # "failed to open directory ...\_ROOT: ObjectNamenotfound (0xc0000034)".
        # Creating it here means it exists whenever anything asks for it.
        #
        # The guard is load-bearing: gameDirectory() is QDir(self._gamePath), so
        # with no game path set this resolves relative to the working directory
        # and would strew _ROOT next to ModOrganizer.exe.
        directory = super().dataDirectory()
        if self._gamePath:
            try:
                Path(directory.absolutePath()).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        return directory

    def mappings(self) -> "List[mobase.Mapping]":
        # gamePath can be unset during early MO2 refreshes — do nothing then.
        if not getattr(self, "_gamePath", ""):
            return []

        mods_dir = self._paks_dir() / _MODS_SUBFOLDER
        logic_dir = self._paks_dir() / _LOGICMODS_SUBFOLDER
        mod_paths = list(self._active_mod_paths())

        if self._tfwworkbench_active(mod_paths):
            self._ensure_tfwworkbench_tree()

        result: "List[mobase.Mapping]" = [
            # Ensure the target exists and let Overwrite drop-ins reach it.
            mobase.Mapping(
                self._organizer.overwritePath(),
                str(mods_dir),
                True,   # isDirectory
                True,   # createTarget
            )
        ]

        mapped_into_logic = False

        for priority, mod_path in enumerate(mod_paths):
            for f in mod_path.rglob("*"):
                if not f.is_file() or _is_root_builder_payload(f, mod_path):
                    continue
                is_logic = _LOGICMODS_SUBFOLDER.lower() in (
                    p.lower() for p in f.parts
                )
                mapped_into_logic = mapped_into_logic or is_logic
                base = logic_dir if is_logic else mods_dir
                folder = _LOGICMODS_SUBFOLDER if is_logic else _MODS_SUBFOLDER

                if f.suffix.lower() in _IOSTORE_EXTS:
                    if is_logic:
                        # Blueprint mods: keep the name; UE4SS orders these itself.
                        dest = logic_dir / f.name
                    else:
                        # Content paks: encode MO2 priority as the pak's chunk
                        # version, which is the only filename channel the engine
                        # actually reads. See _iostore_name().
                        dest = mods_dir / _iostore_name(f, priority)
                else:
                    # Non-pak payload — e.g. TFWWorkbench reads its DataTable JSON
                    # from Mods\TFWWorkbench\DataTable\. These used to arrive via the
                    # plain overlay when GameDataPath was Content\Paks; now that all
                    # placement runs through here, skipping them would silently
                    # inert any mod that ships data alongside its pak.
                    #
                    # No priority prefix: these carry their own ordering convention
                    # (HeavyRifleRebalanceFix ships 005_*.json), and renaming them
                    # would fight it. Structure is preserved instead, so MO2
                    # priority only breaks ties — later mods map last and win.
                    rel = _rel_under_folder(f, mod_path, folder)
                    if rel is None:
                        continue  # mod-root file (meta.ini, …) — not game content
                    dest = base / rel
                result.append(mobase.Mapping(str(f), str(dest), False))

        # LogicMods\ must exist on disk before USVFS links anything into it: it refuses a
        # file link whose parent it cannot resolve (assertPathExists -> ERROR_PATH_NOT_FOUND),
        # and MO2 discards that return value, so a Blueprint mod would vanish in silence.
        # Mods\ escapes this only because the Overwrite entry above is a *directory* mapping,
        # which registers the node; LogicMods\ has none, and the game ships neither folder.
        # Tracked as we emit, so it is created if and only if something actually lands
        # there — a content-paks-only setup gets no stray directory.
        if mapped_into_logic:
            try:
                logic_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

        return result


def createPlugin() -> mobase.IPlugin:
    return TheForeverWinterGame()
