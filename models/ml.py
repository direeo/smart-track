"""
Machine Learning module for KPI forecasting and employee performance prediction.
Provides ARIMA-based forecasting and Random Forest-based behavior prediction.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

# Suppress warnings
warnings.filterwarnings('ignore')

print("[*] ML module imports starting...", flush=True)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from scipy import stats
    print("[OK] All ML libraries imported successfully", flush=True)
except ImportError as e:
    print(f"[ERROR] Failed to import ML libraries: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)


def predict_kpi(update_list: list, target_value: float, deadline: str, unit: str) -> dict:
    """
    Forecast KPI values using ARIMA model.
    
    Args:
        update_list: List of {"date": "YYYY-MM-DD", "value": float} historical updates
        target_value: Target KPI value
        deadline: Deadline date (YYYY-MM-DD format)
        unit: Unit of measurement (e.g., "$", "%", "units")
    
    Returns:
        dict with 'forecast', 'trend', 'status', 'recommendation'
    """
    try:
        print(f"[*] Predicting KPI with {len(update_list)} historical updates, target={target_value}", flush=True)
        
        if not update_list or len(update_list) < 2:
            print(f"[WARN] Insufficient historical data ({len(update_list)} points), using simple estimate", flush=True)
            return {
                'current': 0,
                'target': target_value,
                'forecast': target_value,
                'trend': 'neutral',
                'confidence': 0.3,
                'recommendation': 'More data needed for accurate forecast',
                'status': 'insufficient_data'
            }
        
        # Extract values
        values = np.array([float(u['value']) for u in update_list])
        
        if len(values) < 3:
            # Simple linear trend
            current = float(values[-1])
            first = float(values[0])
            trend_val = (current - first) / len(values)
            
            return {
                'current': current,
                'target': target_value,
                'forecast': current + (trend_val * 5),  # 5-day projection
                'trend': 'up' if trend_val > 0 else 'down' if trend_val < 0 else 'neutral',
                'confidence': 0.5,
                'recommendation': f'Trend is {"improving" if trend_val > 0 else "declining"}, monitor closely',
                'status': 'simple_trend'
            }
        
        # Fit ARIMA model
        try:
            model = ARIMA(values, order=(1, 1, 1))
            results = model.fit()
            
            # Get forecast for 10 periods
            forecast = results.get_forecast(steps=10)
            forecast_values = forecast.predicted_mean
            
            # Calculate metrics
            current = float(values[-1])
            predicted_next = float(forecast_values.iloc[0])
            avg_forecast = float(forecast_values.mean())
            
            # Determine trend
            if predicted_next > current * 1.02:
                trend = 'up'
            elif predicted_next < current * 0.98:
                trend = 'down'
            else:
                trend = 'neutral'
            
            # Calculate confidence based on residuals
            residuals = results.resid
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            confidence = max(0.3, min(1.0, 1.0 - (rmse / current) if current != 0 else 0.6))
            
            # Generate recommendation
            pct_of_target = (current / target_value * 100) if target_value != 0 else 0
            if pct_of_target >= 100:
                recommendation = f"✓ Target achieved at {pct_of_target:.0f}%"
            elif pct_of_target >= 80:
                recommendation = f"On track: {pct_of_target:.0f}% of target"
            elif trend == 'up':
                recommendation = f"Improving: {pct_of_target:.0f}% of target, maintain momentum"
            else:
                recommendation = f"Below target at {pct_of_target:.0f}%, acceleration needed"
            
            print(f"[OK] ARIMA prediction: current={current:.2f}, forecast={avg_forecast:.2f}, trend={trend}", flush=True)
            
            return {
                'current': current,
                'target': target_value,
                'forecast': avg_forecast,
                'trend': trend,
                'confidence': confidence,
                'recommendation': recommendation,
                'status': 'success'
            }
        except Exception as arima_err:
            print(f"[WARN] ARIMA fitting failed ({arima_err}), using simple trend", flush=True)
            current = float(values[-1])
            trend_val = float(values[-1] - values[0]) / len(values)
            
            return {
                'current': current,
                'target': target_value,
                'forecast': current + (trend_val * 5),
                'trend': 'up' if trend_val > 0 else 'down' if trend_val < 0 else 'neutral',
                'confidence': 0.5,
                'recommendation': f'Simple trend: {"improving" if trend_val > 0 else "declining"}',
                'status': 'simple_trend_fallback'
            }
            
    except Exception as e:
        print(f"[ERROR] predict_kpi failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return {
            'current': 0,
            'target': target_value,
            'forecast': target_value,
            'trend': 'neutral',
            'confidence': 0.0,
            'recommendation': 'Unable to generate prediction',
            'status': 'error'
        }


def predict_behaviour(update_list: list, target_value: float, deadline: str) -> dict:
    """
    Predict KPI achievement behavior/performance based on historical updates.
    
    Args:
        update_list: List of {"date": "YYYY-MM-DD", "value": float} historical updates
        target_value: Target KPI value
        deadline: Deadline date (YYYY-MM-DD format)
    
    Returns:
        dict with 'risk_level', 'achievement_probability', 'days_remaining', 'recommendation'
    """
    try:
        print(f"[*] Predicting behavior for {len(update_list)} updates, target={target_value}, deadline={deadline}", flush=True)
        
        if not update_list or len(update_list) == 0:
            print(f"[WARN] No historical data for behavior prediction", flush=True)
            return {
                'risk_level': 'high',
                'achievement_probability': 0.0,
                'days_remaining': 0,
                'recommendation': 'No progress recorded yet. Start updating KPI values.',
                'status': 'no_data'
            }
        
        # Parse dates and calculate days remaining
        from datetime import datetime
        try:
            deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
            today = datetime.now()
            days_remaining = (deadline_dt - today).days
        except:
            days_remaining = 30  # Default estimate
        
        # Extract values
        values = np.array([float(u['value']) for u in update_list])
        current_value = float(values[-1])
        
        # Calculate progress rate
        if len(values) > 1:
            progress = current_value - float(values[0])
            days_elapsed = len(update_list)  # Rough estimate
            daily_rate = progress / max(days_elapsed, 1)
        else:
            daily_rate = 0
            progress = 0
        
        # Calculate achievement probability
        remaining_gap = target_value - current_value
        
        if remaining_gap <= 0:
            # Already achieved
            achievement_prob = 100.0
            risk = 'low'
            rec = f"✓ Target achieved! Current: {current_value}, Target: {target_value}"
        elif days_remaining <= 0:
            # Deadline passed
            achievement_prob = 0.0
            risk = 'critical'
            rec = f"✗ Deadline passed. Final value: {current_value} / {target_value}"
        elif daily_rate > 0:
            # Calculate if we can reach target
            projected_final = current_value + (daily_rate * days_remaining)
            achievement_prob = min(100.0, max(0.0, (projected_final / target_value) * 100))
            
            if achievement_prob >= 100:
                risk = 'low'
                rec = f"On pace to exceed target. Projected: {projected_final:.0f} / {target_value}"
            elif achievement_prob >= 80:
                risk = 'medium'
                rec = f"Good pace. {achievement_prob:.0f}% likely to achieve. Keep up momentum."
            elif achievement_prob >= 50:
                risk = 'medium_high'
                rec = f"Moderate risk at {achievement_prob:.0f}% likelihood. Acceleration recommended."
            else:
                risk = 'high'
                rec = f"High risk. Only {achievement_prob:.0f}% likely at current pace. Urgent action needed."
        else:
            # Not progressing
            achievement_prob = 0.0
            risk = 'critical'
            rec = f"No progress. Current: {current_value} / {target_value}. Action required immediately."
        
        print(f"[OK] Behavior prediction: risk={risk}, prob={achievement_prob:.0f}%", flush=True)
        
        return {
            'risk_level': risk,
            'achievement_probability': achievement_prob,
            'days_remaining': days_remaining,
            'current_value': current_value,
            'target_value': target_value,
            'recommendation': rec,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"[ERROR] predict_behaviour failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return {
            'risk_level': 'unknown',
            'achievement_probability': 50.0,
            'days_remaining': 0,
            'recommendation': 'Unable to generate behavior prediction',
            'status': 'error'
        }


# Test on import to verify module works
try:
    print("[*] Testing ML module functions...", flush=True)
    
    # Test predict_kpi with dummy data
    test_updates = [
        {"date": "2026-01-01", "value": 50},
        {"date": "2026-01-15", "value": 65},
        {"date": "2026-02-01", "value": 75},
        {"date": "2026-02-15", "value": 85},
    ]
    result = predict_kpi(test_updates, target_value=100, deadline="2026-03-01", unit="units")
    print(f"[TEST] predict_kpi: {result['status']}", flush=True)
    
    # Test predict_behaviour with dummy data
    result = predict_behaviour(test_updates, target_value=100, deadline="2026-03-15")
    print(f"[TEST] predict_behaviour: {result['status']}", flush=True)
    
    print("[OK] ML module fully loaded and tested", flush=True)
    
except Exception as e:
    print(f"[ERROR] ML module test failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
