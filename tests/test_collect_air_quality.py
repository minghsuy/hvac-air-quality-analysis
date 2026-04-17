"""Tests for air quality collection functionality"""

from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, ".")  # Add root to path

import collect_with_sheets_api_v2 as collector


class TestFilterEfficiencyCalculation:
    """Test filter efficiency calculation logic"""

    def test_normal_efficiency(self):
        """Test normal filter efficiency calculation"""
        assert collector.calculate_efficiency(5, 10) == 50.0
        assert collector.calculate_efficiency(2, 20) == 90.0

    def test_perfect_efficiency(self):
        """Test when indoor PM2.5 is zero"""
        assert collector.calculate_efficiency(0, 10) == 100.0

    def test_no_outdoor_pollution(self):
        """Test when outdoor PM2.5 is zero"""
        assert collector.calculate_efficiency(5, 0) == 0.0

    def test_same_indoor_outdoor(self):
        """Test when indoor equals outdoor (no filtration)"""
        assert collector.calculate_efficiency(10, 10) == 0.0

    def test_indoor_worse_than_outdoor(self):
        """Test when indoor is worse than outdoor (clamped to 0)"""
        assert collector.calculate_efficiency(20, 10) == 0.0

    def test_negative_indoor(self):
        """Test edge case with negative indoor (clamped to 100%)"""
        assert collector.calculate_efficiency(-5, 10) == 100.0

    def test_negative_outdoor(self):
        """Test edge case with negative outdoor"""
        assert collector.calculate_efficiency(5, -10) == 0.0


class TestAirthingsAPI:
    """Test Airthings API integration"""

    @patch("requests.post")
    @patch("requests.get")
    def test_get_airthings_data_success(self, mock_get, mock_post):
        """Test successful data retrieval from Airthings"""
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_token_response

        # Mock account response
        mock_account_response = MagicMock()
        mock_account_response.json.return_value = {"accounts": [{"id": "test_account_id"}]}

        # Mock sensor response
        mock_sensor_response = MagicMock()
        mock_sensor_response.json.return_value = {
            "results": [
                {
                    "batteryPercentage": 100,
                    "recorded": "2025-07-27T10:00:00",
                    "sensors": [
                        {"sensorType": "pm25", "value": 5.0, "unit": "μg/m³"},
                        {"sensorType": "co2", "value": 450, "unit": "ppm"},
                        {"sensorType": "temp", "value": 22.5, "unit": "°C"},
                        {"sensorType": "humidity", "value": 45, "unit": "%"},
                        {"sensorType": "voc", "value": 100, "unit": "ppb"},
                        {"sensorType": "radonShortTermAvg", "value": 10, "unit": "Bq/m³"},
                    ],
                }
            ]
        }

        mock_get.side_effect = [mock_account_response, mock_sensor_response]

        with patch.dict(
            "os.environ",
            {
                "AIRTHINGS_CLIENT_ID": "test_id",
                "AIRTHINGS_CLIENT_SECRET": "test_secret",
                "AIRTHINGS_DEVICE_SERIAL": "123456",
            },
        ):
            data = collector.get_airthings_data()

            assert data is not None
            assert data["pm25"] == 5.0
            assert data["co2"] == 450
            assert data["temp"] == 22.5
            assert data["humidity"] == 45
            assert data["room"] == "master_bedroom"
            assert data["sensor_type"] == "airthings"

    @patch("requests.post")
    @patch("requests.get")
    def test_get_airthings_data_no_results(self, mock_get, mock_post):
        """Test when Airthings returns no results"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_token_response

        mock_account_response = MagicMock()
        mock_account_response.json.return_value = {"accounts": [{"id": "test_account_id"}]}

        mock_sensor_response = MagicMock()
        mock_sensor_response.json.return_value = {"results": []}

        mock_get.side_effect = [mock_account_response, mock_sensor_response]

        with patch.dict(
            "os.environ",
            {
                "AIRTHINGS_CLIENT_ID": "test_id",
                "AIRTHINGS_CLIENT_SECRET": "test_secret",
            },
        ):
            data = collector.get_airthings_data()
            assert data is None


class TestAirGradientAPI:
    """Test AirGradient API integration"""

    @patch("requests.get")
    def test_get_airgradient_data_success(self, mock_get):
        """Test successful data retrieval from AirGradient"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pm02Compensated": 3.5,
            "atmpCompensated": 25.0,
            "rhumCompensated": 50.0,
            "rco2": 420,
            "tvocIndex": 100,
            "noxIndex": 1,
        }
        mock_get.return_value = mock_response

        with patch.dict("os.environ", {"AIRGRADIENT_OUTDOOR_IP": "192.168.X.XX"}):
            data = collector.get_airgradient_data("test123", "outdoor", "192.168.X.XX")

            assert data is not None
            assert data["pm25"] == 3.5
            assert data["temp"] == 25.0
            assert data["humidity"] == 50.0
            assert data["co2"] == 420
            assert data["voc"] == 100
            assert data["nox"] == 1
            assert data["room"] == "outdoor"

    @patch("requests.get")
    def test_get_airgradient_data_timeout(self, mock_get):
        """Test AirGradient API timeout"""
        mock_get.side_effect = Exception("Connection timeout")

        data = collector.get_airgradient_data("test123", "outdoor", "192.168.X.XX")
        assert data is None

    @patch("requests.get")
    def test_get_airgradient_data_uses_compensated_values(self, mock_get):
        """Test that compensated values are preferred over raw values"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pm02": 5.0,  # Raw value
            "pm02Compensated": 3.5,  # Compensated value (should be used)
            "atmp": 24.0,
            "atmpCompensated": 25.0,
            "rhum": 48.0,
            "rhumCompensated": 50.0,
            "rco2": 420,
            "tvocIndex": 100,
            "noxIndex": 1,
        }
        mock_get.return_value = mock_response

        data = collector.get_airgradient_data("test123", "outdoor", "192.168.X.XX")

        # Should use compensated values
        assert data["pm25"] == 3.5  # Not 5.0
        assert data["temp"] == 25.0  # Not 24.0
        assert data["humidity"] == 50.0  # Not 48.0


class TestGoogleSheetsIntegration:
    """Test Google Sheets API integration"""

    @patch.object(collector, "get_sheets_service")
    def test_append_to_sheet_success(self, mock_service):
        """Test successful row append"""
        mock_sheets = MagicMock()
        mock_service.return_value = mock_sheets

        mock_values = MagicMock()
        mock_sheets.spreadsheets.return_value.values.return_value = mock_values
        mock_values.append.return_value.execute.return_value = {
            "updates": {"updatedRows": 1, "updatedRange": "Sheet1!A2:R2"}
        }

        result = collector.append_to_sheet(
            mock_sheets,
            "test_spreadsheet_id",
            ["2025-01-01", "sensor1", "room1", "type1", 5, 10, 50.0],
        )

        assert result is True


class TestTempStickAPI:
    """Test Temp Stick WiFi sensor integration"""

    @patch("requests.get")
    def test_get_tempstick_data_success(self, mock_get):
        """Test successful data retrieval from Temp Stick"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "sensor_id": "TS00XXTST1",
                "sensor_name": "Attic",
                "last_temp": 20.52,
                "last_humidity": 50.8,
                "battery_pct": 98.5,
                "offline": False,
            }
        }
        mock_get.return_value = mock_response

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "test_key"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["room"] == "attic"
        assert data["sensor_type"] == "tempstick"
        assert data["sensor_id"] == "tempstick_TST1"
        assert data["temp"] == 20.52  # API returns °C directly
        assert data["humidity"] == 50.8

    @patch("requests.get")
    def test_tempstick_temp_rounding(self, mock_get):
        """Test that Temp Stick temperature is rounded to 2 decimal places"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "last_temp": 35.456789,
                "last_humidity": 50.0,
            }
        }
        mock_get.return_value = mock_response

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "test_key"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00TEST01"),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["temp"] == 35.46  # Rounded to 2 decimal places

    @patch("requests.get")
    def test_tempstick_null_temp(self, mock_get):
        """Test that null temperature from API returns empty string"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"last_temp": None, "last_humidity": 80.0}}
        mock_get.return_value = mock_response

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "test_key"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00TEST01"),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["temp"] == ""  # None → empty string per schema rules

    @patch("requests.get")
    def test_tempstick_api_failure(self, mock_get):
        """Test graceful failure when Temp Stick API is unreachable"""
        mock_get.side_effect = Exception("Connection timeout")

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "test_key"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00TEST01"),
        ):
            data = collector.get_tempstick_data()

        assert data is None

    @patch("requests.get")
    def test_tempstick_api_error_status(self, mock_get):
        """Test graceful failure on non-200 status"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "test_key"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00TEST01"),
        ):
            data = collector.get_tempstick_data()

        assert data is None

    def test_tempstick_skipped_without_config(self):
        """Test that Temp Stick is silently skipped when not configured"""
        with (
            patch.object(collector, "TEMP_STICK_API_KEY", ""),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", ""),
        ):
            data = collector.get_tempstick_data()

        assert data is None


class TestTempStickDedup:
    """Dedup by last_checkin — skip Sheet write when the sensor hasn't reported
    a fresh reading. Temp Stick updates ~hourly for battery life, so polling
    every 5 min would otherwise write 11 duplicates per cycle."""

    def _response(self, checkin, temp=20.06, humidity=35.5):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "data": {
                "last_checkin": checkin,
                "last_temp": temp,
                "last_humidity": humidity,
            }
        }
        return r

    @patch("requests.get")
    def test_writes_cache_on_first_call(self, mock_get, tmp_path):
        """Empty cache → dict returned + cache populated with the checkin value."""
        cache = tmp_path / "tempstick_last_checkin"
        mock_get.return_value = self._response("2026-04-17 15:02:02")

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["temp"] == 20.06
        assert cache.read_text() == "2026-04-17 15:02:02"

    @patch("requests.get")
    def test_skips_when_checkin_unchanged(self, mock_get, tmp_path):
        """Cache matches API's last_checkin → returns None, Sheet write skipped."""
        cache = tmp_path / "tempstick_last_checkin"
        cache.write_text("2026-04-17 15:02:02")
        mock_get.return_value = self._response("2026-04-17 15:02:02")

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        assert data is None
        # Cache stays exactly as it was — no spurious rewrites.
        assert cache.read_text() == "2026-04-17 15:02:02"

    @patch("requests.get")
    def test_writes_when_checkin_differs(self, mock_get, tmp_path):
        """Cache has an older checkin → new reading flows through, cache updated."""
        cache = tmp_path / "tempstick_last_checkin"
        cache.write_text("2026-04-17 14:02:02")
        mock_get.return_value = self._response("2026-04-17 15:02:02", temp=21.5)

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["temp"] == 21.5
        assert cache.read_text() == "2026-04-17 15:02:02"

    @patch("requests.get")
    def test_missing_checkin_returns_dict_without_touching_cache(self, mock_get, tmp_path):
        """API 200 without last_checkin (schema drift) → still return dict but
        leave the cache untouched so an empty-string value can't starve all
        subsequent calls."""
        cache = tmp_path / "tempstick_last_checkin"
        cache.write_text("2026-04-17 14:02:02")

        r = MagicMock()
        r.status_code = 200
        # last_checkin absent from the payload
        r.json.return_value = {"data": {"last_temp": 20.0, "last_humidity": 40.0}}
        mock_get.return_value = r

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        assert data is not None
        assert data["temp"] == 20.0
        # Cache preserved — no partial state that would poison the next cycle.
        assert cache.read_text() == "2026-04-17 14:02:02"

    @patch("requests.get")
    def test_corrupt_cache_self_heals(self, mock_get, tmp_path):
        """Garbage bytes in the cache (torn write) → treated as 'no prior state',
        one duplicate row this cycle, cache re-seeded."""
        cache = tmp_path / "tempstick_last_checkin"
        cache.write_bytes(b"\x00\xff\x00partial-write")
        mock_get.return_value = self._response("2026-04-17 15:02:02")

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        # read_text on the corrupt bytes may raise — _read_tempstick_cache
        # should handle that gracefully and treat it as cache-miss.
        assert data is not None
        assert cache.read_text() == "2026-04-17 15:02:02"

    @patch("requests.get")
    def test_api_429_does_not_touch_cache(self, mock_get, tmp_path):
        """429 from the edge WAF → return None immediately; never read or write
        the cache (transient failure shouldn't corrupt state)."""
        cache = tmp_path / "tempstick_last_checkin"
        cache.write_text("2026-04-17 14:02:02")

        r = MagicMock()
        r.status_code = 429
        r.text = "Too Many Requests"
        mock_get.return_value = r

        with (
            patch.object(collector, "TEMP_STICK_API_KEY", "k"),
            patch.object(collector, "TEMP_STICK_SENSOR_ID", "TS00XXTST1"),
            patch.object(collector, "_TEMPSTICK_CACHE", cache),
        ):
            data = collector.get_tempstick_data()

        assert data is None
        assert cache.read_text() == "2026-04-17 14:02:02"


class TestEfficiencyEdgeCases:
    """Test edge cases in efficiency calculation"""

    def test_very_low_outdoor_pm25(self):
        """Test with very low outdoor PM2.5 (precision issues)"""
        # When outdoor is very low, small indoor values can cause large efficiency swings
        assert collector.calculate_efficiency(0, 1) == 100.0
        assert collector.calculate_efficiency(1, 1) == 0.0
        assert collector.calculate_efficiency(0.5, 1) == 50.0

    def test_rounding(self):
        """Test that efficiency is rounded to 2 decimal places"""
        result = collector.calculate_efficiency(1, 3)
        # (3-1)/3 = 0.666... should round to 66.67
        assert result == 66.67

    def test_both_zero(self):
        """Test when both indoor and outdoor are zero"""
        # Edge case: 0/0 should return 100% (perfect efficiency when no pollution)
        assert collector.calculate_efficiency(0, 0) == 100.0


# ---------------------------------------------------------------------------
# Shared Sheets loader (scripts/_sheets_loader.py) — extracted from three
# near-identical copies in refresh_cache.py, dashboard.py, and bench_heatmap.py
# ---------------------------------------------------------------------------

sys.path.insert(0, "scripts")  # make _sheets_loader importable as a sibling

import _sheets_loader  # noqa: E402


HEADERS = [
    "Timestamp",
    "Sensor_ID",
    "Room",
    "Sensor_Type",
    "Indoor_PM25",
    "Outdoor_PM25",
    "Filter_Efficiency",
    "Indoor_CO2",
    "Indoor_VOC",
    "Indoor_NOX",
    "Indoor_Temp",
    "Indoor_Humidity",
    "Indoor_Radon",
    "Outdoor_CO2",
    "Outdoor_Temp",
    "Outdoor_Humidity",
    "Outdoor_VOC",
    "Outdoor_NOX",
]


class TestSheetsLoader:
    """Test the shared Google Sheets → DataFrame loader."""

    def test_modern_18col_row_preserves_all_values(self):
        """Full 18-column post-stabilization row: nothing gets nulled."""
        values = [
            HEADERS,
            [
                "2026-02-10 12:00:00",
                "airthings_abc",
                "master_bedroom",
                "airthings",
                "1.5",  # Indoor_PM25
                "4.0",  # Outdoor_PM25
                "62.5",  # Filter_Efficiency
                "600",  # Indoor_CO2
                "100",  # Indoor_VOC
                "5",  # Indoor_NOX
                "22.5",  # Indoor_Temp ← must survive
                "45.0",  # Indoor_Humidity ← must survive
                "50",  # Indoor_Radon
                "420",  # Outdoor_CO2
                "15.0",  # Outdoor_Temp
                "60.0",  # Outdoor_Humidity
                "80",  # Outdoor_VOC
                "3",  # Outdoor_NOX
            ],
        ]
        df = _sheets_loader._values_to_df(values)
        assert len(df) == 1
        assert df.iloc[0]["Indoor_Temp"] == 22.5
        assert df.iloc[0]["Indoor_Humidity"] == 45.0
        assert df.iloc[0]["Outdoor_Temp"] == 15.0

    def test_legacy_17col_row_triggers_shift_repair(self):
        """Pre-2025-09-01 row with 17 columns: shift-repair nulls Indoor_Temp etc."""
        # Legacy short row — missing last column; shift-repair nulls the SHIFTED_COLS
        values = [
            HEADERS,
            [
                "2025-08-15 10:00:00",
                "airthings_abc",
                "master_bedroom",
                "airthings",
                "1.5",
                "4.0",
                "62.5",
                "600",
                "100",
                "5",
                "22.5",  # Indoor_Temp  — nulled by shift-repair
                "45.0",  # Indoor_Humidity — nulled
                "50",  # Indoor_Radon — nulled
                "420",  # Outdoor_CO2 — nulled
                "15.0",  # Outdoor_Temp — nulled
                "60.0",  # Outdoor_Humidity — nulled
                "80",  # Outdoor_VOC — nulled
                # 17 values only — missing Outdoor_NOX
            ],
        ]
        df = _sheets_loader._values_to_df(values)
        assert len(df) == 1
        # All SHIFTED_COLS for this legacy short row must be NaN
        import math

        assert math.isnan(df.iloc[0]["Indoor_Temp"])
        assert math.isnan(df.iloc[0]["Indoor_Humidity"])
        assert math.isnan(df.iloc[0]["Outdoor_Temp"])
        # But non-shifted columns stay intact
        assert df.iloc[0]["Indoor_PM25"] == 1.5
        assert df.iloc[0]["Filter_Efficiency"] == 62.5

    def test_modern_12col_tempstick_row_preserves_temp_humidity(self):
        """Post-stabilization Temp Stick row: Sheets trims 6 trailing empties,
        row lands as 12 cols, but shift-repair MUST NOT fire."""
        values = [
            HEADERS,
            [
                "2026-02-10 12:00:00",
                "tempstick_abcd",
                "attic",
                "tempstick",
                "",  # Indoor_PM25 (empty — tempstick doesn't report PM)
                "",  # Outdoor_PM25
                "",  # Filter_Efficiency
                "",  # Indoor_CO2
                "",  # Indoor_VOC
                "",  # Indoor_NOX
                "20.06",  # Indoor_Temp ← MUST SURVIVE
                "35.5",  # Indoor_Humidity ← MUST SURVIVE
                # 12 values total — Sheets API trimmed the 6 trailing empties
            ],
        ]
        df = _sheets_loader._values_to_df(values)
        assert len(df) == 1
        assert df.iloc[0]["Indoor_Temp"] == 20.06
        assert df.iloc[0]["Indoor_Humidity"] == 35.5

    def test_header_only_sheet_returns_empty_df(self):
        """Sheet with only the header row returns an empty DataFrame."""
        values = [HEADERS]
        df = _sheets_loader._values_to_df(values)
        assert len(df) == 0
        assert list(df.columns) == HEADERS

    def test_fetch_values_raises_on_empty_sheet(self):
        """Empty Sheet API response raises RuntimeError with a clear message."""
        import pytest

        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {}
        with (
            patch("_sheets_loader.build", return_value=mock_service),
            patch("_sheets_loader.service_account.Credentials.from_service_account_file"),
        ):
            with pytest.raises(RuntimeError, match="no rows"):
                _sheets_loader._fetch_values("fake_id", "fake_tab", "fake_creds.json")
