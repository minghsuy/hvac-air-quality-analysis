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
