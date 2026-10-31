Discord: https://discord.gg/pC4n2fvrmD

## Update notices

The launcher checks its project's public GitHub release metadata in the background when opened. Select Check for updates to check again; if a newer release is available, Download update opens its GitHub page. Updating is optional: notices never block launching or playing, and nothing is downloaded or installed automatically. A failed or offline check leaves the launcher usable.

The request sends no game saves, settings, local paths or credentials. GitHub receives the ordinary connection metadata needed to serve the request.

**Launch Behavior**
Game startup no longer requires a matching version or a successful hook-pattern scan. Failed hook installations are reported individually, while other hooks remain active. If the shared extension runtime cannot initialize, its partial hooks are removed and the normal game opens instead.

Unknown game builds use a best-effort bundled layout. This removes startup blocking; it does not guarantee that changed game code, data layouts or every feature will work. Optional diagnostics remain available. Permanent collection edits retain their save-format checks.

# Azeroth Survivors Trainer — native edition

A standalone Windows trainer for the native **Azeroth Survivors** game, updated for **0.131.0**. This is separate from Legendary Mayhem: it adds optional cheat
controls without Mayhem's automatic waves, events or difficulty scaling.

## Launch and menu behavior

Startup - No version or required-hook launch gate; failed hooks are skipped.

Menu - XP controls are under Rewards; movement speed and independent map travel are under Session.

## Included map-travel fix

Corrects map-transfer zone references for upgraded characters and excludes departed
lobby records. Existing player stats remain unchanged.

## Quick start

1. Download the native trainer EXE or extract its ZIP.
2. Keep your original `AzerothSurvivors.exe` and its `Data` folder together.
   The trainer can be placed alongside them or elsewhere.
3. Close other running game instances. Run the trainer, Browse to the game EXE,
   and click **Launch with trainer**.
4. Use windowed or borderless mode. Press **Insert** to open the control panel;
   Insert or Escape closes it. All cheats start **off**.
5. Start a solo match or host a co-op lobby normally. Keep the trainer open.
   Closing the trainer also closes the game it launched.

Windows 10/11 x64. No Python, browser or extension installation is required.
Administrator access is not required. The community executable is unsigned.
The native game uses its ordinary native save; browser saves are not migrated.

## Combat

- **God mode:** prevent incoming native player damage, including lethal hits.
- **One-Hit Kill:** greatly increase successful hits while retaining the game's
  hit/immunity and kill-credit paths.
- **Kill Aura:** automatically defeat nearby enemies, with an adjustable radius.
- **Rapid skills:** shorten supported base, starting and learned skill timers.
  Skills still require valid targets and activation conditions.
- **Skill area:** multiply native area scaling. Fixed ranges, soft caps and
  target-count limits still apply.
- **Damage multiplier:** increase outgoing damage. Movement speed is configured under Session.

## Rewards

- **XP boost:** multiply incoming match XP. The game's level cap still applies.

- **Unlimited gold:** maintain the uint32 maximum of **4,294,967,295**. Pickup
  arithmetic saturates instead of wrapping. Remaining gold stays after disabling.
- **Free chests** and **free rerolls:** separate 0-gold toggles; neither requires
  Unlimited Gold. With Unlimited Gold enabled both are also free.
- **Unlimited banishes:** bypass the native allowance while preserving the
  actual banished choices and normal allowance for when it is switched off.
- **All Legendary rolls:** Legendary quality for supported new skill/jewelry
  choices and generated class gear. Existing choices need a reroll; existing
  equipment is not converted. Drop frequency is unchanged.
- **Supply spawning:** native chests, power-ups, gold and XP collectibles.

## Spawners and match actions

Choose a map and boss or guardian. Manual boss spawns preserve the timed schedule;
**Spawn next scheduled boss** advances it. **Boss enemies** replaces new normal
spawns with the selected boss. Existing enemies are unchanged.

**Instant win** uses native victory processing and cannot award the same run
twice. **Clear all enemies** defeats living enemies through native damage/reward
handling. Killing a final boss, including through Kill Aura, can finish a match.

## Mid-match map travel

The host can move the whole party to another map without starting a new run.
Use Insert → Session → Move party in Mayhem, or Insert → Spawners → Travel
in the trainer. Ordinary guests do not need a modified client.

Levels, learned skills, carried items, gold and elapsed match time are kept.
Existing enemies, hazards and uncollected ground drops are cleared without
kill rewards. Players receive five seconds of damage protection while loading.
Close all upgrade choices before travelling, and wait between transfers.
Completion rewards retain the original run’s map identity; travelling does not
award extra map clears. This does not increase the game’s lobby size.

## Collection unlocks

This separate trainer includes **Unlock collection** publicly. Return to the
character menu, open Insert → Collection, and confirm the permanent action.
The trainer closes its game, makes and verifies an independent save backup,
applies the supported collection and restarts the game.

The supported catalog contains 125 achievements, 581 class gear entries,
142 Codex entries, all class zone clears, 13 perks, 26 companion looks,
21 tabards, eight races and 14 reward appearances. Native collection gates
and the normal talent-point capacity are granted. Existing equipped choices,
statistics and talent allocations are preserved. Marks and item-star upgrade
currency are not filled. Other players' accounts are not unlocked.

Backups: `%LOCALAPPDATA%/AzerothSurvivorsTrainerNative/Collection Backups`.
Use **Open verified backups** to find them. Do not replace a save while the game
is running. A whole-save restore also reverts progress earned since the backup.

## Shortcuts and co-op

| Key | Toggle |
| --- | --- |
| Insert | Open/close panel |
| 1 | God mode |
| 2 | Rapid skills |
| 3 | Unlimited gold |
| 4 | Legendary rolls |
| 5 | XP boost |
| 6 | Skill area |
| 7 | Boss enemies |

Number row and numpad work while the game is focused. **Click choice cards**;
number keys are reserved for the trainer. Other apps retain their normal input.
Use the host for world changes and spawns. Guests use the ordinary compatible
game and do not see the trainer panel. Host-simulated player effects can also
affect party members; do not assume a guest trainer can control the host.

## Validation and limits

The reviewed 0.130.0 build was tested in isolated native matches: combat toggles,
stat restoration, real reroll/banish UI actions, chest purchases, Legendary
rewards, all 12 maps’ guardian definitions, native pickups and Instant Win.
The new trainer has not completed a full co-op test for every toggle or class.
It does not increase the game’s lobby limit. The reorganized Insert overlay was checked locally. This release targets game 0.131.0. See its release notes for the checks completed on that build; earlier adapters remain available.

## Compatibility, source and updates

The game updater is disabled during trainer-launched sessions; update the normal
game separately between sessions and use a matching trainer release.

The browser trainer remains in older releases. Source is MIT licensed; the game
and its assets are not included. See PRIVACY.md and THIRD_PARTY_NOTICES.md.
Unofficial community project, not affiliated with Aethus or Blizzard.
