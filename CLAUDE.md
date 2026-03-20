# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Plexbot is a Discord bot that monitors a Plex Media Server and sends alerts when it goes down, with recovery notifications. Features include fun movie/TV quotes in alerts, quiet hours, snooze via emoji reactions, auto-restart on prolonged outage (via SSH), and proactive scheduled restarts on a cron schedule.

## Commands

```bash
# Run tests
python -m pytest test_plexbot.py -v

# Run a single test
python -m pytest test_plexbot.py -v -k "test_name"

# Run locally (requires .env)
python plexbot.py

# Build and run with Docker
docker compose up -d --build

# Install dependencies (local dev)
pip install -r requirements.txt
```

There is no linter or formatter configured.

## Architecture

The entire bot lives in a single file: `plexbot.py` (~750 lines). Tests are in `test_plexbot.py`.

### Key sections of `plexbot.py` (in order):

1. **Configuration** — Environment variables loaded via `python-dotenv`, validated at import time. `_env_bool()` helper for boolean flags. Required vars (`DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`) cause `SystemExit` if missing.

2. **Message banks** — `MESSAGES_DOWN`, `MESSAGES_BACK_UP`, `MESSAGES_STARTUP_OK`, `MESSAGES_STARTUP_DOWN`, `SNOOZE_MESSAGE`. Down/back-up messages are random movie/TV quotes. Back-up messages use `{duration}` placeholder.

3. **Plex API functions** — `_plex_get()` does HTTP+XML parsing against the Plex server. `check_plex_health()` returns `(healthy: bool, problems: list[str])`. `get_plex_libraries()` and `get_active_streams()` require `PLEX_TOKEN`.

4. **Utilities** — `format_duration()`, `in_quiet_hours()`, `build_message()`, `parse_restart_time()`, `build_restart_cron_expression()`, `next_scheduled_restart()`.

5. **Restart operations** — SSH-based Docker container restart. `_ssh_base_cmd()` builds the SSH invocation. `scheduled_restart_loop()` is an independent async loop using `croniter` for timing.

6. **Discord bot** — `discord.Client` setup with `on_ready`, `on_message` (`!health` command), and `on_reaction_add` (snooze). The main monitoring loop polls Plex every `CHECK_INTERVAL` seconds.

### State management

- `down_since` / `last_alert_time` / `alert_count_this_outage` — outage tracking
- `alert_message_ids` — LRU set (max 50) of bot message IDs for snooze detection
- `snooze_until` — suppresses alerts when a user reacts to an alert message
- Alert suppression has three independent layers: snooze, cooldown timer, and quiet hours

### Auto-restart flow

After `RESTART_AFTER_ALERTS` consecutive alerts (default 2), the bot SSHes into the Plex host and runs `docker restart`. The SSH key is mounted into the Docker container at `/root/.ssh/plex_key`.

### Scheduled restart flow

Independent of outage monitoring. Uses `croniter` to sleep until the next cron-matched time. Skips restart if active streams are detected (requires `PLEX_TOKEN`). Configurable via either explicit cron or friendly frequency/day/time env vars (cron takes precedence).

## Testing

- pytest with `pytest-asyncio` for async tests
- Heavy use of `unittest.mock.patch` and `AsyncMock`
- Tests cover utility functions, cron building, Plex API interaction, and scheduled restart logic
- Discord integration (bot events, monitoring loop) is not directly unit-tested

## Configuration

All configuration is via environment variables (see `.env.example` for the full list). Key groups:
- **Core**: `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `PLEX_URL`
- **Quiet hours**: `QUIET_HOURS_ENABLED`, `QUIET_HOURS_START`, `QUIET_HOURS_END`, `QUIET_HOURS_TIMEZONE`
- **Auto-restart** (on outage): `PLEX_AUTO_RESTART`, `PLEX_SSH_HOST`, `PLEX_SSH_USER`, `PLEX_SSH_KEY_HOST_PATH`
- **Scheduled restart** (proactive): `PLEX_SCHEDULED_RESTART_ENABLED`, frequency/time/cron settings
