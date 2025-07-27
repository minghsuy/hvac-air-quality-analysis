"""Tests for air quality collection functionality"""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import sys
sys.path.insert(0, '.')  # Add root to path

import collect_air_quality


class TestFilterEfficiencyCalculation:
    """Test filter efficiency calculation logic"""
    
    def test_normal_efficiency(self):
        """Test normal filter efficiency calculation"""
        assert collect_air_quality.calculate_filter_efficiency(5, 10) == 50.0
        assert collect_air_quality.calculate_filter_efficiency(2, 20) == 90.0
    
    def test_perfect_efficiency(self):
        """Test when indoor PM2.5 is zero"""
        assert collect_air_quality.calculate_filter_efficiency(0, 10) == 100.0
    
    def test_no_outdoor_pollution(self):
        """Test when outdoor PM2.5 is zero"""
        assert collect_air_quality.calculate_filter_efficiency(5, 0) == 0
    
    def test_same_indoor_outdoor(self):
        """Test when indoor equals outdoor (no filtration)"""
        assert collect_air_quality.calculate_filter_efficiency(10, 10) == 0
    
    def test_indoor_worse_than_outdoor(self):
        """Test when indoor is worse than outdoor (clamped to 0)"""
        assert collect_air_quality.calculate_filter_efficiency(20, 10) == 0
    
    def test_negative_values(self):
        """Test edge case with negative values"""
        assert collect_air_quality.calculate_filter_efficiency(-5, 10) == 100.0
        assert collect_air_quality.calculate_filter_efficiency(5, -10) == 0


class TestAirthingsAPI:
    """Test Airthings API integration"""
    
    @patch('requests.post')
    def test_get_token_success(self, mock_post):
        """Test successful token retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token_123'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {
            'AIRTHINGS_CLIENT_ID': 'test_id',
            'AIRTHINGS_CLIENT_SECRET': 'test_secret'
        }):
            token = collect_air_quality.get_airthings_token()
            assert token == 'test_token_123'
            
            # Verify API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://accounts-api.airthings.com/v1/token"
            assert call_args[1]['json']['grant_type'] == 'client_credentials'
    
    @patch('requests.post')
    def test_get_token_failure(self, mock_post):
        """Test token retrieval failure"""
        mock_post.side_effect = Exception("API Error")
        
        with patch.dict('os.environ', {
            'AIRTHINGS_CLIENT_ID': 'test_id',
            'AIRTHINGS_CLIENT_SECRET': 'test_secret'
        }):
            with pytest.raises(Exception):
                collect_air_quality.get_airthings_token()
    
    @patch('requests.get')
    @patch('collect_air_quality.get_airthings_token')
    def test_get_airthings_data_success(self, mock_token, mock_get):
        """Test successful data retrieval from Airthings"""
        mock_token.return_value = 'test_token'
        
        # Mock account response
        mock_account_response = MagicMock()
        mock_account_response.json.return_value = {
            'accounts': [{'id': 'test_account_id'}]
        }
        
        # Mock sensor response
        mock_sensor_response = MagicMock()
        mock_sensor_response.json.return_value = {
            'results': [{
                'batteryPercentage': 100,
                'recorded': '2025-07-27T10:00:00',
                'sensors': [
                    {'sensorType': 'pm25', 'value': 5.0, 'unit': 'μg/m³'},
                    {'sensorType': 'co2', 'value': 450, 'unit': 'ppm'},
                    {'sensorType': 'temp', 'value': 22.5, 'unit': '°C'},
                    {'sensorType': 'humidity', 'value': 45, 'unit': '%'}
                ]
            }]
        }
        
        mock_get.side_effect = [mock_account_response, mock_sensor_response]
        
        with patch.dict('os.environ', {'AIRTHINGS_DEVICE_SERIAL': '123456'}):
            data = collect_air_quality.get_airthings_data()
            
            assert data is not None
            assert data['battery'] == 100
            assert data['pm25'] == 5.0
            assert data['co2'] == 450
            assert data['temp'] == 22.5
            assert data['humidity'] == 45
    
    @patch('requests.get')
    @patch('collect_air_quality.get_airthings_token')
    def test_get_airthings_data_no_results(self, mock_token, mock_get):
        """Test when Airthings returns no results"""
        mock_token.return_value = 'test_token'
        
        mock_account_response = MagicMock()
        mock_account_response.json.return_value = {
            'accounts': [{'id': 'test_account_id'}]
        }
        
        mock_sensor_response = MagicMock()
        mock_sensor_response.json.return_value = {'results': []}
        
        mock_get.side_effect = [mock_account_response, mock_sensor_response]
        
        data = collect_air_quality.get_airthings_data()
        assert data is None


class TestAirGradientAPI:
    """Test AirGradient API integration"""
    
    @patch('requests.get')
    def test_get_airgradient_data_success(self, mock_get):
        """Test successful data retrieval from AirGradient"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'pm02Compensated': 3.5,
            'atmpCompensated': 25.0,
            'rhumCompensated': 50.0,
            'rco2': 420,
            'tvocIndex': 100,
            'noxIndex': 1
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        with patch.dict('os.environ', {'AIRGRADIENT_SERIAL': 'test_serial'}):
            data = collect_air_quality.get_airgradient_data()
            
            assert data is not None
            assert data['pm25'] == 3.5
            assert data['temp'] == 25.0
            assert data['humidity'] == 50.0
            assert data['co2'] == 420
            assert data['voc'] == 100
            assert data['nox'] == 1
    
    @patch('requests.get')
    def test_get_airgradient_data_timeout(self, mock_get):
        """Test AirGradient API timeout"""
        mock_get.side_effect = Exception("Connection timeout")
        
        with patch.dict('os.environ', {'AIRGRADIENT_SERIAL': 'test_serial'}):
            data = collect_air_quality.get_airgradient_data()
            assert data is None
    
    @patch('requests.get')
    def test_get_airgradient_data_missing_fields(self, mock_get):
        """Test AirGradient data with missing fields"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'pm02Compensated': 3.5,
            # Missing other fields
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        with patch.dict('os.environ', {'AIRGRADIENT_SERIAL': 'test_serial'}):
            data = collect_air_quality.get_airgradient_data()
            
            assert data is not None
            assert data['pm25'] == 3.5
            assert data['temp'] == 0  # Default value
            assert data['humidity'] == 0  # Default value


class TestGoogleSheetsIntegration:
    """Test Google Sheets form submission"""
    
    @patch('requests.post')
    def test_send_to_google_sheets_success(self, mock_post):
        """Test successful form submission"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        test_data = {
            'timestamp': '2025-07-27T10:00:00',
            'indoor_pm25': 5.0,
            'outdoor_pm25': 10.0,
            'filter_efficiency': 50.0
        }
        
        with patch.dict('os.environ', {
            'GOOGLE_FORM_ID': 'test_form_id',
            'FORM_TIMESTAMP': 'entry.123',
            'FORM_INDOOR_PM25': 'entry.456',
            'FORM_OUTDOOR_PM25': 'entry.789',
            'FORM_EFFICIENCY': 'entry.012'
        }):
            result = collect_air_quality.send_to_google_sheets(test_data)
            assert result is True
            
            # Verify form data was sent correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert 'test_form_id' in call_args[0][0]
            assert call_args[1]['data']['entry.123'] == '2025-07-27T10:00:00'
            assert call_args[1]['data']['entry.456'] == 5.0
    
    @patch('requests.post')
    def test_send_to_google_sheets_no_form_id(self, mock_post):
        """Test when Google Form ID is not configured"""
        test_data = {'indoor_pm25': 5.0}
        
        with patch.dict('os.environ', {}, clear=True):
            result = collect_air_quality.send_to_google_sheets(test_data)
            assert result is False
            mock_post.assert_not_called()


class TestMainFlow:
    """Test the main collection flow"""
    
    @patch('collect_air_quality.send_to_google_sheets')
    @patch('collect_air_quality.get_airgradient_data')
    @patch('collect_air_quality.get_airthings_data')
    @patch('builtins.print')
    def test_main_success_flow(self, mock_print, mock_airthings, mock_airgradient, mock_sheets):
        """Test successful end-to-end flow"""
        mock_airthings.return_value = {
            'pm25': 5.0,
            'co2': 450,
            'temp': 22.5,
            'humidity': 45,
            'voc': 50
        }
        
        mock_airgradient.return_value = {
            'pm25': 10.0,
            'co2': 420,
            'temp': 25.0,
            'humidity': 50,
            'voc': 100,
            'nox': 1
        }
        
        mock_sheets.return_value = True
        
        with patch('builtins.open', create=True):
            collect_air_quality.main()
        
        # Verify APIs were called
        mock_airthings.assert_called_once()
        mock_airgradient.assert_called_once()
        mock_sheets.assert_called_once()
        
        # Verify efficiency calculation
        sheets_data = mock_sheets.call_args[0][0]
        assert sheets_data['indoor_pm25'] == 5.0
        assert sheets_data['outdoor_pm25'] == 10.0
        assert sheets_data['filter_efficiency'] == 50.0
        
        # Verify console output
        print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
        assert any('Indoor PM2.5: 5' in call for call in print_calls)
        assert any('Filter Efficiency: 50.0%' in call for call in print_calls)
    
    @patch('collect_air_quality.get_airthings_data')
    @patch('builtins.print')
    def test_main_airthings_failure(self, mock_print, mock_airthings):
        """Test when Airthings API fails"""
        mock_airthings.return_value = None
        
        collect_air_quality.main()
        
        # Verify error message
        print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
        assert any('Failed to get Airthings data' in call for call in print_calls)