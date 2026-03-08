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
docker build -t plexbot .
docker run -d --name plexbot --restart unless-stopped --env-file .env plexbot
```

Requires a `.env` file — copy from `.env.example`. At minimum needs `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID`.

## Architecture

Everything lives in `plexbot.py`. No tests, no modules.

- **Plex API layer**: `_plex_get()` is the shared helper for all Plex HTTP requests (returns parsed XML or None). `check_plex_health()`, `get_plex_identity()`, `get_plex_libraries()`, and `get_library_count()` build on it.
- **Health check logic**: `check_plex_health()` returns `(healthy: bool, problems: list[str])`. Checks `/identity` endpoint (no auth), then validates required libraries exist and have >0 items (requires `PLEX_TOKEN`).
- **Discord event loop**: `on_ready()` runs the polling loop with `asyncio.sleep`. `on_message()` handles the `!health` command. `on_reaction_add()` handles snooze.
- **Alert suppression**: Three layers — quiet hours (11 PM–7 AM Central), cooldown (1 alert/hour), and snooze (emoji reaction extends cooldown).
- **Messages**: Random movie/TV quotes from message lists (`MESSAGES_DOWN`, `MESSAGES_BACK_UP`, etc.). Down messages must start with `🔴 **Plex is down!**`. Keep the tone fun.

## Key Design Decisions

- Quiet hours and timezone are hardcoded to America/Chicago — not configurable via env vars
