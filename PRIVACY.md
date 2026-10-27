# Privacy and local data

The published source and Windows downloads contain trainer code, runtime libraries, an icon and documentation. They do not include the developer's browser profile, cookies, game saves, backups, screenshots, investigations, account credentials, private logs or local workspace files.

The launcher creates a separate browser profile for the current Windows user at:

```
%LOCALAPPDATA%\Azeroth Survivors Trainer\Browser
```

Backups and explicit exports are written locally to sibling `Backups` and `Exported Saves` folders. The launcher has buttons to open those folders. Unlock backups are also retained in the game's browser IndexedDB. These files are not uploaded by the trainer.

The launcher opens the official game website. The website, its asset servers and co-op services receive their normal browser/network traffic; the game's own behavior and policies apply. This tool does not add analytics, telemetry, advertising, remote control or an automatic upload service. The Instructions button opens this public GitHub repository in the default browser.

Permanent unlocks act on the account in the trainer's local browser profile. They first require a verified game checkpoint and independent backup. Restoring a backup replaces the destination's entire progress. Export your existing game progress yourself if you want to move it between profiles.

Only share an EXE or ZIP from GitHub Releases. Do not redistribute your generated Browser, Backups or Exported Saves folders. When reporting a problem, avoid attaching saves, browser profiles or screenshots containing names unless you intend to share them.
