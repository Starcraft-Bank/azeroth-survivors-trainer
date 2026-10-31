# Privacy and local data

The release contains trainer source, runtime libraries, a game compatibility
profile, collection definitions, an icon and documentation. It contains no
developer saves, screenshots, credentials, browser profile, personal settings,
local tests, game EXE or game asset archives.

The launcher starts the game selected by you and instruments that owned process.
It does not attach to an unrelated running game or patch the game EXE on disk.
Closing the trainer closes its game because active hooks reference trainer memory.
The game's own normal networking and save behavior still apply. Match rewards
and deliberate collection unlocks can persist in your native game save.

Your chosen executable path, compatibility report and verified collection backups
remain under `%LOCALAPPDATA%/AzerothSurvivorsTrainerNative`. Toggles start off on
each launch. There is no telemetry, analytics, save upload or remote-control
service. No saves, settings or local paths are sent to GitHub.

Collection unlocks require a separate confirmation. The trainer closes its game,
verifies a backup outside the live save directory, checks the original has not
changed, and replaces the save atomically. Keep your backups. Restoring a whole
save also restores the earlier progress recorded in that backup.

Only distribute the EXE or ZIP from Releases, not your local backup/settings
folders. A decompressed artifact audit and SHA-256 checksums accompany releases.

## Optional release updates

At startup and when you select Check for updates, the launcher requests public release metadata from its project's GitHub API. This sends no game saves, settings, local paths or credentials. GitHub receives ordinary connection metadata, such as the network address and application user agent. No account or token is used. The check runs in the background and never blocks launch; it does not download or install software. Download update opens the project's GitHub release page in your browser.
