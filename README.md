<p align="center">
  <img src="assets/plexbot-logo.png" alt="Plexbot" width="200">
</p>

# Plexbot

A Discord bot that monitors your Plex Media Server and alerts you when it goes down. Alerts come with random movie and TV quotes for fun.

## Features

- **Health monitoring** — Checks Plex every 5 minutes (configurable) and alerts Discord when it's down
- **Library validation** — Verifies that required libraries exist and aren't empty (e.g., Movies, TV Shows)
- **Recovery notifications** — Tells you when Plex is back and how long it was down
- **Quiet hours** — No alerts between 11 PM and 7 AM Central
- **Snooze** — React to any alert with an emoji to snooze further alerts for 4 hours (configurable)
- **@mentions** — Optionally ping a specific user on alerts
- **`!health` command** — On-demand health check showing server info and library stats
- **Fun messages** — Random movie/TV quotes with every alert

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and go to the **Bot** tab
3. Click **Reset Token** and copy it — this is your `DISCORD_BOT_TOKEN`
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Go to **OAuth2 > URL Generator**, select `bot` scope with `Send Messages` and `Read Message History` permissions
6. Open the generated URL to invite the bot to your server

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | Yes | Bot token from Discord Developer Portal |
| `DISCORD_CHANNEL_ID` | Yes | Channel ID for alerts (enable Developer Mode, right-click channel, Copy ID) |
| `PLEX_URL` | No | Plex server URL (default: `http://10.0.0.16:32400`) |
| `PLEX_TOKEN` | No | Plex auth token for library checks ([how to find](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)) |
| `PLEX_REQUIRED_LIBRARIES` | No | Comma-separated library names to validate (e.g., `Movies,TV Shows`) |
| `CHECK_INTERVAL_SECONDS` | No | How often to check Plex (default: `300`) |
| `ALERT_COOLDOWN_SECONDS` | No | Min time between repeated down alerts (default: `3600`) |
| `SNOOZE_HOURS` | No | Hours to snooze on emoji reaction (default: `4`) |
| `STARTUP_DELAY_SECONDS` | No | Wait time before first check (default: `180`) |
| `DISCORD_MENTION_USER_ID` | No | Discord user ID to @mention on alerts |

### 3. Run

#### Docker (recommended for Unraid / servers)

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
| `!health` | Run an on-demand health check showing server version, status, and library item counts |

## Snooze

When the bot sends a down alert, react to it with any emoji to snooze further alerts. Only the configured `DISCORD_MENTION_USER_ID` can snooze (if set). The bot will confirm with a message showing how long alerts are snoozed.
