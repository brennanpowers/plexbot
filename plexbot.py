import asyncio
import os
import random
import subprocess
import time
import logging
from datetime import datetime
from urllib.parse import urlparse
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import discord
from dotenv import load_dotenv
import requests

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
PLEX_URL = os.environ.get("PLEX_URL", "http://10.0.0.16:32400")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
ALERT_COOLDOWN = int(os.environ.get("ALERT_COOLDOWN_SECONDS", "3600"))
SNOOZE_SECONDS = int(os.environ.get("SNOOZE_HOURS", "4")) * 3600
STARTUP_DELAY = int(os.environ.get("STARTUP_DELAY_SECONDS", "180"))
QUIET_TZ = ZoneInfo("America/Chicago")
QUIET_START = 23
QUIET_END = 7
MENTION_USER_ID = os.environ.get("DISCORD_MENTION_USER_ID")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN")
PLEX_AUTO_RESTART = os.environ.get("PLEX_AUTO_RESTART", "false").lower() in ("true", "1", "yes")
PLEX_CONTAINER_NAME = os.environ.get("PLEX_CONTAINER_NAME", "plex")
PLEX_SSH_HOST = os.environ.get("PLEX_SSH_HOST", "") or urlparse(PLEX_URL).hostname
PLEX_SSH_USER = os.environ.get("PLEX_SSH_USER", "root")
RESTART_AFTER_ALERTS = int(os.environ.get("RESTART_AFTER_ALERTS", "2"))
RESTART_CHECK_DELAY = int(os.environ.get("RESTART_CHECK_DELAY_SECONDS", "60"))
RESTART_TIMEOUT = int(os.environ.get("RESTART_TIMEOUT_SECONDS", "120"))
REQUIRED_LIBRARIES = [
    name.strip()
    for name in os.environ.get("PLEX_REQUIRED_LIBRARIES", "").split(",")
    if name.strip()
]

MESSAGES_DOWN = [
    "🔴 **Plex is down!** Have you tried turning it off and on again?",
    "🔴 **Plex is down!** This is fine. 🔥 Everything is fine.",
    "🔴 **Plex is down!** I've got a bad feeling about this...",
    "🔴 **Plex is down!** You either die a hero, or live long enough to see your server crash.",
    "🔴 **Plex is down!** To stream, or not to stream? That is no longer the question.",
    "🔴 **Plex is down!** Somebody call 0118 999 881 999 119 725 3!",
    "🔴 **Plex is down!** It's dead, Jim.",
    "🔴 **Plex is down!** Plex has left the building.",
    "🔴 **Plex is down!** Houston, we have a problem.",
    "🔴 **Plex is down!** One does not simply stream right now.",
    "🔴 **Plex is down!** I am Groot... and I can't stream.",
    "🔴 **Plex is down!** This is not the server you're looking for.",
    "🔴 **Plex is down!** We're gonna need a bigger server.",
    "🔴 **Plex is down!** Forget it, Jake. It's Chinatown.",
    "🔴 **Plex is down!** Here's looking at you, broken server.",
    "🔴 **Plex is down!** It just pulled a Ferris Bueller and disappeared.",
    "🔴 **Plex is down!** I see dead servers. They don't know they're dead.",
    "🔴 **Plex is down!** May the uptime be with you... eventually.",
    "🔴 **Plex is down!** What we've got here is failure to communicate.",
]

MESSAGES_BACK_UP = [
    "🟢 Plex is back after {duration}! The show must go on! 🍿",
    "🟢 I'm back, baby! Plex recovered after {duration}.",
    "🟢 After {duration}, Plex has risen from the ashes like a phoenix.",
    "🟢 Plex is back after {duration}. Life, uh, finds a way.",
    "🟢 {duration} later... I am inevitable. Plex has returned.",
    "🟢 Reports of my death have been greatly exaggerated. Back after {duration}.",
    "🟢 After {duration} in the upside down, Plex is back!",
    "🟢 Plex is back after {duration}. Frankly my dear, I don't give a damn.",
    "🟢 {duration} of darkness, but Plex has returned. You have my sword. And my streams.",
    "🟢 Just when I thought I was out, they pull me back in. Plex is up after {duration}.",
    "🟢 After {duration}, Plex is back. I'll be back... and I was! 🍿",
    "🟢 Plex survived {duration} of downtime. What doesn't kill you makes you buffer stronger.",
    "🟢 {duration} later and Plex rises. Today is a good day to stream.",
]

MESSAGES_STARTUP_OK = [
    "🟢 Plexbot reporting for duty! Plex is up and streams are flowing. 🍿",
    "🟢 Plexbot online. Plex looks great. As you wish.",
    "🟢 Plexbot has entered the chat. Plex is alive! It's alive!",
    "🟢 I'll be watching. Always watching. Plex is up!",
    "🟢 Plexbot is here. Plex is up. Roads? Where we're going, we don't need roads.",
    "🟢 Plexbot activated. Plex is up. I love it when a plan comes together.",
    "🟢 Plexbot online. Plex is running. You shall not buffer!",
    "🟢 Good morning, Vietnam! Plexbot is up and Plex is streaming!",
    "🟢 Plexbot is locked and loaded. Plex is up. Hasta la vista, downtime.",
    "🟢 Plexbot online. Plex checks out. It's gonna be a good day. 🍿",
    "🟢 There's no place like Plex. And it's up! 🍿",
    "🟢 Plexbot here. Plex is running smoother than a Dude's White Russian.",
    "🟢 Plexbot booted up. Plex is alive. After all, tomorrow is another stream day.",
    "🟢 E.T. phone home... and stream something. Plex is up!",
    "🟢 Plexbot is on the case. Plex is up. Elementary, my dear Watson.",
]

MESSAGES_STARTUP_DOWN = [
    "🔴 Plexbot is up but Plex is not. Well, that's just, like, your opinion, man.",
    "🔴 Plexbot is here but Plex isn't. Inconceivable!",
    "🔴 Plexbot online, but Plex is MIA. We can't stop here, this is bat country!",
    "🔴 Plexbot woke up and Plex didn't. Anybody? Anybody? Bueller?",
    "🔴 Plexbot is ready but Plex is not. I'm not even supposed to be here today!",
    "🔴 Plexbot is here. Plex is not. Mama always said life is like a box of chocolates.",
    "🔴 Plexbot online but Plex is ghost. Who you gonna call?",
    "🔴 Plexbot started but Plex is missing. Here's Johnny! ...just kidding, nobody's home.",
    "🔴 Plexbot checking in. Plex is down. I think we're gonna need a montage.",
    "🔴 Plexbot is awake. Plex is not. Toto, I've a feeling we're not streaming anymore.",
]

SNOOZE_MESSAGE = "😴 Got it, snoozing alerts for {hours}h. React again to extend."

MAX_TRACKED_ALERTS = 50


def _plex_get(endpoint, use_token=False):
    """Makes a GET request to Plex and returns parsed XML root, or None on failure."""
    headers = {}
    if use_token and PLEX_TOKEN:
        headers["X-Plex-Token"] = PLEX_TOKEN
    try:
        resp = requests.get(f"{PLEX_URL}{endpoint}", headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        return ElementTree.fromstring(resp.text)
    except (requests.RequestException, ElementTree.ParseError):
        return None


def check_plex_health():
    """Returns (healthy, problems) where problems is a list of issue descriptions."""
    if _plex_get("/identity") is None:
        return False, ["Server not responding"]

    if not PLEX_TOKEN or not REQUIRED_LIBRARIES:
        return True, []

    libraries = get_plex_libraries()
    if libraries is None:
        return False, ["Unable to read libraries"]

    lib_by_name = {lib["name"]: lib for lib in libraries}
    problems = []
    for required in REQUIRED_LIBRARIES:
        if required not in lib_by_name:
            problems.append(f"Library '{required}' not found")
        else:
            count = lib_by_name[required]["count"]
            if count is not None and count == 0:
                problems.append(f"Library '{required}' is empty")
            elif count is None:
                problems.append(f"Library '{required}' unreadable")

    return len(problems) == 0, problems


def get_plex_identity():
    root = _plex_get("/identity")
    if root is None:
        return None
    return {
        "name": root.get("friendlyName", "Unknown"),
        "version": root.get("version", "Unknown"),
    }


def get_plex_libraries():
    if not PLEX_TOKEN:
        return None
    root = _plex_get("/library/sections", use_token=True)
    if root is None:
        return None
    libraries = []
    for directory in root.findall("Directory"):
        name = directory.get("title", "Unknown")
        lib_key = directory.get("key")
        count = get_library_count(lib_key)
        libraries.append({"name": name, "count": count})
    return libraries


def get_library_count(key):
    if not PLEX_TOKEN or not key:
        return None
    root = _plex_get(
        f"/library/sections/{key}/all?X-Plex-Container-Start=0&X-Plex-Container-Size=0",
        use_token=True,
    )
    if root is None:
        return None
    try:
        return int(root.get("totalSize", 0))
    except ValueError:
        return None


def format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_min = minutes % 60
    if remaining_min:
        return f"{hours}h {remaining_min}m"
    return f"{hours}h"


def in_quiet_hours():
    hour = datetime.now(QUIET_TZ).hour
    return hour >= QUIET_START or hour < QUIET_END


def build_message(text):
    if MENTION_USER_ID:
        return f"<@{MENTION_USER_ID}> {text}"
    return text


def _ssh_base_cmd():
    """Build the common SSH command prefix."""
    return ["ssh",
            "-i", "/root/.ssh/plex_key",
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{PLEX_SSH_USER}@{PLEX_SSH_HOST}"]


def check_ssh_connectivity():
    """Test SSH connection to the Plex host. Logs result, never raises."""
    if not PLEX_SSH_HOST:
        log.info("Auto-restart: no SSH host configured, will use local Docker socket")
        return
    try:
        cmd = _ssh_base_cmd() + ["echo", "ok"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            log.info("Auto-restart: SSH connection to %s@%s successful", PLEX_SSH_USER, PLEX_SSH_HOST)
        else:
            log.warning("Auto-restart: SSH connection to %s@%s failed: %s",
                        PLEX_SSH_USER, PLEX_SSH_HOST, result.stderr.strip())
    except FileNotFoundError:
        log.warning("Auto-restart: ssh command not available in this container")
    except subprocess.TimeoutExpired:
        log.warning("Auto-restart: SSH connection to %s@%s timed out", PLEX_SSH_USER, PLEX_SSH_HOST)


def log_startup_health():
    """Log Plex health status at startup."""
    identity = get_plex_identity()
    if not identity:
        log.warning("Plex health: not responding at %s", PLEX_URL)
        return

    log.info("Plex health: online — %s v%s", identity["name"], identity["version"])

    libraries = get_plex_libraries()
    if libraries is None:
        if PLEX_TOKEN:
            log.warning("Plex health: unable to read libraries")
        return

    for lib in libraries:
        if lib["count"] is not None:
            if lib["count"] == 0:
                log.warning("Plex health:   %s — EMPTY", lib["name"])
            else:
                log.info("Plex health:   %s — %d items", lib["name"], lib["count"])
        else:
            log.warning("Plex health:   %s — unable to read", lib["name"])

    healthy, problems = check_plex_health()
    if healthy:
        log.info("Plex health: all checks passed")
    else:
        log.warning("Plex health: issues detected — %s", "; ".join(problems))


def restart_plex_container():
    """Restart the Plex Docker container. Returns (success, status_message)."""
    name = PLEX_CONTAINER_NAME
    host = PLEX_SSH_HOST
    try:
        if host:
            cmd = _ssh_base_cmd() + [f"docker restart {name}"]
        else:
            cmd = ["docker", "restart", name]

        log.info("Restarting Plex container: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=RESTART_TIMEOUT)

        if result.returncode == 0:
            return True, "🔄 Restart issued — checking if Plex recovers..."

        stderr = result.stderr.strip()
        if host and ("Connection refused" in stderr or "No route to host" in stderr
                     or "Connection timed out" in stderr or "Could not resolve" in stderr):
            return False, f"❌ Could not SSH into {host} — server may be fully down"
        if "No such container" in stderr or f"Error: No such object: {name}" in stderr:
            return False, f"❌ Container '{name}' not found on {host or 'localhost'}"
        return False, f"❌ Docker command failed: {stderr[:200]}"

    except subprocess.TimeoutExpired:
        return False, f"❌ Restart command timed out ({RESTART_TIMEOUT}s) — server may be unresponsive"
    except FileNotFoundError:
        return False, "❌ docker/ssh command not available in this container"


async def attempt_restart_and_check():
    """Attempt to restart Plex and re-check health. Returns (recovered, status_message)."""
    success, status = restart_plex_container()
    if not success:
        return False, status

    log.info("Restart issued, waiting %ds before health check...", RESTART_CHECK_DELAY)
    await asyncio.sleep(RESTART_CHECK_DELAY)

    healthy, problems = check_plex_health()
    if healthy:
        log.info("Plex recovered after restart")
        return True, "✅ Restart successful — Plex is back up!"
    else:
        log.warning("Plex still down after restart: %s", "; ".join(problems))
        return False, "⚠️ Restart issued but Plex is still not responding"


intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

alert_message_ids = set()
snooze_until = 0


@client.event
async def on_reaction_add(reaction, user):
    global snooze_until
    if user.bot:
        return
    if reaction.message.id not in alert_message_ids:
        return
    if MENTION_USER_ID and str(user.id) != MENTION_USER_ID:
        return

    snooze_until = time.time() + SNOOZE_SECONDS
    hours = SNOOZE_SECONDS // 3600
    log.info("Alerts snoozed for %dh by %s", hours, user)
    channel = reaction.message.channel
    await channel.send(SNOOZE_MESSAGE.format(hours=hours))


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip().lower() != "!health":
        return

    identity = get_plex_identity()
    if not identity:
        await message.channel.send("🔴 **Plex Health Check**\nServer: Not responding")
        return

    lines = [
        "**Plex Health Check**",
        f"Server: {identity['name']} v{identity['version']}",
        "Status: Online",
    ]

    libraries = get_plex_libraries()
    warnings = []
    if libraries is not None:
        lines.append(f"Libraries: {len(libraries)}")
        for lib in libraries:
            if lib["count"] is not None:
                if lib["count"] == 0:
                    status = "⚠️ EMPTY"
                    warnings.append(lib["name"])
                else:
                    status = f"{lib['count']} items"
                lines.append(f"  - {lib['name']}: {status}")
            else:
                lines.append(f"  - {lib['name']}: unable to read")
    elif PLEX_TOKEN:
        lines.append("Libraries: unable to read")

    if warnings:
        emoji = "⚠️"
        lines.append(f"\n**Warning:** Empty libraries detected: {', '.join(warnings)}")
    else:
        emoji = "🟢"

    await message.channel.send(f"{emoji} " + "\n".join(lines))


@client.event
async def on_ready():
    log.info("Bot connected as %s", client.user)
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        log.error("Channel %d not found — check DISCORD_CHANNEL_ID", CHANNEL_ID)
        await client.close()
        return

    log.info("--- Startup Diagnostics ---")

    if PLEX_AUTO_RESTART:
        check_ssh_connectivity()
    else:
        log.info("Auto-restart: disabled")

    log.info("Waiting %ds for other containers to start...", STARTUP_DELAY)
    await asyncio.sleep(STARTUP_DELAY)

    log_startup_health()
    log.info("--- Monitoring Started ---")

    last_alert_time = 0
    down_since = None
    alert_count_this_outage = 0

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        up, problems = check_plex_health()
        if problems:
            log.warning("Health check issues: %s", "; ".join(problems))

        quiet = in_quiet_hours()

        if up:
            if down_since is not None:
                downtime_secs = time.time() - down_since
                duration = format_duration(downtime_secs)
                log.info("Plex is back up after %s", duration)
                if not quiet:
                    text = random.choice(MESSAGES_BACK_UP).format(duration=duration)
                    await channel.send(build_message(text))
                down_since = None
                last_alert_time = 0
                alert_count_this_outage = 0
                alert_message_ids.clear()
            else:
                log.info("Plex is up")
        else:
            now = time.time()
            snoozed = now < snooze_until
            cooldown_ok = now - last_alert_time >= ALERT_COOLDOWN

            if cooldown_ok and not snoozed and not quiet:
                alert_count_this_outage += 1
                log.warning("Plex is DOWN — sending alert #%d", alert_count_this_outage)
                text = random.choice(MESSAGES_DOWN)
                sent = await channel.send(build_message(text))
                if len(alert_message_ids) >= MAX_TRACKED_ALERTS:
                    alert_message_ids.pop()
                alert_message_ids.add(sent.id)
                last_alert_time = now

                if PLEX_AUTO_RESTART and alert_count_this_outage >= RESTART_AFTER_ALERTS:
                    log.info("Attempting auto-restart (alert #%d)", alert_count_this_outage)
                    await sent.edit(content=build_message(text + "\n🔄 Restarting Plex..."))

                    recovered, status = await attempt_restart_and_check()
                    await sent.edit(content=build_message(text + f"\n{status}"))

                    if recovered:
                        downtime_secs = time.time() - down_since
                        duration = format_duration(downtime_secs)
                        recovery_text = random.choice(MESSAGES_BACK_UP).format(duration=duration)
                        await channel.send(build_message(recovery_text))
                        down_since = None
                        last_alert_time = 0
                        alert_count_this_outage = 0
                        alert_message_ids.clear()
            else:
                reason = "snoozed" if snoozed else "quiet hours" if quiet else "cooldown"
                log.warning("Plex is DOWN — alert suppressed (%s)", reason)

            if down_since is None:
                down_since = now


if __name__ == "__main__":
    client.run(DISCORD_TOKEN, log_handler=None)
