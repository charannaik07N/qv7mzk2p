import hmac
import logging
import asyncio
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from datetime import date, datetime
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import ADMIN_TOKEN, CORS_ORIGINS, DEFAULT_CUTOFF, HISTORY_WARNING, ENABLE_LOCAL_REFRESH, AUTO_REFRESH_ON_STARTUP
from .analytics import evaluate, metrics, residual
from .storage import Store

logging.basicConfig(level=logging.INFO)
async def background_refresh():
    try:
        await store.refresh()
    except Exception:
        pass  # Store records the actionable failure and logs the traceback.

@asynccontextmanager
async def lifespan(app):
    if AUTO_REFRESH_ON_STARTUP and store.meta['status'] == 'unavailable':
        store.refresh_task = asyncio.create_task(background_refresh())
    yield
    if store.refresh_task and not store.refresh_task.done():
        store.refresh_task.cancel()
        try:
            await store.refresh_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title='WindMarket Intelligence', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-Admin-Token'])
store = Store()

@app.exception_handler(Exception)
async def unexpected(request, exc):
    from fastapi.responses import JSONResponse
    logging.getLogger(__name__).exception('Unhandled API error', exc_info=exc)
    return JSONResponse(status_code=500, content={'detail': 'Unexpected server error. Check server logs.'})

def scope(day):
    if not date(2026,1,1) <= day <= date(2026,1,31):
        raise HTTPException(422, 'Delivery dates must be within January 2026')

def options(delivery_date: date = date(2026,1,15), decision_time: datetime | None = None,
            mode: Literal['decision', 'retrospective'] = 'decision',
            cutoff: str = Query(DEFAULT_CUTOFF, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')):
    scope(delivery_date)
    if decision_time is not None and (decision_time.tzinfo is None or decision_time.utcoffset() is None):
        raise HTTPException(422, 'decision_time must include a timezone offset')
    store.load()
    return delivery_date, decision_time, mode, cutoff

def frame_for(opts):
    return evaluate(store.actuals, store.forecasts, *opts[:3], cutoff=opts[3])

def serialize(frame):
    return __import__('json').loads(frame.to_json(orient='records', date_format='iso'))

@app.get('/api/health')
def health():
    return {'status': 'ok', 'dataStatus': store.meta['status']}

@app.get('/api/metadata')
def metadata():
    store.load()
    return {**store.meta, 'refresh': store.refresh_state, 'localRefreshEnabled': ENABLE_LOCAL_REFRESH, 'timezone': 'Europe/London', 'dateScope': ['2026-01-01','2026-01-31'],
            'defaultCutoff': DEFAULT_CUTOFF, 'expectedJanuaryIntervals': 1488,
            'sources': ['https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream',
                        'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream']}

@app.get('/api/overview')
def overview(opts=Depends(options)):
    frame = frame_for(opts)
    return {'metrics': metrics(frame), 'intervals': serialize(frame), 'metadata': metadata(),
            'mode': opts[2], 'decisionTime': frame.decisionTime.iloc[0].isoformat(), 'historyWarning': HISTORY_WARNING}

@app.get('/api/forecasts')
def forecasts(opts=Depends(options), settlement_period: int | None = Query(None, ge=1, le=48),
              page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=100),
              sort: Literal['startTime','forecast','actual','error','absoluteError','publishTime'] = 'startTime', descending: bool = False):
    frame = frame_for(opts)
    if settlement_period:
        frame = frame[frame.settlementPeriod == settlement_period]
    frame = frame.sort_values(sort, ascending=not descending, na_position='last')
    return {'total': len(frame), 'page': page, 'items': serialize(frame.iloc[(page-1)*page_size:page*page_size])}

@app.get('/api/forecast-history')
def history(opts=Depends(options), settlement_period: int = Query(1, ge=1, le=48)):
    evaluated = frame_for(opts)
    row = evaluated[evaluated.settlementPeriod == settlement_period].iloc[0]
    records = store.forecasts[store.forecasts.startTime == row.startTime].copy()
    records['eligible'] = records.publishTime <= row.decisionTime
    records['selected'] = records.publishTime == row.publishTime
    return {'items': serialize(records), 'selected': serialize(evaluated[evaluated.settlementPeriod == settlement_period])[0],
            'historyComplete': False, 'warning': HISTORY_WARNING}

@app.get('/api/accuracy')
def accuracy(opts=Depends(options), start_date: date = date(2026,1,1), end_date: date = date(2026,1,31)):
    scope(start_date); scope(end_date)
    if end_date < start_date:
        raise HTTPException(422, 'end_date must follow start_date')
    if opts[1] is not None and start_date != end_date:
        raise HTTPException(422, 'A custom decision timestamp requires a single delivery date. Use cutoff for daily day-ahead decisions.')
    frames, daily = [], []
    for day in pd.date_range(start_date, end_date):
        frame = evaluate(store.actuals, store.forecasts, day.date(), opts[1], opts[2], opts[3])
        frames.append(frame)
        daily.append({'date': str(day.date()), **metrics(frame)})
    all_rows = pd.concat(frames, ignore_index=True)
    paired = all_rows.dropna(subset=['error'])
    import numpy as np
    counts, bins = np.histogram(paired.error, bins=12) if len(paired) else ([], [])
    distribution = [{'range': f'{bins[i]:.0f} to {bins[i+1]:.0f}', 'count': int(c)} for i,c in enumerate(counts)]
    time_of_day = [{'settlementPeriod': int(k), **metrics(g)} for k,g in all_rows.groupby('settlementPeriod')]
    lead_bins = pd.cut(all_rows.leadTimeHours, [-float('inf'),0,12,24,36,48,float('inf')])
    lead_time = [{'leadTime': str(k), **metrics(g)} for k,g in all_rows.groupby(lead_bins, observed=True)]
    return {'mode': opts[2], 'metrics': metrics(all_rows), 'daily': daily, 'distribution': distribution,
            'timeOfDay': time_of_day, 'leadTime': lead_time}

class Scenario(BaseModel):
    demand_mw: float = Field(ge=0, le=200000, allow_inf_nan=False)
    actual_demand_mw: float | None = Field(None, ge=0, le=200000, allow_inf_nan=False)
    delivery_date: date
    settlement_period: int = Field(ge=1, le=48)
    decision_time: datetime | None = None
    cutoff: str = Field(DEFAULT_CUTOFF, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')

@app.post('/api/scenarios/residual-procurement')
def scenario(body: Scenario):
    opts = options(body.delivery_date, body.decision_time, 'decision', body.cutoff)
    frame = frame_for(opts)
    row = frame[frame.settlementPeriod == body.settlement_period].iloc[0]
    if pd.isna(row.forecast):
        raise HTTPException(409, 'No eligible forecast for this interval; refresh source data or change decision timestamp')
    result = residual(body.demand_mw, row.forecast, None if pd.isna(row.actual) else row.actual, body.actual_demand_mw)
    return {**result, 'interval': serialize(frame[frame.settlementPeriod == body.settlement_period])[0]}

@app.post('/api/admin/refresh')
async def refresh(x_admin_token: str = Header('')):
    if not ADMIN_TOKEN:
        raise HTTPException(503, 'Remote refresh disabled. Use the local acquisition command or configure ADMIN_TOKEN.')
    if not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(403, 'Invalid admin token')
    try:
        return await store.refresh()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except Exception:
        raise HTTPException(502, 'Elexon refresh failed. Existing cache preserved; check backend logs and official source availability.')


@app.post('/api/local/refresh', status_code=202)
async def local_refresh(request: Request):
    """Opt-in local development only; never enabled by the production containers."""
    if not ENABLE_LOCAL_REFRESH:
        raise HTTPException(403, 'Local refresh is disabled. Start with scripts/dev.sh or use the authenticated admin refresh.')
    hostname = urlparse(str(request.url)).hostname
    if not request.client or request.client.host not in ('127.0.0.1', '::1') or hostname not in ('localhost', '127.0.0.1', '::1'):
        raise HTTPException(403, 'Local refresh accepts loopback requests only')
    if request.headers.get('origin') not in ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000'):
        raise HTTPException(403, 'Untrusted refresh origin')
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'application/json is required')
    if store.lock.locked() or (store.refresh_task and not store.refresh_task.done()):
        return {'state': 'loading'}
    now = time.monotonic()
    if now - store.last_refresh_started < 60:
        raise HTTPException(429, 'Wait a minute before retrying Elexon.')
    store.last_refresh_started = now
    store.refresh_state = {'state': 'loading', 'message': 'Connecting to Elexon…'}
    store.refresh_task = asyncio.create_task(background_refresh())
    return {'state': 'loading'}
