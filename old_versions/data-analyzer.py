#!/usr/bin/env python3
"""
HVAC/ERV Investment Analysis
Analyzes air quality improvements and calculates ROI
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirQualityAnalyzer:
    """Analyze air quality data and HVAC/ERV effectiveness"""
    
    def __init__(self):
        self.data = None
        self.timeline = {
            'hvac_install': pd.Timestamp('2024-02-20'),  # Adjust to your actual date
            'erv_install': pd.Timestamp('2024-03-15'),   # Adjust to your actual date
            'filter_upgrade': pd.Timestamp('2024-06-01')  # MERV 8 to MERV 13
        }
        
    def load_sensor_data(self, data_dir="data/raw"):
        """Load all sensor data files"""
        data_path = Path(data_dir)
        sensor_files = sorted(data_path.glob("sensors_*.json"))
        
        all_data = []
        for file in sensor_files:
            with open(file, 'r') as f:
                data = json.load(f)
                if data.get('results'):
                    for result in data['results']:
                        record = {
                            'timestamp': pd.to_datetime(result['recorded']),
                            'battery': result.get('batteryPercentage'),
                            'serial': result['serialNumber']
                        }
                        # Extract sensor values
                        for sensor in result['sensors']:
                            record[sensor['sensorType']] = sensor['value']
                        all_data.append(record)
        
        self.data = pd.DataFrame(all_data)
        self.data.set_index('timestamp', inplace=True)
        self.data.sort_index(inplace=True)
        
        logger.info(f"Loaded {len(self.data)} records from {len(sensor_files)} files")
        logger.info(f"Date range: {self.data.index.min()} to {self.data.index.max()}")
        
        return self.data
    
    def add_phase_labels(self):
        """Add labels for different phases of the project"""
        self.data['phase'] = 'baseline'
        
        # Mark different phases
        mask_hvac = self.data.index >= self.timeline['hvac_install']
        self.data.loc[mask_hvac, 'phase'] = 'hvac_only'
        
        mask_erv = self.data.index >= self.timeline['erv_install']
        self.data.loc[mask_erv, 'phase'] = 'hvac_erv'
        
        mask_filter = self.data.index >= self.timeline['filter_upgrade']
        self.data.loc[mask_filter, 'phase'] = 'merv13'
        
    def calculate_improvements(self):
        """Calculate air quality improvements by phase"""
        # Key metrics to analyze
        metrics = ['pm25', 'pm1', 'co2', 'voc', 'humidity', 'temp']
        available_metrics = [m for m in metrics if m in self.data.columns]
        
        # Calculate statistics by phase
        improvements = {}
        for metric in available_metrics:
            phase_stats = self.data.groupby('phase')[metric].agg(['mean', 'std', 'min', 'max'])
            improvements[metric] = phase_stats
            
        return improvements
    
    def plot_timeline(self, metric='pm25', save_path='data/figures'):
        """Plot air quality metric over time with phase markers"""
        plt.figure(figsize=(14, 8))
        
        # Plot the metric
        if metric in self.data.columns:
            plt.plot(self.data.index, self.data[metric], alpha=0.6, label='Raw data')
            
            # Add rolling average
            rolling = self.data[metric].rolling('7D').mean()
            plt.plot(self.data.index, rolling, linewidth=2, label='7-day average')
            
            # Add phase markers
            for event, date in self.timeline.items():
                plt.axvline(x=date, color='red', linestyle='--', alpha=0.7)
                plt.text(date, plt.ylim()[1]*0.95, event.replace('_', ' ').title(), 
                        rotation=45, verticalalignment='top')
            
            # Color backgrounds by phase
            phase_colors = {
                'baseline': 'lightgray',
                'hvac_only': 'lightblue', 
                'hvac_erv': 'lightgreen',
                'merv13': 'gold'
            }
            
            for phase, color in phase_colors.items():
                mask = self.data['phase'] == phase
                if mask.any():
                    start = self.data[mask].index.min()
                    end = self.data[mask].index.max()
                    plt.axvspan(start, end, alpha=0.2, color=color, label=phase)
            
            plt.xlabel('Date')
            plt.ylabel(f'{metric.upper()} Level')
            plt.title(f'{metric.upper()} Levels Over Time - HVAC/ERV Investment Analysis')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Save figure
            Path(save_path).mkdir(parents=True, exist_ok=True)
            plt.savefig(f'{save_path}/{metric}_timeline.png', dpi=300, bbox_inches='tight')
            plt.close()
            
    def calculate_roi(self, hvac_cost=10000, erv_cost=3000, filter_cost_diff=50):
        """Estimate ROI based on air quality improvements"""
        # This is a simplified ROI calculation
        # You should adjust based on:
        # - Energy savings from proper ventilation
        # - Health benefits (reduced allergies, better sleep)
        # - Productivity improvements from better CO2 levels
        
        improvements = self.calculate_improvements()
        
        roi_factors = {
            'energy_savings': 0,  # Estimate monthly energy savings
            'health_benefits': 0,  # Estimate health cost reductions
            'productivity': 0      # Estimate productivity gains
        }
        
        # Example: CO2 reduction leading to better cognitive performance
        if 'co2' in improvements:
            baseline_co2 = improvements['co2'].loc['baseline', 'mean']
            current_co2 = improvements['co2'].loc[self.data['phase'].iloc[-1], 'mean']
            co2_reduction = baseline_co2 - current_co2
            
            # Research shows ~15% cognitive improvement per 400ppm CO2 reduction
            if co2_reduction > 0:
                productivity_gain = (co2_reduction / 400) * 0.15
                roi_factors['productivity'] = productivity_gain * 2000  # Monthly value estimate
        
        return roi_factors
    
    def generate_report(self):
        """Generate summary report"""
        improvements = self.calculate_improvements()
        
        print("\n=== HVAC/ERV INVESTMENT ANALYSIS REPORT ===\n")
        print(f"Analysis Period: {self.data.index.min().date()} to {self.data.index.max().date()}")
        print(f"Total Days Analyzed: {(self.data.index.max() - self.data.index.min()).days}")
        
        print("\n--- Air Quality Improvements by Phase ---")
        for metric, stats in improvements.items():
            print(f"\n{metric.upper()}:")
            print(stats)
            
            # Calculate percentage improvements
            if 'baseline' in stats.index:
                baseline = stats.loc['baseline', 'mean']
                for phase in ['hvac_only', 'hvac_erv', 'merv13']:
                    if phase in stats.index:
                        current = stats.loc[phase, 'mean']
                        if metric in ['pm25', 'pm1', 'co2', 'voc']:  # Lower is better
                            improvement = ((baseline - current) / baseline) * 100
                            print(f"  {phase}: {improvement:.1f}% reduction")
                        else:  # Higher might be better (like controlled humidity)
                            change = ((current - baseline) / baseline) * 100
                            print(f"  {phase}: {change:+.1f}% change")

def main():
    """Run the analysis"""
    analyzer = AirQualityAnalyzer()
    
    # Load data
    analyzer.load_sensor_data()
    
    # Add phase labels
    analyzer.add_phase_labels()
    
    # Generate visualizations
    for metric in ['pm25', 'co2', 'voc', 'humidity']:
        if metric in analyzer.data.columns:
            analyzer.plot_timeline(metric)
    
    # Generate report
    analyzer.generate_report()
    
    # Calculate ROI
    roi = analyzer.calculate_roi()
    print("\n--- ROI Estimates ---")
    for factor, value in roi.items():
        print(f"{factor}: ${value:.2f}/month")

if __name__ == "__main__":
    main()
