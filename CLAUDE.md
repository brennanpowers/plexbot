# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Single-file Discord bot (`plexbot.py`) that monitors a Plex Media Server and sends alerts to Discord when it's down. Deployed as a Docker container on Unraid.

## Running

```bash
# Local development
pip install -r requirements.txt
python plexbot.py

# Docker (production, on Unraid)
docker compose up -d --build
```

Requires a `.env` file — copy from `.env.example`. At minimum needs `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID`.

## Architecture

Everything lives in `plexbot.py`. Tests in `test_plexbot.py`.

- **Plex API layer**: `_plex_get()` is the shared helper for all Plex HTTP requests (returns parsed XML or None). `check_plex_health()`, `get_plex_identity()`, `get_plex_libraries()`, and `get_library_count()` build on it.
- **Health check logic**: `check_plex_health()` returns `(healthy: bool, problems: list[str])`. Checks `/identity` endpoint (no auth), then validates required libraries exist and have >0 items (requires `PLEX_TOKEN`).
- **Discord event loop**: `on_ready()` runs the polling loop with `asyncio.sleep`. `on_message()` handles the `!health` command. `on_reaction_add()` handles snooze.
- **Alert suppression**: Three layers — quiet hours (11 PM–7 AM Central), cooldown (1 alert/hour), and snooze (emoji reaction extends cooldown).
- **Auto-restart**: Opt-in via `PLEX_AUTO_RESTART`. On the 2nd+ alert (`RESTART_AFTER_ALERTS`), the bot SSHes into the Plex host to `docker restart` the container. SSH key is mounted into the container via `docker-compose.yml` (`PLEX_SSH_KEY_HOST_PATH`). SSH host defaults to hostname parsed from `PLEX_URL`. After restarting, waits `RESTART_CHECK_DELAY_SECONDS` and re-checks health. The down message is edited in-place with restart status. If Plex recovers, a recovery message is posted and outage state resets. `restart_plex_container()` handles the subprocess call; `attempt_restart_and_check()` orchestrates restart + re-check.
- **Scheduled restart**: Opt-in via `PLEX_SCHEDULED_RESTART_ENABLED`. Accepts a cron expression (`PLEX_SCHEDULED_RESTART_CRON`) or friendly config (`PLEX_SCHEDULED_RESTART_FREQUENCY` + `PLEX_SCHEDULED_RESTART_TIME` + day fields). Friendly config is converted to a cron expression internally via `build_restart_cron_expression()`. Uses `croniter` for next-run calculation. Timezone configurable via `PLEX_SCHEDULED_RESTART_TIMEZONE` (default UTC). Runs as a separate asyncio task (`scheduled_restart_loop()`) alongside the health check loop. Reuses `restart_plex_container()`. Skips restart if active streams detected (`PLEX_SCHEDULED_RESTART_SKIP_IF_ACTIVE_STREAMS`, default true, requires `PLEX_TOKEN`). `get_active_streams()` checks `/status/sessions`. Posts result to Discord. Monthly day-of-month clamping handled by `next_scheduled_restart()`.
- **Startup diagnostics**: On boot, logs SSH connectivity (if auto-restart enabled), scheduled restart config (frequency, next run time), quiet hours config, timezone mismatch warnings, and Plex health (server identity, library counts, any issues). Runs after `STARTUP_DELAY_SECONDS`. Non-blocking — failures are logged as warnings, never prevent the bot from starting.
- **Messages**: Random movie/TV quotes from message lists (`MESSAGES_DOWN`, `MESSAGES_BACK_UP`, etc.). Down messages must start with `🔴 **Plex is down!**`. Keep the tone fun.

## Testing

Run all tests before committing:

```bash
python -m pytest test_plexbot.py -v
```

When adding or modifying functionality, add or update corresponding tests in `test_plexbot.py`. Tests use pytest with `pytest-asyncio` for async functions. Module globals are patched with `@patch` decorators or `monkeypatch`.

## Key Design Decisions

- Quiet hours timezone configurable via `QUIET_HOURS_TIMEZONE` (default UTC). Quiet start/end hours (23–7) are still hardcoded
- Auto-restart only triggers when an alert is actually sent (not suppressed by cooldown/snooze/quiet hours)
