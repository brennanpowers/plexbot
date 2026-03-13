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

Everything lives in `plexbot.py`. No tests, no modules.

- **Plex API layer**: `_plex_get()` is the shared helper for all Plex HTTP requests (returns parsed XML or None). `check_plex_health()`, `get_plex_identity()`, `get_plex_libraries()`, and `get_library_count()` build on it.
- **Health check logic**: `check_plex_health()` returns `(healthy: bool, problems: list[str])`. Checks `/identity` endpoint (no auth), then validates required libraries exist and have >0 items (requires `PLEX_TOKEN`).
- **Discord event loop**: `on_ready()` runs the polling loop with `asyncio.sleep`. `on_message()` handles the `!health` command. `on_reaction_add()` handles snooze.
- **Alert suppression**: Three layers — quiet hours (11 PM–7 AM Central), cooldown (1 alert/hour), and snooze (emoji reaction extends cooldown).
- **Auto-restart**: Opt-in via `PLEX_AUTO_RESTART`. On the 2nd+ alert (`RESTART_AFTER_ALERTS`), the bot SSHes into the Plex host to `docker restart` the container. SSH key is mounted into the container via `docker-compose.yml` (`PLEX_SSH_KEY_HOST_PATH`). SSH host defaults to hostname parsed from `PLEX_URL`. After restarting, waits `RESTART_CHECK_DELAY_SECONDS` and re-checks health. The down message is edited in-place with restart status. If Plex recovers, a recovery message is posted and outage state resets. `restart_plex_container()` handles the subprocess call; `attempt_restart_and_check()` orchestrates restart + re-check.
- **Messages**: Random movie/TV quotes from message lists (`MESSAGES_DOWN`, `MESSAGES_BACK_UP`, etc.). Down messages must start with `🔴 **Plex is down!**`. Keep the tone fun.

## Key Design Decisions

- Quiet hours and timezone are hardcoded to America/Chicago — not configurable via env vars
- Auto-restart only triggers when an alert is actually sent (not suppressed by cooldown/snooze/quiet hours)
