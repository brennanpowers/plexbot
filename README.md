<p align="center">
  <img src="assets/plexbot-logo.png" alt="Plexbot" width="200">
</p>

# Plexbot

A Discord bot that monitors your Plex Media Server and alerts you when it goes down. Alerts come with random movie and TV quotes for fun.

## Features

- **Health monitoring** — Polls Plex on a configurable interval and alerts a Discord channel when it's down
- **Library validation** — Optionally verifies that required libraries exist and aren't empty (requires `PLEX_TOKEN`)
- **Recovery notifications** — Sends a message when Plex comes back up, including how long it was down
- **Quiet hours** — Optionally suppress alerts during a configurable time window (e.g. 11 PM–7 AM)
- **Snooze** — React to any alert with an emoji to snooze further alerts
- **Auto-restart** — Optionally SSH into the Plex host and restart the Docker container after repeated failures
- **Scheduled restart** — Proactively restart Plex on a cron schedule or friendly daily/weekly/monthly config
- **Active stream detection** — Scheduled restarts are skipped if anyone is currently streaming
- **@mentions** — Optionally ping a specific Discord user on alerts
- **`!health` command** — On-demand health check showing server info and library stats
- **Startup diagnostics** — Logs configuration, SSH connectivity, and Plex health on boot

## Quick Start

```bash
cp .env.example .env
# Edit .env with your DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID
docker compose up -d --build
```

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and go to the **Bot** tab
3. Click **Reset Token** and copy it — this is your `DISCORD_BOT_TOKEN`
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Go to **OAuth2 > URL Generator**, select `bot` scope with these permissions:
   - Send Messages
   - Read Message History
   - Add Reactions (for snooze confirmation)
6. Open the generated URL to invite the bot to your server

### 2. Get Your Discord Channel ID

1. In Discord, go to **Settings > Advanced** and enable **Developer Mode**
2. Right-click the channel you want alerts in and click **Copy Channel ID**

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` — at minimum you need `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID`. Everything else has sensible defaults or is optional.

#### Core Settings

| Variable | Required | Description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | **Yes** | Bot token from Discord Developer Portal |
| `DISCORD_CHANNEL_ID` | **Yes** | Channel ID for alerts |
| `PLEX_URL` | No | Plex server URL (default: `http://localhost:32400`) |
| `PLEX_TOKEN` | No | Plex auth token — enables library validation, active stream detection, and `!health` library details ([how to find](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)) |
| `PLEX_REQUIRED_LIBRARIES` | No | Comma-separated library names to validate (e.g. `Movies,TV Shows`). Requires `PLEX_TOKEN` |
| `CHECK_INTERVAL_SECONDS` | No | How often to check Plex in seconds (default: `300`) |
| `ALERT_COOLDOWN_SECONDS` | No | Min seconds between repeated down alerts (default: `3600`) |
| `SNOOZE_HOURS` | No | Hours to snooze on emoji reaction (default: `4`) |
| `STARTUP_DELAY_SECONDS` | No | Seconds to wait before first check, set to `0` to skip (default: `180`) |
| `SEND_STARTUP_MESSAGE` | No | Post a status message to Discord when the bot starts (default: `false`) |
| `DISCORD_MENTION_USER_ID` | No | Discord user ID to @mention on alerts. Also restricts who can snooze |

#### Quiet Hours

| Variable | Required | Description |
|---|---|---|
| `QUIET_HOURS_ENABLED` | No | Enable quiet hours alert suppression (default: `false`) |
| `QUIET_HOURS_START` | No | Hour to start suppressing alerts, 0-23 (e.g. `23` for 11 PM) |
| `QUIET_HOURS_END` | No | Hour to resume alerts, 0-23 (e.g. `7` for 7 AM) |
| `QUIET_HOURS_TIMEZONE` | No | Timezone (default: `UTC`, e.g. `America/Chicago`) |

Both `QUIET_HOURS_START` and `QUIET_HOURS_END` must be set together. The bot will log a warning and disable quiet hours if misconfigured.

#### Auto-Restart (on outage)

| Variable | Required | Description |
|---|---|---|
| `PLEX_AUTO_RESTART` | No | Enable auto-restart on prolonged outage (default: `false`) |
| `PLEX_CONTAINER_NAME` | No | Docker container name to restart (default: `plex`) |
| `PLEX_SSH_HOST` | No | SSH host for restart (defaults to hostname from `PLEX_URL`) |
| `PLEX_SSH_USER` | No | SSH user (default: `root`) |
| `PLEX_SSH_KEY_HOST_PATH` | No | Absolute path to SSH private key on the Docker host |
| `RESTART_AFTER_ALERTS` | No | Number of alerts before restart kicks in (default: `2`, meaning first alert is notification-only) |
| `RESTART_CHECK_DELAY_SECONDS` | No | Seconds to wait after restart before re-checking health (default: `60`) |
| `RESTART_TIMEOUT_SECONDS` | No | Timeout for the restart command (default: `120`) |

#### Scheduled Restart (proactive)

| Variable | Required | Description |
|---|---|---|
| `PLEX_SCHEDULED_RESTART_ENABLED` | No | Enable scheduled restarts (default: `false`) |
| `PLEX_SCHEDULED_RESTART_TIMEZONE` | No | Timezone (default: `UTC`, e.g. `America/Chicago`) |
| `PLEX_SCHEDULED_RESTART_CRON` | No | Cron expression — takes precedence over frequency settings |
| `PLEX_SCHEDULED_RESTART_FREQUENCY` | No | `daily`, `weekly`, or `monthly` |
| `PLEX_SCHEDULED_RESTART_TIME` | No | Time of day: `04:00` or `4:00 AM` (default: `04:00`) |
| `PLEX_SCHEDULED_RESTART_DAY_OF_WEEK` | No | Day for weekly: `monday`–`sunday` or `mon`–`sun` |
| `PLEX_SCHEDULED_RESTART_DAY_OF_MONTH` | No | Day for monthly: `1`–`31`, clamped to month's max |
| `PLEX_SCHEDULED_RESTART_SKIP_IF_ACTIVE_STREAMS` | No | Skip if someone is streaming (requires `PLEX_TOKEN`, default: `true`) |

### 4. Run

#### Docker (recommended)

```bash
docker compose up -d --build
```

#### Local

```bash
pip install -r requirements.txt
python plexbot.py
```

## Commands

| Command | Description |
|---|---|
| `!health` | On-demand health check — shows server version, status, and library item counts |

## Snooze

React to any down alert with an emoji to snooze further alerts. The bot confirms with a message showing the snooze duration.

If `DISCORD_MENTION_USER_ID` is set, only that user can snooze. If not set, anyone can snooze.

## Auto-Restart

When enabled (`PLEX_AUTO_RESTART=true`), the bot attempts to restart the Plex Docker container after repeated failures:

1. **Alert #1** — Notification only, no restart
2. **Alert #2+** — Sends alert, edits it with "Restarting Plex...", runs `docker restart` via SSH, waits, then re-checks health
   - **Plex recovers** — alert is edited with success status, recovery message is posted
   - **Still down** — alert is edited with error status, normal polling continues

Auto-restart is suppressed along with alerts during quiet hours, cooldown, and snooze.

### SSH Setup

The bot needs passwordless SSH access to the Plex host. The private key is mounted into the container via `docker-compose.yml`:

```bash
# Generate a key (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/plexbot_key -N ""

# Copy the public key to the Plex host
ssh-copy-id -i ~/.ssh/plexbot_key.pub root@YOUR_PLEX_HOST_IP

# Set the absolute path in .env (~ won't expand in docker-compose)
PLEX_SSH_KEY_HOST_PATH=/home/youruser/.ssh/plexbot_key
```

On startup, the bot tests the SSH connection and logs the result. A failed SSH test does not prevent the bot from starting.

## Scheduled Restart

Proactively restart Plex on a schedule to prevent memory leaks and other drift. Independent of the outage auto-restart feature.

By default, scheduled restarts are skipped if anyone is actively streaming. This requires `PLEX_TOKEN` to be set. If skipped, the bot posts a message and retries on the next scheduled cycle.

### Examples

**Weekly on Sundays at 4 AM:**
```env
PLEX_SCHEDULED_RESTART_ENABLED=true
PLEX_SCHEDULED_RESTART_FREQUENCY=weekly
PLEX_SCHEDULED_RESTART_TIME=04:00
PLEX_SCHEDULED_RESTART_DAY_OF_WEEK=sunday
```

**Daily at 3:30 AM:**
```env
PLEX_SCHEDULED_RESTART_ENABLED=true
PLEX_SCHEDULED_RESTART_FREQUENCY=daily
PLEX_SCHEDULED_RESTART_TIME=3:30 AM
```

**Monthly on the 15th at 2 AM:**
```env
PLEX_SCHEDULED_RESTART_ENABLED=true
PLEX_SCHEDULED_RESTART_FREQUENCY=monthly
PLEX_SCHEDULED_RESTART_TIME=02:00
PLEX_SCHEDULED_RESTART_DAY_OF_MONTH=15
```

**Cron expression (every Sunday at 4 AM):**
```env
PLEX_SCHEDULED_RESTART_ENABLED=true
PLEX_SCHEDULED_RESTART_CRON=0 4 * * 0
```

All times use `PLEX_SCHEDULED_RESTART_TIMEZONE` (default: `UTC`). Cron expressions take precedence over friendly config. Inapplicable fields (e.g. `PLEX_SCHEDULED_RESTART_DAY_OF_WEEK` with daily frequency) are ignored with a log warning. For monthly restarts, if the configured day exceeds the month's max (e.g. 31 in February), it uses the last day of the month.

## Development

```bash
pip install -r requirements.txt
python -m pytest test_plexbot.py -v
```
