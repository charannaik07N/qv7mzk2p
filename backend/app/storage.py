"""Versioned snapshots with an atomic pointer; failed refresh preserves old data."""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .config import DATA_DIR, HISTORY_WARNING
from .normalization import normalize_actuals, normalize_forecasts, COLUMNS
from .source import acquire

log = logging.getLogger(__name__)

def empty():
    f = pd.DataFrame(columns=COLUMNS)
    for c in ['startTime', 'publishTime']:
        f[c] = pd.to_datetime(f[c], utc=True)
    return f

class Store:
    def __init__(self, directory=DATA_DIR):
        self.directory = Path(directory)
        self.lock = asyncio.Lock()
        self.refresh_state = {'state': 'idle', 'message': None}
        self.refresh_task = None
        self.last_refresh_started = 0.0
        self.version = None
        self.actuals, self.forecasts = empty(), empty()
        self.meta = {'status': 'unavailable', 'lastSuccessfulRefresh': None, 'warning': HISTORY_WARNING}
        self.load()

    def load(self):
        try:
            pointer = (self.directory/'current.json').read_text()
            version = json.loads(pointer)['version']
            if version == self.version:
                return
            if not isinstance(version, str) or not version.isalnum():
                raise ValueError('Invalid snapshot identifier')
            path = self.directory/version
            a, f = pd.read_csv(path/'actuals.csv'), pd.read_csv(path/'forecasts.csv')
            for frame in [a, f]:
                for col in ['startTime', 'publishTime']:
                    frame[col] = pd.to_datetime(frame[col], utc=True)
                if frame.generation.isna().any() or not frame.generation.ge(0).all():
                    raise ValueError('Invalid snapshot generation')
            meta = json.loads((path/'metadata.json').read_text())
            self.actuals, self.forecasts, self.meta, self.version = a, f, meta, version
        except FileNotFoundError:
            pass
        except (ValueError, KeyError, OSError):
            log.exception('Snapshot load failed; preserving last valid in-memory snapshot')
            self.meta = {**self.meta, 'cacheReadError': 'Snapshot could not be read; repair or refresh it.'}

    async def refresh(self):
        if self.lock.locked():
            raise RuntimeError('Refresh already in progress')
        async with self.lock:
            log.info('Elexon refresh started: January 2026 FUELHH and WINDFOR')
            self.refresh_state = {'state': 'loading', 'message': 'Downloading official January observations and forecast publications. This can take several minutes.'}
            try:
                a_raw, f_raw, spec = await acquire()
                a, aq = normalize_actuals(a_raw)
                f, fq = normalize_forecasts(f_raw)
                start, end = pd.Timestamp('2026-01-01', tz='UTC'), pd.Timestamp('2026-02-01', tz='UTC')
                a = a[(a.startTime >= start) & (a.startTime < end)]
                f = f[(f.startTime >= start) & (f.startTime < end)]
                if a.empty or f.empty:
                    raise ValueError('No valid January records in one or both datasets; existing snapshot preserved')
                version = uuid.uuid4().hex
                path = self.directory/version
                path.mkdir(parents=True)
                a.to_csv(path/'actuals.csv', index=False)
                f.to_csv(path/'forecasts.csv', index=False)
                meta = {'status': 'cached', 'lastSuccessfulRefresh': datetime.now(timezone.utc).isoformat(),
                        'actualRecords': len(a), 'forecastRecords': len(f), 'actualQuality': aq, 'forecastQuality': fq,
                        'actualIntervals': int(a.startTime.nunique()), 'forecastIntervals': int(f.startTime.nunique()),
                        'multipleVintageIntervals': int((f.groupby('startTime').size()>1).sum()),
                        'source': 'Elexon FUELHH/WINDFOR stream', 'warning': HISTORY_WARNING,
                        'publicationWindow': 'FUELHH Jan 1–Feb 4; WINDFOR Dec 25–Feb 2 (exclusive ends)',
                        'historyComplete': False}
                (path/'metadata.json').write_text(json.dumps(meta, indent=2))
                (path/'source-openapi.json').write_text(json.dumps(spec))
                tmp = self.directory/f'pointer-{version}.tmp'
                tmp.write_text(json.dumps({'version': version}))
                os.replace(tmp, self.directory/'current.json')
                self.load()
                self.refresh_state = {'state': 'complete', 'message': 'Official snapshot loaded.'}
                log.info('Elexon refresh completed: actual_intervals=%d forecast_intervals=%d snapshot=%s', meta['actualIntervals'], meta['forecastIntervals'], version)
                return self.meta
            except Exception as exc:
                self.refresh_state = {'state': 'failed', 'message': str(exc)}
                log.exception('Refresh failed; existing cache preserved')
                raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        print(json.dumps(asyncio.run(Store().refresh()), indent=2))
    except Exception as exc:
        raise SystemExit(f'Refresh failed: {exc}. No synthetic fallback. Check network and official API documentation.')
