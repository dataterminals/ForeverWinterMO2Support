# ForeverWinterMO2Support

A [Mod Organizer 2](https://github.com/ModOrganizer2/modorganizer) game plugin
for **The Forever Winter** (Fun Dog Studios, Unreal Engine 5.4.2, Steam App ID
`2828860`).

MO2 has no built-in support for The Forever Winter, and — unlike most UE5 titles
— there was **no community MO2 plugin** for it (the supported mod-manager path is
a dedicated Vortex extension). This repo is a first-of-kind attempt to let MO2
manage TFW content-pak mods through its virtual file system, so you get
profiles, one-click enable/disable, and non-destructive installs without ever
copying files into the game folder.

> **Status:** `v0.1.0` — **validated working (2026-07-12).** A content asset-
> replacement mod enabled in MO2 renders in-game: detect → install to `Mods\` →
> shipping-exe launch → signature bypass → USVFS overlay → in-game. The shipping
> exe launches directly under MO2 (EOS does not block it). Known rough edge: if
> you have the **Root Builder** plugin installed, it can make the first launch
> very slow by caching the whole game folder — see
> [`docs/PLAN.md`](docs/PLAN.md#phase-4--binaries-payload-via-root-builder-optional-quality-of-life).

---

## ⚠️ Read this first — signed paks

The Forever Winter **enforces pak signing**. Every shipped pak has a matching
`.sig`, and the engine rejects unsigned paks. **No mod pak will load** — through
MO2 or any other method — until a community **Signature Bypass** is present in
the game's binaries folder:

```
…\The Forever Winter\Windows\ForeverWinter\Binaries\Win64\
    dsound.dll          ← proxy DLL that disables the signature check
    bitfix\             ← its data folder
```

That folder is **outside** the directory MO2 virtualizes (`Content\Paks`), and
proxy DLLs load too early in process start-up for USVFS to deliver reliably. So
the bypass is a **manual, one-time prerequisite** (or a Root Builder mod — see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)). This plugin manages the content
paks; it does **not** install the bypass for you.

Get the Signature Bypass from Nexus (The Forever Winter → *Signature Bypass*,
mod id 57). If you also want Blueprint/Lua mods, install a UE5.4-capable
**RE-UE4SS** build into the same `Binaries\Win64` folder.

---

## Install

1. **Install the Signature Bypass** into `Binaries\Win64` (see above). Verify the
   game still launches from Steam.
2. **Copy the plugin** into your MO2 install:
   ```
   <MO2>\plugins\basic_games\games\game_theforeverwinter.py
   ```
   or run [`scripts/install-plugin.ps1`](scripts/install-plugin.ps1), which
   auto-detects your MO2 install(s) and copies it for you.
3. **Restart MO2** and create a new instance. The Forever Winter should now appear
   in the game-selection list (Steam auto-detection via App ID `2828860`).
4. **Set the launch target.** Try launching the default *The Forever Winter*
   (shipping exe) entry from MO2 first. If the game refuses to boot (EOS /
   entitlement), switch to the *The Forever Winter (EOS launcher)* entry.

## Using it

- Install content pak mods as usual (drag the archive into MO2 → Install). The
  plugin's mod-data checker relocates bare `.pak/.utoc/.ucas` trios into a
  `Mods\` folder so they virtualize to `Content\Paks\Mods\` at runtime.
- **Always launch the game through MO2.** USVFS is process-local: a game started
  from Steam or Explorer sees a stock, unmodded install.
- **Load order is naming-based, not left-pane-based** (a UE limitation, not an MO2
  one). Conflicting paks resolve by pak name / the `_P` patch suffix. See
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#load-order).

## Layout

| Path | What |
|---|---|
| [`games/game_theforeverwinter.py`](games/game_theforeverwinter.py) | The MO2 Basic Games plugin |
| [`scripts/install-plugin.ps1`](scripts/install-plugin.ps1) | Copy the plugin into your MO2 install(s) |
| [`docs/PLAN.md`](docs/PLAN.md) | Phased build plan, open questions, test checklist |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How MO2 + USVFS + UE5 + TFW fit; design decisions |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Sourced research notes behind the design |

## Credits & prior art

- [ModOrganizer2/modorganizer-basic_games](https://github.com/ModOrganizer2/modorganizer-basic_games)
  — the framework and the Ready or Not / Silent Hill 2 Remake UE templates this
  plugin is modeled on.
- The Forever Winter modding community (Nexus): Signature Bypass, RE-UE4SS builds,
  TFWWorkbench.
