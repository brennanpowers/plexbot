import calendar
import subprocess
from datetime import datetime
from unittest.mock import patch, MagicMock
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import pytest


# Patch env vars before importing plexbot
@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "123456")


# ---- format_duration ----

class TestFormatDuration:
    def test_seconds(self):
        from plexbot import format_duration
        assert format_duration(45) == "45s"

    def test_minutes(self):
        from plexbot import format_duration
        assert format_duration(150) == "2m"

    def test_hours_even(self):
        from plexbot import format_duration
        assert format_duration(7200) == "2h"

    def test_hours_with_minutes(self):
        from plexbot import format_duration
        assert format_duration(5400) == "1h 30m"

    def test_zero(self):
        from plexbot import format_duration
        assert format_duration(0) == "0s"

    def test_exactly_60(self):
        from plexbot import format_duration
        assert format_duration(60) == "1m"

    def test_exactly_3600(self):
        from plexbot import format_duration
        assert format_duration(3600) == "1h"

    def test_float_truncates(self):
        from plexbot import format_duration
        assert format_duration(90.9) == "1m"


# ---- in_quiet_hours ----

class TestInQuietHours:
    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 23)
    @patch("plexbot.QUIET_END", 7)
    @patch("plexbot.datetime")
    def test_during_quiet_late(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 23, 30, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is True

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 23)
    @patch("plexbot.QUIET_END", 7)
    @patch("plexbot.datetime")
    def test_during_quiet_early(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 3, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is True

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 23)
    @patch("plexbot.QUIET_END", 7)
    @patch("plexbot.datetime")
    def test_outside_quiet(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 12, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is False

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 23)
    @patch("plexbot.QUIET_END", 7)
    @patch("plexbot.datetime")
    def test_boundary_start(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 23, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is True

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 23)
    @patch("plexbot.QUIET_END", 7)
    @patch("plexbot.datetime")
    def test_boundary_end(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 7, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is False

    @patch("plexbot.QUIET_HOURS_ENABLED", False)
    def test_disabled_always_returns_false(self):
        from plexbot import in_quiet_hours
        assert in_quiet_hours() is False

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 22)
    @patch("plexbot.QUIET_END", 6)
    @patch("plexbot.datetime")
    def test_custom_window(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 22, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is True

    @patch("plexbot.QUIET_HOURS_ENABLED", True)
    @patch("plexbot.QUIET_START", 22)
    @patch("plexbot.QUIET_END", 6)
    @patch("plexbot.datetime")
    def test_custom_window_outside(self, mock_dt):
        from plexbot import in_quiet_hours, QUIET_TZ
        mock_dt.now.return_value = datetime(2026, 3, 13, 10, 0, tzinfo=QUIET_TZ)
        assert in_quiet_hours() is False


# ---- build_message ----

class TestBuildMessage:
    @patch("plexbot.MENTION_USER_ID", "12345")
    def test_with_mention(self):
        from plexbot import build_message
        assert build_message("hello") == "<@12345> hello"

    @patch("plexbot.MENTION_USER_ID", None)
    def test_without_mention(self):
        from plexbot import build_message
        assert build_message("hello") == "hello"

    @patch("plexbot.MENTION_USER_ID", "")
    def test_empty_mention(self):
        from plexbot import build_message
        assert build_message("hello") == "hello"


# ---- parse_restart_time ----

class TestParseRestartTime:
    def test_24h(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("23:00") == (23, 0)

    def test_24h_with_minutes(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("04:30") == (4, 30)

    def test_12h_am(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("4:00 AM") == (4, 0)

    def test_12h_pm(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("11:00 PM") == (23, 0)

    def test_12h_no_space(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("4:00AM") == (4, 0)

    def test_12h_hour_only(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("4 AM") == (4, 0)

    def test_invalid_defaults_to_0400(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("not-a-time") == (4, 0)

    def test_midnight(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("00:00") == (0, 0)

    def test_noon(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("12:00 PM") == (12, 0)

    def test_whitespace_stripped(self):
        from plexbot import parse_restart_time
        assert parse_restart_time("  04:00  ") == (4, 0)


# ---- build_restart_cron_expression ----

class TestBuildRestartCronExpression:
    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "0 4 * * 0")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_cron_takes_precedence(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * 0"
        assert dom is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "invalid cron")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_invalid_cron(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "daily")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "03:00")
    def test_daily(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 3 * * *"
        assert dom is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "weekly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "friday")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_weekly_friday(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * 5"
        assert dom is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "weekly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "thu")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_weekly_abbreviated_day(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * 4"

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "weekly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_weekly_defaults_to_sunday(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * 0"

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "monthly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "15")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "02:00")
    def test_monthly(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 2 15 * *"
        assert dom == 15

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "monthly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "0")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_monthly_day_below_one_defaults(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 1 * *"
        assert dom == 1

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "monthly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "99")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_monthly_day_above_31_clamps(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 31 * *"
        assert dom == 31

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "monthly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_monthly_no_day_defaults_to_first(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 1 * *"
        assert dom == 1

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_no_cron_no_frequency(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "biweekly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_invalid_frequency(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "daily")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "monday")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "15")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_daily_ignores_day_fields(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * *"
        assert dom is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "daily")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "11:00 PM")
    def test_daily_12h_format(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 23 * * *"

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "0 4 * * 0")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "daily")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "monday")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "15")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "11:00")
    def test_cron_ignores_all_friendly_fields(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 * * 0"
        assert dom is None

    @patch("plexbot.PLEX_SCHEDULED_RESTART_CRON", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_FREQUENCY", "monthly")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_WEEK", "")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_DAY_OF_MONTH", "abc")
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TIME", "04:00")
    def test_monthly_invalid_day_defaults(self):
        from plexbot import build_restart_cron_expression
        expr, dom = build_restart_cron_expression()
        assert expr == "0 4 1 * *"
        assert dom == 1


# ---- next_scheduled_restart ----

class TestNextScheduledRestart:
    @patch("plexbot.PLEX_SCHEDULED_RESTART_TZ", ZoneInfo("UTC"))
    def test_next_daily(self):
        from plexbot import next_scheduled_restart
        with patch("plexbot.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 13, 10, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            # Can't easily mock datetime used by croniter, so test without mock
        result = next_scheduled_restart("0 4 * * *", None)
        assert result.hour == 4
        assert result.minute == 0

    @patch("plexbot.PLEX_SCHEDULED_RESTART_TZ", ZoneInfo("UTC"))
    def test_monthly_day_clamping_february(self):
        from plexbot import next_scheduled_restart
        # Feb 2026 has 28 days. Cron "0 4 31 * *" with croniter will jump to March 31.
        # Our clamping should handle this for the month croniter lands on.
        result = next_scheduled_restart("0 4 31 * *", 31)
        # Result should be on the 31st of some month, or clamped to max
        max_day = calendar.monthrange(result.year, result.month)[1]
        assert result.day <= max_day

    @patch("plexbot.PLEX_SCHEDULED_RESTART_TZ", ZoneInfo("America/Chicago"))
    def test_timezone_respected(self):
        from plexbot import next_scheduled_restart
        result = next_scheduled_restart("0 4 * * *", None)
        assert result.tzinfo == ZoneInfo("America/Chicago")


# ---- DAY_OF_WEEK_MAP ----

class TestDayOfWeekMap:
    def test_all_full_names(self):
        from plexbot import DAY_OF_WEEK_MAP
        assert DAY_OF_WEEK_MAP["sunday"] == 0
        assert DAY_OF_WEEK_MAP["monday"] == 1
        assert DAY_OF_WEEK_MAP["tuesday"] == 2
        assert DAY_OF_WEEK_MAP["wednesday"] == 3
        assert DAY_OF_WEEK_MAP["thursday"] == 4
        assert DAY_OF_WEEK_MAP["friday"] == 5
        assert DAY_OF_WEEK_MAP["saturday"] == 6

    def test_all_abbreviations(self):
        from plexbot import DAY_OF_WEEK_MAP
        assert DAY_OF_WEEK_MAP["sun"] == 0
        assert DAY_OF_WEEK_MAP["mon"] == 1
        assert DAY_OF_WEEK_MAP["tue"] == 2
        assert DAY_OF_WEEK_MAP["wed"] == 3
        assert DAY_OF_WEEK_MAP["thu"] == 4
        assert DAY_OF_WEEK_MAP["fri"] == 5
        assert DAY_OF_WEEK_MAP["sat"] == 6


# ---- _plex_get ----

class TestPlexGet:
    @patch("plexbot.requests.get")
    def test_success(self, mock_get):
        from plexbot import _plex_get
        mock_get.return_value = MagicMock(
            status_code=200,
            text='<MediaContainer friendlyName="Test" version="1.0"/>'
        )
        result = _plex_get("/identity")
        assert result is not None
        assert result.get("friendlyName") == "Test"

    @patch("plexbot.requests.get")
    def test_non_200(self, mock_get):
        from plexbot import _plex_get
        mock_get.return_value = MagicMock(status_code=500)
        assert _plex_get("/identity") is None

    @patch("plexbot.requests.get")
    def test_connection_error(self, mock_get):
        import requests as req
        from plexbot import _plex_get
        mock_get.side_effect = req.ConnectionError
        assert _plex_get("/identity") is None

    @patch("plexbot.requests.get")
    def test_invalid_xml(self, mock_get):
        from plexbot import _plex_get
        mock_get.return_value = MagicMock(status_code=200, text="not xml")
        assert _plex_get("/identity") is None

    @patch("plexbot.requests.get")
    @patch("plexbot.PLEX_TOKEN", "test-token")
    def test_token_sent_when_requested(self, mock_get):
        from plexbot import _plex_get
        mock_get.return_value = MagicMock(
            status_code=200,
            text='<MediaContainer/>'
        )
        _plex_get("/library/sections", use_token=True)
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["X-Plex-Token"] == "test-token"


# ---- check_plex_health ----

class TestCheckPlexHealth:
    @patch("plexbot._plex_get")
    def test_server_not_responding(self, mock_get):
        from plexbot import check_plex_health
        mock_get.return_value = None
        healthy, problems = check_plex_health()
        assert healthy is False
        assert "Server not responding" in problems

    @patch("plexbot.PLEX_TOKEN", "")
    @patch("plexbot._plex_get")
    def test_healthy_no_token(self, mock_get):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        healthy, problems = check_plex_health()
        assert healthy is True
        assert problems == []


# ---- get_active_streams ----

class TestGetActiveStreams:
    @patch("plexbot._plex_get")
    def test_no_streams(self, mock_get):
        from plexbot import get_active_streams
        mock_get.return_value = ElementTree.fromstring('<MediaContainer size="0"/>')
        assert get_active_streams() == 0

    @patch("plexbot._plex_get")
    def test_active_streams(self, mock_get):
        from plexbot import get_active_streams
        mock_get.return_value = ElementTree.fromstring('<MediaContainer size="3"/>')
        assert get_active_streams() == 3

    @patch("plexbot._plex_get")
    def test_connection_failure(self, mock_get):
        from plexbot import get_active_streams
        mock_get.return_value = None
        assert get_active_streams() is None


# ---- get_plex_identity ----

class TestGetPlexIdentity:
    @patch("plexbot._plex_get")
    def test_success(self, mock_get):
        from plexbot import get_plex_identity
        mock_get.return_value = ElementTree.fromstring(
            '<MediaContainer friendlyName="MyPlex" version="1.40.0"/>'
        )
        result = get_plex_identity()
        assert result == {"name": "MyPlex", "version": "1.40.0"}

    @patch("plexbot._plex_get")
    def test_not_responding(self, mock_get):
        from plexbot import get_plex_identity
        mock_get.return_value = None
        assert get_plex_identity() is None


# ---- restart_plex_container ----

class TestRestartPlexContainer:
    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_ssh_success(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = restart_plex_container()
        assert success is True
        assert "Restart issued" in msg

    @patch("plexbot.PLEX_SSH_HOST", "")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_local_docker(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = restart_plex_container()
        assert success is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ["docker", "restart", "plex"]

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_ssh_connection_refused(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=255, stderr="Connection refused")
        success, msg = restart_plex_container()
        assert success is False
        assert "Could not SSH" in msg

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_no_such_container(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=1, stderr="No such container: plex")
        success, msg = restart_plex_container()
        assert success is False
        assert "not found" in msg

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_timeout(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ssh", timeout=120)
        success, msg = restart_plex_container()
        assert success is False
        assert "timed out" in msg

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_file_not_found(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.side_effect = FileNotFoundError
        success, msg = restart_plex_container()
        assert success is False
        assert "not available" in msg

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_generic_docker_error(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        success, msg = restart_plex_container()
        assert success is False
        assert "Docker command failed" in msg


# ---- attempt_restart_and_check ----

class TestAttemptRestartAndCheck:
    @patch("plexbot.check_plex_health")
    @patch("plexbot.restart_plex_container")
    @patch("plexbot.asyncio.sleep", return_value=None)
    @pytest.mark.asyncio
    async def test_restart_success_plex_recovers(self, mock_sleep, mock_restart, mock_health):
        from plexbot import attempt_restart_and_check
        mock_restart.return_value = (True, "restarting")
        mock_health.return_value = (True, [])
        recovered, msg = await attempt_restart_and_check()
        assert recovered is True
        assert "successful" in msg

    @patch("plexbot.check_plex_health")
    @patch("plexbot.restart_plex_container")
    @patch("plexbot.asyncio.sleep", return_value=None)
    @pytest.mark.asyncio
    async def test_restart_success_plex_still_down(self, mock_sleep, mock_restart, mock_health):
        from plexbot import attempt_restart_and_check
        mock_restart.return_value = (True, "restarting")
        mock_health.return_value = (False, ["Server not responding"])
        recovered, msg = await attempt_restart_and_check()
        assert recovered is False
        assert "still not responding" in msg

    @patch("plexbot.restart_plex_container")
    @pytest.mark.asyncio
    async def test_restart_fails(self, mock_restart):
        from plexbot import attempt_restart_and_check
        mock_restart.return_value = (False, "SSH failed")
        recovered, msg = await attempt_restart_and_check()
        assert recovered is False
        assert msg == "SSH failed"


# ---- Messages ----

class TestMessages:
    def test_down_messages_start_with_red_circle(self):
        from plexbot import MESSAGES_DOWN
        for msg in MESSAGES_DOWN:
            assert msg.startswith("🔴 **Plex is down!**"), f"Bad down message: {msg}"

    def test_back_up_messages_have_duration_placeholder(self):
        from plexbot import MESSAGES_BACK_UP
        for msg in MESSAGES_BACK_UP:
            assert "{duration}" in msg, f"Missing duration placeholder: {msg}"

    def test_back_up_messages_format_ok(self):
        from plexbot import MESSAGES_BACK_UP
        for msg in MESSAGES_BACK_UP:
            formatted = msg.format(duration="1h 30m")
            assert "1h 30m" in formatted

    def test_startup_ok_messages_start_with_green(self):
        from plexbot import MESSAGES_STARTUP_OK
        for msg in MESSAGES_STARTUP_OK:
            assert msg.startswith("🟢"), f"Startup OK message missing green circle: {msg}"

    def test_startup_down_messages_start_with_red(self):
        from plexbot import MESSAGES_STARTUP_DOWN
        for msg in MESSAGES_STARTUP_DOWN:
            assert msg.startswith("🔴"), f"Startup down message missing red circle: {msg}"


# ---- _env_bool ----

class TestEnvBool:
    def test_true_values(self):
        from plexbot import _env_bool
        with patch.dict("os.environ", {"TEST_VAR": "true"}):
            assert _env_bool("TEST_VAR") is True
        with patch.dict("os.environ", {"TEST_VAR": "1"}):
            assert _env_bool("TEST_VAR") is True
        with patch.dict("os.environ", {"TEST_VAR": "yes"}):
            assert _env_bool("TEST_VAR") is True
        with patch.dict("os.environ", {"TEST_VAR": "TRUE"}):
            assert _env_bool("TEST_VAR") is True
        with patch.dict("os.environ", {"TEST_VAR": "Yes"}):
            assert _env_bool("TEST_VAR") is True

    def test_false_values(self):
        from plexbot import _env_bool
        with patch.dict("os.environ", {"TEST_VAR": "false"}):
            assert _env_bool("TEST_VAR") is False
        with patch.dict("os.environ", {"TEST_VAR": "0"}):
            assert _env_bool("TEST_VAR") is False
        with patch.dict("os.environ", {"TEST_VAR": "no"}):
            assert _env_bool("TEST_VAR") is False
        with patch.dict("os.environ", {"TEST_VAR": ""}):
            assert _env_bool("TEST_VAR") is False

    def test_missing_uses_default(self):
        from plexbot import _env_bool
        with patch.dict("os.environ", {}, clear=False):
            assert _env_bool("NONEXISTENT_VAR") is False
            assert _env_bool("NONEXISTENT_VAR", "true") is True


# ---- check_plex_health (extended) ----

class TestCheckPlexHealthExtended:
    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.REQUIRED_LIBRARIES", ["Movies", "TV Shows"])
    @patch("plexbot.get_plex_libraries")
    @patch("plexbot._plex_get")
    def test_healthy_with_libraries(self, mock_get, mock_libs):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        mock_libs.return_value = [
            {"name": "Movies", "count": 100},
            {"name": "TV Shows", "count": 50},
        ]
        healthy, problems = check_plex_health()
        assert healthy is True
        assert problems == []

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.REQUIRED_LIBRARIES", ["Movies", "TV Shows"])
    @patch("plexbot.get_plex_libraries")
    @patch("plexbot._plex_get")
    def test_missing_library(self, mock_get, mock_libs):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        mock_libs.return_value = [{"name": "Movies", "count": 100}]
        healthy, problems = check_plex_health()
        assert healthy is False
        assert any("TV Shows" in p for p in problems)

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.REQUIRED_LIBRARIES", ["Movies"])
    @patch("plexbot.get_plex_libraries")
    @patch("plexbot._plex_get")
    def test_empty_library(self, mock_get, mock_libs):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        mock_libs.return_value = [{"name": "Movies", "count": 0}]
        healthy, problems = check_plex_health()
        assert healthy is False
        assert any("empty" in p.lower() for p in problems)

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.REQUIRED_LIBRARIES", ["Movies"])
    @patch("plexbot.get_plex_libraries")
    @patch("plexbot._plex_get")
    def test_unreadable_library(self, mock_get, mock_libs):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        mock_libs.return_value = [{"name": "Movies", "count": None}]
        healthy, problems = check_plex_health()
        assert healthy is False
        assert any("unreadable" in p.lower() for p in problems)

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.REQUIRED_LIBRARIES", ["Movies"])
    @patch("plexbot.get_plex_libraries")
    @patch("plexbot._plex_get")
    def test_libraries_return_none(self, mock_get, mock_libs):
        from plexbot import check_plex_health
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        mock_libs.return_value = None
        healthy, problems = check_plex_health()
        assert healthy is False
        assert "Unable to read libraries" in problems


# ---- get_plex_libraries ----

class TestGetPlexLibraries:
    @patch("plexbot.PLEX_TOKEN", "")
    def test_no_token_returns_none(self):
        from plexbot import get_plex_libraries
        assert get_plex_libraries() is None

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot.get_library_count")
    @patch("plexbot._plex_get")
    def test_parses_directories(self, mock_get, mock_count):
        from plexbot import get_plex_libraries
        mock_get.return_value = ElementTree.fromstring(
            '<MediaContainer><Directory title="Movies" key="1"/>'
            '<Directory title="TV Shows" key="2"/></MediaContainer>'
        )
        mock_count.side_effect = [100, 50]
        result = get_plex_libraries()
        assert len(result) == 2
        assert result[0] == {"name": "Movies", "count": 100}
        assert result[1] == {"name": "TV Shows", "count": 50}


# ---- get_library_count ----

class TestGetLibraryCount:
    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot._plex_get")
    def test_returns_count(self, mock_get):
        from plexbot import get_library_count
        mock_get.return_value = ElementTree.fromstring('<MediaContainer totalSize="42"/>')
        assert get_library_count("1") == 42

    @patch("plexbot.PLEX_TOKEN", "token")
    @patch("plexbot._plex_get")
    def test_no_total_size_defaults_zero(self, mock_get):
        from plexbot import get_library_count
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        assert get_library_count("1") == 0

    @patch("plexbot.PLEX_TOKEN", "")
    def test_no_token_returns_none(self):
        from plexbot import get_library_count
        assert get_library_count("1") is None

    @patch("plexbot.PLEX_TOKEN", "token")
    def test_no_key_returns_none(self):
        from plexbot import get_library_count
        assert get_library_count("") is None
        assert get_library_count(None) is None


# ---- _plex_get (extended) ----

class TestPlexGetExtended:
    @patch("plexbot.requests.get")
    def test_timeout(self, mock_get):
        import requests as req
        from plexbot import _plex_get
        mock_get.side_effect = req.Timeout
        assert _plex_get("/identity") is None

    @patch("plexbot.requests.get")
    @patch("plexbot.PLEX_TOKEN", "")
    def test_no_token_no_header(self, mock_get):
        from plexbot import _plex_get
        mock_get.return_value = MagicMock(status_code=200, text='<MediaContainer/>')
        _plex_get("/identity", use_token=True)
        _, kwargs = mock_get.call_args
        assert "X-Plex-Token" not in kwargs["headers"]

    @patch("plexbot.requests.get")
    def test_uses_correct_url(self, mock_get):
        from plexbot import _plex_get, PLEX_URL
        mock_get.return_value = MagicMock(status_code=200, text='<MediaContainer/>')
        _plex_get("/identity")
        url = mock_get.call_args[0][0]
        assert url == f"{PLEX_URL}/identity"


# ---- restart_plex_container (extended) ----

class TestRestartPlexContainerExtended:
    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_ssh_command_includes_strict_host_key_no(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=0)
        restart_plex_container()
        cmd = mock_run.call_args[0][0]
        assert "-o" in cmd
        assert "StrictHostKeyChecking=no" in cmd

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "my container")
    @patch("plexbot.subprocess.run")
    def test_container_name_is_shell_quoted(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=0)
        restart_plex_container()
        cmd = mock_run.call_args[0][0]
        remote_cmd = cmd[-1]
        assert "my container" not in remote_cmd or "'" in remote_cmd

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_ssh_no_route_to_host(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=255, stderr="No route to host")
        success, msg = restart_plex_container()
        assert success is False
        assert "Could not SSH" in msg

    @patch("plexbot.PLEX_SSH_HOST", "10.0.0.16")
    @patch("plexbot.PLEX_SSH_USER", "root")
    @patch("plexbot.PLEX_CONTAINER_NAME", "plex")
    @patch("plexbot.subprocess.run")
    def test_ssh_connection_timed_out(self, mock_run):
        from plexbot import restart_plex_container
        mock_run.return_value = MagicMock(returncode=255, stderr="Connection timed out")
        success, msg = restart_plex_container()
        assert success is False
        assert "Could not SSH" in msg


# ---- get_active_streams (extended) ----

class TestGetActiveStreamsExtended:
    @patch("plexbot._plex_get")
    def test_missing_size_attribute(self, mock_get):
        from plexbot import get_active_streams
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        assert get_active_streams() == 0

    @patch("plexbot._plex_get")
    def test_invalid_size_value(self, mock_get):
        from plexbot import get_active_streams
        mock_get.return_value = ElementTree.fromstring('<MediaContainer size="abc"/>')
        assert get_active_streams() is None


# ---- get_plex_identity (extended) ----

class TestGetPlexIdentityExtended:
    @patch("plexbot._plex_get")
    def test_missing_attributes_default(self, mock_get):
        from plexbot import get_plex_identity
        mock_get.return_value = ElementTree.fromstring('<MediaContainer/>')
        result = get_plex_identity()
        assert result == {"name": "Unknown", "version": "Unknown"}
