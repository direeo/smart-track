"""
Machine Learning module for KPI forecasting and employee performance prediction.
Provides ARIMA-based forecasting and linear trajectory-based behaviour prediction.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

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


def _parse_deadline(deadline: str):
    """Returns (deadline_dt, days_remaining, deadline_passed)."""
    try:
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_remaining = (deadline_dt - today).days
        return deadline_dt, days_remaining, days_remaining < 0
    except Exception:
        return None, 30, False


def _daily_rate(update_list: list) -> float:
    """Calculate average daily progress rate using real calendar dates."""
    if len(update_list) < 2:
        return 0.0
    try:
        first_dt = datetime.strptime(update_list[0]['date'], '%Y-%m-%d')
        last_dt  = datetime.strptime(update_list[-1]['date'], '%Y-%m-%d')
        days_elapsed = max(1, (last_dt - first_dt).days)
        return (float(update_list[-1]['value']) - float(update_list[0]['value'])) / days_elapsed
    except Exception:
        # Fall back to rate-per-entry if dates are bad
        elapsed = max(1, len(update_list) - 1)
        return (float(update_list[-1]['value']) - float(update_list[0]['value'])) / elapsed


def predict_kpi(update_list: list, target_value: float, deadline: str, unit: str) -> dict:
    """
    Forecast what value the employee will reach by their deadline at their current pace.
    Uses ARIMA to detect trend direction; uses linear rate projection to answer the
    deadline question directly.
    """
    try:
        print(f"[*] predict_kpi: {len(update_list)} updates, target={target_value}, deadline={deadline}", flush=True)

        _, days_remaining, deadline_passed = _parse_deadline(deadline)

        # ── Not enough data ───────────────────────────────────────────────────
        if not update_list or len(update_list) < 2:
            base = {
                'current': float(update_list[0]['value']) if update_list else 0,
                'target': target_value,
                'forecast': 0,
                'projected_at_deadline': 0,
                'deadline': deadline,
                'deadline_passed': deadline_passed,
                'days_remaining': days_remaining,
                'trend': 'neutral',
                'confidence': 0.0,
                'status': 'insufficient_data',
            }
            if deadline_passed:
                base['recommendation'] = f"Your deadline of {deadline} has passed. Log more data to enable analysis."
            else:
                base['recommendation'] = "Log at least 2 progress updates so the system can generate a forecast."
            return base

        values  = np.array([float(u['value']) for u in update_list])
        current = float(values[-1])
        rate    = _daily_rate(update_list)

        # ── Deadline already passed ───────────────────────────────────────────
        if deadline_passed:
            pct = (current / target_value * 100) if target_value else 0
            print(f"[OK] Deadline passed — achieved {pct:.0f}%", flush=True)
            return {
                'current': current,
                'target': target_value,
                'forecast': current,
                'projected_at_deadline': current,
                'deadline': deadline,
                'deadline_passed': True,
                'days_remaining': days_remaining,
                'trend': 'neutral',
                'confidence': 1.0,
                'recommendation': (
                    f"Your deadline of {deadline} has passed. "
                    f"You finished at {current:.1f} {unit} out of a target of {target_value} {unit} "
                    f"({pct:.0f}% achieved)."
                ),
                'status': 'deadline_passed',
            }

        # ── Project to deadline ───────────────────────────────────────────────
        projected = current + (rate * days_remaining) if days_remaining > 0 else current

        # ── Use ARIMA to refine trend direction (best-effort) ─────────────────
        trend      = 'up' if rate > 0 else ('down' if rate < 0 else 'neutral')
        confidence = 0.65
        try:
            if len(values) >= 3:
                model   = ARIMA(values, order=(1, 1, 1))
                results = model.fit()
                arima_next = float(results.get_forecast(steps=1).predicted_mean.iloc[0])
                if arima_next > current * 1.02:
                    trend = 'up'
                elif arima_next < current * 0.98:
                    trend = 'down'
                rmse       = float(np.sqrt(np.mean(results.resid ** 2)))
                confidence = max(0.4, min(0.95, 1.0 - rmse / max(abs(current), 1)))
        except Exception as arima_err:
            print(f"[WARN] ARIMA skipped: {arima_err}", flush=True)

        # ── Recommendation ────────────────────────────────────────────────────
        gap = target_value - projected
        if projected >= target_value:
            rec = (
                f"At your current pace you are on track to reach {projected:.1f} {unit} by {deadline}, "
                f"meeting or exceeding the target of {target_value} {unit}."
            )
        else:
            rec = (
                f"At your current pace you will reach {projected:.1f} {unit} by {deadline}. "
                f"You are {gap:.1f} {unit} short of the target — you need to increase your pace to close the gap."
            )

        print(f"[OK] predict_kpi: projected={projected:.2f}, trend={trend}", flush=True)
        return {
            'current': current,
            'target': target_value,
            'forecast': projected,
            'projected_at_deadline': projected,
            'deadline': deadline,
            'deadline_passed': False,
            'days_remaining': days_remaining,
            'trend': trend,
            'confidence': confidence,
            'recommendation': rec,
            'status': 'success',
        }

    except Exception as e:
        print(f"[ERROR] predict_kpi failed: {e}", file=sys.stderr, flush=True)
        import traceback; traceback.print_exc(file=sys.stderr)
        return {
            'current': 0, 'target': target_value,
            'forecast': 0, 'projected_at_deadline': 0,
            'deadline': deadline, 'deadline_passed': False,
            'days_remaining': 30, 'trend': 'neutral',
            'confidence': 0.0,
            'recommendation': 'Unable to generate forecast.',
            'status': 'error',
        }


def predict_behaviour(update_list: list, target_value: float, deadline: str) -> dict:
    """
    Analyse the employee's progress trajectory and tell them what they need to do
    to hit their target by the deadline — or, if the deadline has passed, what to
    improve for next time.
    """
    try:
        print(f"[*] predict_behaviour: {len(update_list)} updates, target={target_value}, deadline={deadline}", flush=True)

        _, days_remaining, deadline_passed = _parse_deadline(deadline)

        # ── No data ───────────────────────────────────────────────────────────
        if not update_list:
            return {
                'risk_level': 'high',
                'achievement_probability': 0.0,
                'days_remaining': days_remaining,
                'deadline_passed': deadline_passed,
                'current_rate': 0.0,
                'needed_rate': 0.0,
                'recommendation': (
                    "No progress recorded yet. "
                    "Start logging KPI updates so the system can analyse your trajectory."
                ),
                'status': 'no_data',
            }

        values        = np.array([float(u['value']) for u in update_list])
        current_value = float(values[-1])
        remaining_gap = target_value - current_value
        rate          = _daily_rate(update_list)

        # ── Target already achieved ───────────────────────────────────────────
        if remaining_gap <= 0:
            return {
                'risk_level': 'low',
                'achievement_probability': 100.0,
                'days_remaining': days_remaining,
                'deadline_passed': deadline_passed,
                'current_rate': round(rate, 3),
                'needed_rate': 0.0,
                'current_value': current_value,
                'target_value': target_value,
                'recommendation': f"Target achieved. Current value: {current_value:.1f} / {target_value}.",
                'status': 'success',
            }

        # ── Deadline passed ───────────────────────────────────────────────────
        if deadline_passed:
            pct = (current_value / target_value * 100) if target_value else 0
            # How much faster they would have needed to go (based on days from first to last update)
            try:
                first_dt   = datetime.strptime(update_list[0]['date'], '%Y-%m-%d')
                last_dt    = datetime.strptime(update_list[-1]['date'], '%Y-%m-%d')
                total_span = max(1, (last_dt - first_dt).days)
            except Exception:
                total_span = max(1, len(update_list) - 1)
            needed_rate_overall = target_value / max(total_span, 1) if target_value else 0

            rec = (
                f"Your deadline has passed. You reached {current_value:.1f} out of {target_value} ({pct:.0f}%). "
                f"You were averaging {rate:.2f} units/day. "
                f"To have hit the target in the same timeframe you would have needed {needed_rate_overall:.2f} units/day from the start. "
                f"For your next KPI, focus on starting faster and logging updates more regularly."
            )
            return {
                'risk_level': 'critical',
                'achievement_probability': min(100.0, pct),
                'days_remaining': days_remaining,
                'deadline_passed': True,
                'current_rate': round(rate, 3),
                'needed_rate': round(needed_rate_overall, 3),
                'current_value': current_value,
                'target_value': target_value,
                'recommendation': rec,
                'status': 'deadline_passed',
            }

        # ── Active KPI ────────────────────────────────────────────────────────
        needed_rate = remaining_gap / max(days_remaining, 1)

        if rate > 0:
            projected_final  = current_value + (rate * days_remaining)
            achievement_prob = min(100.0, max(0.0, (projected_final / target_value) * 100))
        else:
            projected_final  = current_value
            achievement_prob = 0.0

        # Risk level
        if achievement_prob >= 100:
            risk = 'low'
        elif achievement_prob >= 80:
            risk = 'medium'
        elif achievement_prob >= 50:
            risk = 'medium_high'
        else:
            risk = 'high'

        # Specific recommendation
        if rate <= 0:
            rec = (
                f"No progress detected. To reach {target_value} by {deadline} you need to average "
                f"{needed_rate:.2f} units/day — start logging updates immediately."
            )
        elif rate >= needed_rate:
            excess = rate - needed_rate
            rec = (
                f"You are averaging {rate:.2f} units/day and only need {needed_rate:.2f} units/day "
                f"to reach {target_value} by {deadline}. You have {excess:.2f} units/day of headroom — keep going."
            )
        else:
            shortfall_rate = needed_rate - rate
            rec = (
                f"You are averaging {rate:.2f} units/day but need {needed_rate:.2f} units/day "
                f"to reach {target_value} by {deadline}. "
                f"Increase your daily pace by {shortfall_rate:.2f} units to get back on track."
            )

        print(f"[OK] predict_behaviour: risk={risk}, prob={achievement_prob:.0f}%, rate={rate:.3f}, needed={needed_rate:.3f}", flush=True)
        return {
            'risk_level': risk,
            'achievement_probability': achievement_prob,
            'days_remaining': days_remaining,
            'deadline_passed': False,
            'current_rate': round(rate, 3),
            'needed_rate': round(needed_rate, 3),
            'current_value': current_value,
            'target_value': target_value,
            'recommendation': rec,
            'status': 'success',
        }

    except Exception as e:
        print(f"[ERROR] predict_behaviour failed: {e}", file=sys.stderr, flush=True)
        import traceback; traceback.print_exc(file=sys.stderr)
        return {
            'risk_level': 'unknown',
            'achievement_probability': 50.0,
            'days_remaining': 0,
            'deadline_passed': False,
            'current_rate': 0.0,
            'needed_rate': 0.0,
            'recommendation': 'Unable to generate behaviour prediction.',
            'status': 'error',
        }


# ── Smoke-test on import ───────────────────────────────────────────────────────
try:
    print("[*] Testing ML module functions...", flush=True)
    _test = [
        {"date": "2026-01-01", "value": 10},
        {"date": "2026-02-01", "value": 20},
        {"date": "2026-03-01", "value": 30},
        {"date": "2026-04-01", "value": 40},
    ]
    r1 = predict_kpi(_test, target_value=60, deadline="2026-12-01", unit="units")
    print(f"[TEST] predict_kpi: {r1['status']}, projected={r1.get('projected_at_deadline')}", flush=True)
    r2 = predict_behaviour(_test, target_value=60, deadline="2026-12-01")
    print(f"[TEST] predict_behaviour: {r2['status']}, rate={r2.get('current_rate')}", flush=True)
    print("[OK] ML module fully loaded and tested", flush=True)
except Exception as e:
    print(f"[ERROR] ML module test failed: {e}", file=sys.stderr, flush=True)
    import traceback; traceback.print_exc(file=sys.stderr)
