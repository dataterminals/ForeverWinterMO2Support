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

> **Status:** `v0.2.1` — **validated working.** A content asset-replacement mod
> enabled in MO2 renders in-game: detect → install to `Mods\` → shipping-exe
> launch → signature bypass → USVFS overlay → in-game (2026-07-12). The shipping
> exe launches directly under MO2 — EOS does not block it. MO2's left-pane
> priority drives pak load order, confirmed in-game 2026-07-16, and the full
> UE4SS + TFWWorkbench stack ran end-to-end under MO2 the same day.
>
> **On Root Builder:** if you run UE4SS, TFWWorkbench, or a packaged Signature
> Bypass, Root Builder must be **enabled** — those are `Root\` mods and deploy
> nothing without it, silently and with no error. It does cache the game folder
> on first build, which is slow; the fix is a `Content\Paks` exclusion, not
> disabling the plugin. See
> [`docs/UE4SS-TFWWORKBENCH.md`](docs/UE4SS-TFWWORKBENCH.md).

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

> **Running UE4SS / TFWWorkbench?** Read
> [`docs/UE4SS-TFWWORKBENCH.md`](docs/UE4SS-TFWWORKBENCH.md) first. **Root Builder must
> be enabled** — older advice in `docs/PLAN.md` said to disable it, which is correct for
> content paks only and wrong once UE4SS is in play; with it off, UE4SS and TFWWorkbench
> deploy nothing and log nothing. TFWWorkbench also cannot create its own directories
> under MO2, but as of v0.2.0 the plugin pre-creates its `DataTable\` tree in Overwrite
> for you. Verified working 2026-07-16.

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
- **MO2's left-pane priority controls pak load order** as of v0.2.0 — drag a mod
  higher and it wins conflicts. Paks deploy as `<Name>_<N>_P.*` where `N` comes from
  MO2 priority, which is the one part of a pak's filename UE actually reads. Verified
  in-game 2026-07-16. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#load-order) —
  and note a numeric *prefix* does nothing at all, which is what earlier builds
  (and most community advice) get wrong.

## Layout

| Path | What |
|---|---|
| [`games/game_theforeverwinter.py`](games/game_theforeverwinter.py) | The MO2 Basic Games plugin |
| [`scripts/install-plugin.ps1`](scripts/install-plugin.ps1) | Copy the plugin into your MO2 install(s) |
| [`docs/PLAN.md`](docs/PLAN.md) | Phased build plan, open questions, test checklist |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How MO2 + USVFS + UE5 + TFW fit; design decisions |
| [`docs/UE4SS-TFWWORKBENCH.md`](docs/UE4SS-TFWWORKBENCH.md) | Running UE4SS + TFWWorkbench under MO2 — two silent prerequisites |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Sourced research notes behind the design |

## Credits & prior art

- [ModOrganizer2/modorganizer-basic_games](https://github.com/ModOrganizer2/modorganizer-basic_games)
  — the framework and the Ready or Not / Silent Hill 2 Remake UE templates this
  plugin is modeled on.
- The Forever Winter modding community (Nexus): Signature Bypass, RE-UE4SS builds,
  TFWWorkbench.
