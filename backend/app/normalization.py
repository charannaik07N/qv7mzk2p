"""Dataset-specific parsers. Conflicting records are excluded, never averaged."""
import math
import pandas as pd

COLUMNS = ['startTime', 'publishTime', 'generation']

def records(payload):
    if not isinstance(payload, list) or any(not isinstance(r, dict) for r in payload):
        raise ValueError('Expected the stream endpoint JSON array of objects')
    return payload

def stamp(value):
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:
        raise ValueError('A valid timezone-aware source timestamp is required')
    return t.tz_convert('UTC')

def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Missing or invalid generation')
    v = float(value)
    if not math.isfinite(v) or v < 0:
        raise ValueError('Generation must be finite and nonnegative')
    return v

def _normalize(rows, forecast):
    valid, invalid = [], 0
    for r in rows:
        try:
            t = stamp(r['startTime'])
            if t.minute % 30 or t.second or t.microsecond:
                raise ValueError('Not a settlement boundary')
            p = stamp(r['publishTime']) if forecast else (stamp(r['publishTime']) if r.get('publishTime') else t)
            valid.append({'startTime': t, 'publishTime': p, 'generation': number(r['generation'])})
        except (ValueError, KeyError, TypeError, OverflowError):
            invalid += 1
    frame = pd.DataFrame(valid, columns=COLUMNS)
    for c in ['startTime', 'publishTime']:
        frame[c] = pd.to_datetime(frame[c], utc=True)
    keys = ['startTime', 'publishTime']
    duplicates = len(frame) - len(frame.drop_duplicates())
    frame = frame.drop_duplicates()
    conflicts = frame.groupby(keys).generation.nunique()
    conflict_keys = set(conflicts[conflicts > 1].index)
    conflict_rows = frame.apply(lambda r: (r.startTime, r.publishTime) in conflict_keys, axis=1) if len(frame) else pd.Series([], dtype=bool)
    frame = frame.loc[~conflict_rows].copy()
    if not forecast:
        # Latest outturn revision; actuals are eventual, not as-of actuals.
        frame = frame.sort_values(keys).drop_duplicates('startTime', keep='last')
    return frame.sort_values(keys).reset_index(drop=True), {
        'invalid': invalid, 'duplicates': duplicates, 'conflicting_keys': len(conflict_keys)}

def normalize_actuals(payload):
    return _normalize([r for r in records(payload) if r.get('fuelType') == 'WIND'], False)

def normalize_forecasts(payload):
    return _normalize(records(payload), True)
