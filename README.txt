# Azeroth Survivors Trainer

An unofficial Windows launcher and in-browser trainer for **[Azeroth Survivors](https://wow.aethus.pl/)** by Aethus.

## Download

**[Get the Windows EXE or ZIP from Releases](https://github.com/Starcraft-Bank/azeroth-survivors-trainer/releases/latest).**

Download `AzerothSurvivorsTrainer.exe`, or extract the ZIP first for offline instructions and license notices. The EXE includes Python and Playwright; you do not need to install Python, run commands, or install an extension.

Requires **64-bit Windows 10/11**, an up-to-date **Microsoft Edge or Google Chrome**, internet access, and hardware/browser support for the game's WebGPU renderer. The launcher prefers Edge. It does not install a browser or require administrator access. The game is downloaded from its official website when launched.

## Quick start

1. Run `AzerothSurvivorsTrainer.exe` and click **Launch game with trainer**.
2. Keep the launcher open while playing. Its browser uses a separate local profile.
3. Use the trainer panel at the **bottom right**. Expand its sections for spawners and permanent unlocks. Use the minus button to collapse the panel.
4. Start a match to enable match actions. **All toggles start off.**

| Key | Toggle |
| --- | --- |
| 1 | God mode |
| 2 | Rapid skills |
| 3 | Unlimited gold |
| 4 | Legendary rolls |
| 5 | XP boost |
| 6 | Skill area |
| 7 | Boss enemies |

The number row and numpad both work. **Click level-up cards**: number keys are reserved for the trainer.

## Features

- **God mode:** prevents normal incoming player damage. It does not revive an already dead hero.
- **Rapid skills:** choose 0.25 s, 0.10 s or every-frame cooldowns. Skills still require valid targets/conditions.
- **Unlimited gold:** replenishes current-run gold to its actual 32-bit maximum, **4,294,967,295**. Chests and rerolls become free; pickup overflow is prevented.
- **Legendary rolls:** newly generated skill/jewelry choices and supported generated class gear receive Legendary quality. Reroll an already-open choice menu. Drop frequency is unchanged.
- **XP boost:** 2x, 5x, 10x or 100x incoming match XP.
- **Skill area:** supported range/radius multipliers up to 100x, retaining the game's soft limits and target caps.
- **Boss/guardian spawners:** choose among 60 boss entries and 148 guardian/rare templates from all 12 zones. Guardians retain their normal interactions. Manual boss spawns preserve the schedule; Spawn next advances it. Killing a final boss can finish the match.
- **Boss enemies:** replaces **new** normal enemy spawns with the selected boss while retaining the normal population cap.
- **Instant win:** uses the normal victory flow, including one run/win and progression credit.

For co-op world changes/spawns, use the host. Cross-client behavior depends on the game and feature; not every multiplayer combination has been tested. The launcher modifies its own game client. It does not install anything on teammates' computers or grant their accounts collection unlocks.

## Permanent collection unlocks

During a match, expand **Permanent collection unlocks** and click **Unlock collection & win**.

This permanently grants the supported build's collection to the account in this browser profile, then wins the match:

- All **98 achievements**, their rewards and **142 Codex entries**.
- All **581 collectible class gear pieces**, 14 cosmetic appearances and every class's zone access/clears.
- All 13 perks at maximum rank, both companion slots and all 26 companion looks.
- All 21 tabards and eight races.
- The normal **51-point talent capacity** for each of nine classes. Existing talent allocations are preserved; remaining points can be spent on the build you choose.

The game first creates a checkpoint. The trainer verifies and saves an independent `.sav` backup before granting anything. A failed backup stops the permanent action. Use the launcher's **Backups** button or **Download last pre-unlock backup** in the game panel, then restore through **Options > Saves > Import Save** to undo the grants. Restoring replaces the whole account with its earlier state.

## Existing progress and file locations

Your normal browser save is separate. To bring it across, export a copy from the original game via **Options > Saves > Export Save**, then import that copy in the trainer browser. Keep the original export.

All generated player data remains under the current Windows user's:

```
%LOCALAPPDATA%\Azeroth Survivors Trainer\
  Browser\
  Backups\
  Exported Saves\
```

The game saves normally while playing. The launcher retains explicit exports. Updating/replacing the EXE does not erase this profile. Closing the launcher closes its game browser. To play unmodified, open the official game in a normal browser, or disable the optional extension and reload.

## Supported build and troubleshooting

Launcher **1.4.1** contains trainer **1.4** for game **v0.120.4 (93ecb257)**, asset stamp `86a011904793`. The original WASM SHA-256 must match:

```
52d0c462824285869e193345307432b9e48117c3e04eb06186cea56cac03dd8b
```

An unknown game build runs normally with trainer controls disabled. An update to this tool is required for a new game build. Restart the trainer browser after updating.

- **No browser:** install/update Edge or Chrome from its official source.
- **WebGPU/blank screen:** update the browser and graphics driver, enable normal browser hardware acceleration, and check whether the official game works without the trainer.
- **Profile already open:** close the existing trainer browser and try again. No personal browser process is killed.
- **Missing progress:** import your own exported save into the trainer profile; profiles do not automatically share saves.
- **Download warning:** the community EXE is unsigned. Compare its SHA-256 with the release's `SHA256SUMS.txt` and review this source; no security setting needs to be disabled.

## Privacy, source and build

Read [PRIVACY.md](PRIVACY.md). Release packaging uses an allowlist and is audited after extracting the executable's embedded contents. No development browser profiles, saves or personal workspace files are included.

The optional `extension/` folder can also be loaded unpacked in Edge/Chrome's extensions page with Developer mode, then the game must be reloaded.

To build the Windows EXE from source, use Python 3.12 x64 on Windows:

```powershell
python -m pip install -r requirements-build.txt
python build_windows.py
python audit_release.py
```

Build outputs are in `dist/`. The game binary and original game assets are not in this repository. The exact-build patch specification is included, so the launcher can be built without downloading a development WASM snapshot.

Original code: [MIT](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for the bundled runtimes and the Blizzard WoW icon. This project is not affiliated with or endorsed by Blizzard Entertainment or Aethus.
