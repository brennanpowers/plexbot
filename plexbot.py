import asyncio
import calendar
import os
import random
import shlex
import subprocess
import time
import logging
from datetime import datetime
from urllib.parse import urlparse
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import discord
from croniter import croniter
from dotenv import load_dotenv
import requests

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

def _env_bool(key, default="false"):
    return os.environ.get(key, default).lower() in ("true", "1", "yes")


_missing = [v for v in ("DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID") if v not in os.environ]
if _missing:
    raise SystemExit(f"Missing required environment variable(s): {', '.join(_missing)}")

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
PLEX_URL = os.environ.get("PLEX_URL", "http://localhost:32400")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
ALERT_COOLDOWN = int(os.environ.get("ALERT_COOLDOWN_SECONDS", "3600"))
SNOOZE_SECONDS = int(os.environ.get("SNOOZE_HOURS", "4")) * 3600
STARTUP_DELAY = int(os.environ.get("STARTUP_DELAY_SECONDS", "180"))
SEND_STARTUP_MESSAGE = _env_bool("SEND_STARTUP_MESSAGE")
QUIET_HOURS_ENABLED = _env_bool("QUIET_HOURS_ENABLED")
_quiet_tz_name = os.environ.get("QUIET_HOURS_TIMEZONE", "UTC").strip()
try:
    QUIET_TZ = ZoneInfo(_quiet_tz_name)
except KeyError:
    log.warning("Quiet hours: invalid timezone '%s', falling back to UTC", _quiet_tz_name)
    QUIET_TZ = ZoneInfo("UTC")
_quiet_start_raw = os.environ.get("QUIET_HOURS_START", "")
_quiet_end_raw = os.environ.get("QUIET_HOURS_END", "")
if QUIET_HOURS_ENABLED:
    if _quiet_start_raw and _quiet_end_raw:
        try:
            QUIET_START = int(_quiet_start_raw)
            QUIET_END = int(_quiet_end_raw)
            if not (0 <= QUIET_START <= 23 and 0 <= QUIET_END <= 23):
                log.warning("!!! Quiet hours: QUIET_HOURS_START (%s) and QUIET_HOURS_END (%s) must be 0-23 — DISABLING quiet hours",
                            _quiet_start_raw, _quiet_end_raw)
                QUIET_HOURS_ENABLED = False
        except ValueError:
            log.warning("!!! Quiet hours: QUIET_HOURS_START ('%s') and QUIET_HOURS_END ('%s') must be integers — DISABLING quiet hours",
                        _quiet_start_raw, _quiet_end_raw)
            QUIET_HOURS_ENABLED = False
    elif _quiet_start_raw or _quiet_end_raw:
        log.warning("!!! Quiet hours: both QUIET_HOURS_START and QUIET_HOURS_END must be set (got start='%s', end='%s') — DISABLING quiet hours",
                    _quiet_start_raw, _quiet_end_raw)
        QUIET_HOURS_ENABLED = False
    else:
        log.warning("!!! Quiet hours: enabled but QUIET_HOURS_START and QUIET_HOURS_END not set — DISABLING quiet hours")
        QUIET_HOURS_ENABLED = False
if not QUIET_HOURS_ENABLED:
    QUIET_START = 0
    QUIET_END = 0
MENTION_USER_ID = os.environ.get("DISCORD_MENTION_USER_ID")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN")
PLEX_AUTO_RESTART = _env_bool("PLEX_AUTO_RESTART")
PLEX_CONTAINER_NAME = os.environ.get("PLEX_CONTAINER_NAME", "plex")
PLEX_SSH_HOST = os.environ.get("PLEX_SSH_HOST", "") or urlparse(PLEX_URL).hostname
PLEX_SSH_USER = os.environ.get("PLEX_SSH_USER", "root")
RESTART_AFTER_ALERTS = int(os.environ.get("RESTART_AFTER_ALERTS", "2"))
RESTART_CHECK_DELAY = int(os.environ.get("RESTART_CHECK_DELAY_SECONDS", "60"))
RESTART_TIMEOUT = int(os.environ.get("RESTART_TIMEOUT_SECONDS", "120"))
PLEX_SCHEDULED_RESTART_ENABLED = _env_bool("PLEX_SCHEDULED_RESTART_ENABLED")
PLEX_SCHEDULED_RESTART_CRON = os.environ.get("PLEX_SCHEDULED_RESTART_CRON", "").strip()
PLEX_SCHEDULED_RESTART_FREQUENCY = os.environ.get("PLEX_SCHEDULED_RESTART_FREQUENCY", "").strip().lower()
PLEX_SCHEDULED_RESTART_TIME = os.environ.get("PLEX_SCHEDULED_RESTART_TIME", "04:00").strip()
PLEX_SCHEDULED_RESTART_DAY_OF_WEEK = os.environ.get("PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "").strip().lower()
PLEX_SCHEDULED_RESTART_DAY_OF_MONTH = os.environ.get("PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "").strip()
PLEX_SCHEDULED_RESTART_SKIP_IF_ACTIVE_STREAMS = _env_bool("PLEX_SCHEDULED_RESTART_SKIP_IF_ACTIVE_STREAMS", "true")
_restart_tz_name = os.environ.get("PLEX_SCHEDULED_RESTART_TIMEZONE", "UTC").strip()
try:
    PLEX_SCHEDULED_RESTART_TZ = ZoneInfo(_restart_tz_name)
except KeyError:
    log.warning("Scheduled restart: invalid timezone '%s', falling back to UTC", _restart_tz_name)
    PLEX_SCHEDULED_RESTART_TZ = ZoneInfo("UTC")
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

    return not problems, problems


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


def get_active_streams():
    """Return the number of active Plex streams, or None if unable to check."""
    root = _plex_get("/status/sessions", use_token=True)
    if root is None:
        return None
    try:
        return int(root.get("size", 0))
    except (ValueError, TypeError):
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
    if not QUIET_HOURS_ENABLED:
        return False
    hour = datetime.now(QUIET_TZ).hour
    return hour >= QUIET_START or hour < QUIET_END


def build_message(text):
    if MENTION_USER_ID:
        return f"<@{MENTION_USER_ID}> {text}"
    return text


DAY_OF_WEEK_MAP = {
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
    "sun": 0, "mon": 1, "tue": 2, "wed": 3,
    "thu": 4, "fri": 5, "sat": 6,
}


def parse_restart_time(time_str):
    """Parse a time string like '23:00' or '11:00 PM'. Returns (hour, minute)."""
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            t = datetime.strptime(time_str.strip(), fmt)
            return t.hour, t.minute
        except ValueError:
            continue
    log.warning("Scheduled restart: could not parse time '%s', defaulting to 04:00", time_str)
    return 4, 0


def build_restart_cron_expression():
    """Build a cron expression from config. Returns (cron_expr, day_of_month_raw) or (None, None)."""
    if PLEX_SCHEDULED_RESTART_CRON:
        if croniter.is_valid(PLEX_SCHEDULED_RESTART_CRON):
            if PLEX_SCHEDULED_RESTART_FREQUENCY:
                log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_CRON is set, ignoring PLEX_SCHEDULED_RESTART_FREQUENCY")
            if PLEX_SCHEDULED_RESTART_DAY_OF_WEEK:
                log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_CRON is set, ignoring PLEX_SCHEDULED_RESTART_DAY_OF_WEEK")
            if PLEX_SCHEDULED_RESTART_DAY_OF_MONTH:
                log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_CRON is set, ignoring PLEX_SCHEDULED_RESTART_DAY_OF_MONTH")
            if PLEX_SCHEDULED_RESTART_TIME != "04:00":
                log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_CRON is set, ignoring PLEX_SCHEDULED_RESTART_TIME")
            return PLEX_SCHEDULED_RESTART_CRON, None
        log.warning("Scheduled restart: invalid cron expression '%s'", PLEX_SCHEDULED_RESTART_CRON)
        return None, None

    if not PLEX_SCHEDULED_RESTART_FREQUENCY:
        log.warning("Scheduled restart: enabled but no PLEX_SCHEDULED_RESTART_CRON or PLEX_SCHEDULED_RESTART_FREQUENCY set")
        return None, None

    hour, minute = parse_restart_time(PLEX_SCHEDULED_RESTART_TIME)

    if PLEX_SCHEDULED_RESTART_FREQUENCY == "daily":
        if PLEX_SCHEDULED_RESTART_DAY_OF_WEEK:
            log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_WEEK ignored for daily frequency")
        if PLEX_SCHEDULED_RESTART_DAY_OF_MONTH:
            log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_MONTH ignored for daily frequency")
        return f"{minute} {hour} * * *", None

    if PLEX_SCHEDULED_RESTART_FREQUENCY == "weekly":
        if PLEX_SCHEDULED_RESTART_DAY_OF_MONTH:
            log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_MONTH ignored for weekly frequency")
        dow = DAY_OF_WEEK_MAP.get(PLEX_SCHEDULED_RESTART_DAY_OF_WEEK)
        if dow is None:
            if PLEX_SCHEDULED_RESTART_DAY_OF_WEEK:
                log.warning("Scheduled restart: unrecognized day '%s', defaulting to sunday",
                            PLEX_SCHEDULED_RESTART_DAY_OF_WEEK)
            else:
                log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_WEEK not set, defaulting to sunday")
            dow = 0
        return f"{minute} {hour} * * {dow}", None

    if PLEX_SCHEDULED_RESTART_FREQUENCY == "monthly":
        if PLEX_SCHEDULED_RESTART_DAY_OF_WEEK:
            log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_WEEK ignored for monthly frequency")
        dom = 1
        if PLEX_SCHEDULED_RESTART_DAY_OF_MONTH:
            try:
                dom = int(PLEX_SCHEDULED_RESTART_DAY_OF_MONTH)
            except ValueError:
                log.warning("Scheduled restart: invalid day of month '%s', defaulting to 1",
                            PLEX_SCHEDULED_RESTART_DAY_OF_MONTH)
                dom = 1
            if dom < 1:
                log.warning("Scheduled restart: day of month %d < 1, defaulting to 1", dom)
                dom = 1
            elif dom > 31:
                log.warning("Scheduled restart: day of month %d > 31, clamping to 31", dom)
                dom = 31
        else:
            log.warning("Scheduled restart: PLEX_SCHEDULED_RESTART_DAY_OF_MONTH not set, defaulting to 1st")
        return f"{minute} {hour} {dom} * *", dom

    log.warning("Scheduled restart: unrecognized frequency '%s' (use daily/weekly/monthly)",
                PLEX_SCHEDULED_RESTART_FREQUENCY)
    return None, None


def next_scheduled_restart(cron_expr, day_of_month_raw):
    """Get the next scheduled restart time, handling monthly day clamping."""
    now = datetime.now(PLEX_SCHEDULED_RESTART_TZ)
    cron = croniter(cron_expr, now.replace(tzinfo=None))
    next_naive = cron.get_next(datetime)
    next_time = next_naive.replace(tzinfo=PLEX_SCHEDULED_RESTART_TZ)

    if day_of_month_raw and day_of_month_raw > 28:
        max_day = calendar.monthrange(next_time.year, next_time.month)[1]
        if day_of_month_raw > max_day:
            next_time = next_time.replace(day=max_day)

    return next_time


async def scheduled_restart_loop(channel):
    """Run scheduled restarts on a cron-like schedule."""
    cron_expr, day_of_month_raw = build_restart_cron_expression()
    if cron_expr is None:
        return

    log.info("Scheduled restart: cron expression '%s' (%s)", cron_expr, PLEX_SCHEDULED_RESTART_TZ)

    while True:
        next_time = next_scheduled_restart(cron_expr, day_of_month_raw)
        log.info("Scheduled restart: next restart at %s", next_time.strftime("%Y-%m-%d %I:%M %p %Z"))

        now = datetime.now(PLEX_SCHEDULED_RESTART_TZ)
        delay = (next_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        if PLEX_SCHEDULED_RESTART_SKIP_IF_ACTIVE_STREAMS and PLEX_TOKEN:
            streams = get_active_streams()
            if streams is not None and streams > 0:
                log.info("Scheduled restart: skipped — %d active stream(s)", streams)
                await channel.send(build_message(
                    f"🔄 **Scheduled restart skipped** — {streams} active stream(s). Will retry next cycle."))
                await asyncio.sleep(61)
                continue
            if streams is not None:
                log.info("Scheduled restart: no active streams, proceeding")

        log.info("Scheduled restart: executing now")
        success, status = restart_plex_container()
        if success:
            log.info("Scheduled restart: container restarted successfully")
            await channel.send(build_message("🔄 **Scheduled restart complete.** Plex container restarted."))
        else:
            log.warning("Scheduled restart: failed — %s", status)
            await channel.send(build_message(f"⚠️ **Scheduled restart failed.** {status}"))

        await asyncio.sleep(61)


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
            cmd = _ssh_base_cmd() + [f"docker restart {shlex.quote(name)}"]
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
_restart_task_started = False


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

    if PLEX_SCHEDULED_RESTART_ENABLED:
        cron_expr, dom = build_restart_cron_expression()
        if cron_expr:
            next_time = next_scheduled_restart(cron_expr, dom)
            if PLEX_SCHEDULED_RESTART_CRON:
                log.info("Scheduled restart: cron '%s' (%s)", PLEX_SCHEDULED_RESTART_CRON, PLEX_SCHEDULED_RESTART_TZ)
            else:
                parts = [PLEX_SCHEDULED_RESTART_FREQUENCY, f"at {PLEX_SCHEDULED_RESTART_TIME}"]
                if PLEX_SCHEDULED_RESTART_FREQUENCY == "weekly" and PLEX_SCHEDULED_RESTART_DAY_OF_WEEK:
                    parts.append(f"on {PLEX_SCHEDULED_RESTART_DAY_OF_WEEK}")
                if PLEX_SCHEDULED_RESTART_FREQUENCY == "monthly" and PLEX_SCHEDULED_RESTART_DAY_OF_MONTH:
                    parts.append(f"on day {PLEX_SCHEDULED_RESTART_DAY_OF_MONTH}")
                log.info("Scheduled restart: %s (%s)", " ".join(parts), PLEX_SCHEDULED_RESTART_TZ)
            log.info("Scheduled restart: next restart at %s", next_time.strftime("%Y-%m-%d %I:%M %p %Z"))
        else:
            log.warning("Scheduled restart: enabled but misconfigured, will not run")
    else:
        log.info("Scheduled restart: disabled")

    if QUIET_HOURS_ENABLED:
        log.info("Quiet hours: %02d:00–%02d:00 %s", QUIET_START, QUIET_END, QUIET_TZ)
    else:
        log.info("Quiet hours: disabled")

    if QUIET_HOURS_ENABLED and PLEX_SCHEDULED_RESTART_ENABLED and QUIET_TZ != PLEX_SCHEDULED_RESTART_TZ:
        log.warning("Timezone mismatch: quiet hours use %s but scheduled restarts use %s",
                    QUIET_TZ, PLEX_SCHEDULED_RESTART_TZ)

    log.info("Waiting %ds for other containers to start...", STARTUP_DELAY)
    await asyncio.sleep(STARTUP_DELAY)

    log_startup_health()

    if SEND_STARTUP_MESSAGE:
        healthy, _ = check_plex_health()
        if healthy:
            await channel.send(build_message(random.choice(MESSAGES_STARTUP_OK)))
        else:
            await channel.send(build_message(random.choice(MESSAGES_STARTUP_DOWN)))

    global _restart_task_started
    if PLEX_SCHEDULED_RESTART_ENABLED and not _restart_task_started:
        client.loop.create_task(scheduled_restart_loop(channel))
        _restart_task_started = True

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
