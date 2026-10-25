"""Temporal evaluation over a complete UK settlement grid."""
from datetime import timedelta
import numpy as np
import pandas as pd
from .config import DEFAULT_CUTOFF


def settlement_grid(day):
    local = pd.Timestamp(day).tz_localize('Europe/London')
    end = pd.Timestamp(pd.Timestamp(day).date() + timedelta(days=1)).tz_localize('Europe/London')
    return pd.date_range(local.tz_convert('UTC'), end.tz_convert('UTC'), freq='30min', inclusive='left')

def decision_for(day, cutoff=DEFAULT_CUTOFF):
    previous = pd.Timestamp(day).date() - timedelta(days=1)
    return pd.Timestamp(f'{previous}T{cutoff}').tz_localize('Europe/London').tz_convert('UTC')

def evaluate(actuals, forecasts, day, decision=None, mode='decision', cutoff=DEFAULT_CUTOFF):
    decision = pd.Timestamp(decision) if decision is not None else decision_for(day, cutoff)
    if decision.tzinfo is None:
        raise ValueError('Decision timestamp must include timezone')
    decision = decision.tz_convert('UTC')
    grid = settlement_grid(day)
    f = forecasts[forecasts.startTime.isin(grid)].copy()
    if mode == 'decision':
        f = f[f.publishTime <= decision]
    f = f.sort_values(['startTime', 'publishTime']).drop_duplicates('startTime', keep='last')
    frame = pd.DataFrame({'startTime': grid, 'settlementPeriod': range(1, len(grid)+1)})
    frame = frame.merge(actuals[['startTime', 'generation']].rename(columns={'generation': 'actual'}), on='startTime', how='left', validate='one_to_one')
    frame = frame.merge(f.rename(columns={'generation': 'forecast'}), on='startTime', how='left', validate='one_to_one')
    frame['decisionTime'] = decision
    frame['forecastAgeHours'] = (decision - frame.publishTime).dt.total_seconds() / 3600 if mode == 'decision' else np.nan
    frame['leadTimeHours'] = (frame.startTime - frame.publishTime).dt.total_seconds() / 3600
    frame['error'] = frame.forecast - frame.actual
    frame['absoluteError'] = frame.error.abs()
    frame['percentageError'] = 100 * frame.error / frame.actual.replace(0, np.nan)
    frame['status'] = np.select([frame.actual.isna() & frame.forecast.isna(), frame.actual.isna(), frame.forecast.isna()], ['missing_both', 'missing_actual', 'missing_forecast'], default='matched')
    return frame

def metrics(frame):
    paired = frame.dropna(subset=['actual', 'forecast'])
    n, total = len(paired), len(frame)
    def mean(col):
        return float(paired[col].mean()) if n else None
    denominator = float(paired.actual.abs().sum())
    return {
        'sampleSize': n, 'expectedIntervals': total,
        'coverage': 100*n/total if total else 0,
        'missingActual': int(frame.actual.isna().sum()),
        'missingForecast': int(frame.forecast.isna().sum()),
        'mae': mean('absoluteError'),
        'rmse': float(np.sqrt((paired.error**2).mean())) if n else None,
        'bias': mean('error'), 'averageActual': mean('actual'), 'averageForecast': mean('forecast'),
        'maxAbsoluteError': float(paired.absoluteError.max()) if n else None,
        'wape': float(100*paired.absoluteError.sum()/denominator) if denominator else None,
        'wapeDenominatorMW': denominator, 'percentageSampleSize': int((paired.actual != 0).sum()),
        'overforecastCount': int((paired.error > 0).sum()),
        'underforecastCount': int((paired.error < 0).sum()), 'exactCount': int((paired.error == 0).sum()),
    }

def residual(demand, forecast, actual=None, actual_demand=None):
    estimated = max(0, demand-forecast)
    realized = max(0, (demand if actual_demand is None else actual_demand)-actual) if actual is not None else None
    return {'estimatedResidualMW': estimated, 'actualResidualMW': realized,
            'residualErrorMW': estimated-realized if realized is not None else None,
            'demandSource': 'user-supplied scenario',
            'actualDemandAssumption': 'same user-supplied demand' if actual_demand is None else 'separate user-supplied actual demand',
            'limitation': 'Wind-only scenario; omits other generation, interconnectors, balancing, contracts and demand uncertainty. This is not a procurement order.'}
