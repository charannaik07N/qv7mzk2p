"""Bounded, retrying official API access. Schema checked before acquisition."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import httpx
from .config import API_BASE

log = logging.getLogger(__name__)

class ElexonClient:
    def __init__(self, transport=None):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(45, connect=10), transport=transport, follow_redirects=True)
        self.semaphore = asyncio.Semaphore(2)

    async def close(self):
        await self.client.aclose()

    async def get(self, url, params=None):
        async with self.semaphore:
            for attempt in range(4):
                try:
                    response = await self.client.get(url, params=params)
                    if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                        if attempt < 3:
                            try:
                                delay = float(response.headers.get('Retry-After', 2**attempt))
                            except ValueError:
                                delay = 2**attempt
                            await asyncio.sleep(min(max(delay, 0), 30))
                            continue
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.NetworkError):
                    log.warning('Elexon request failed: %s attempt=%s', url, attempt+1)
                    if attempt == 3:
                        raise
                    await asyncio.sleep(2**attempt)
                except (httpx.HTTPError, ValueError):
                    log.exception('Elexon response failure: %s', url)
                    raise

    async def verify_schema(self):
        # Do not silently guess changed query semantics. Save the retrieved spec.
        candidates = ['https://data.elexon.co.uk/swagger/v1/swagger.json']
        last = None
        for url in candidates:
            try:
                spec = await self.get(url)
                for dataset in ['FUELHH', 'WINDFOR']:
                    path = next(v for k, v in spec['paths'].items() if k.lower().endswith(f'/datasets/{dataset.lower()}/stream'))
                    names = {p['name'] for p in path['get'].get('parameters', [])}
                    if not {'publishDateTimeFrom', 'publishDateTimeTo'} <= names:
                        raise ValueError(f'{dataset}: publication query parameters not verified. Review official schema before changing client.')
                return spec
            except (httpx.HTTPError, ValueError, KeyError, StopIteration) as exc:
                last = exc
        raise ValueError(f'Could not verify official stream publication-query schemas: {last}. Check internet/DNS access to data.elexon.co.uk.') from last

    async def dataset(self, name, start, end):
        async def chunk(a, b):
            result = await self.get(f'{API_BASE}/datasets/{name}/stream', {
                'publishDateTimeFrom': a.isoformat(), 'publishDateTimeTo': b.isoformat()})
            if not isinstance(result, list):
                raise ValueError(f'{name}: expected JSON array; no snapshot written')
            return result
        # Two in flight, one-day chunks, no pagination assumed for stream arrays.
        output = []
        while start < end:
            batch = []
            for _ in range(2):
                if start >= end:
                    break
                nxt = min(start+timedelta(days=1), end)
                batch.append(chunk(start, nxt))
                start = nxt
            for rows in await asyncio.gather(*batch):
                output.extend(rows)
        return output

async def acquire():
    client = ElexonClient()
    try:
        spec = await client.verify_schema()
        actuals = await client.dataset('FUELHH', datetime(2026,1,1,tzinfo=timezone.utc), datetime(2026,2,4,tzinfo=timezone.utc))
        forecasts = await client.dataset('WINDFOR', datetime(2025,12,25,tzinfo=timezone.utc), datetime(2026,2,2,tzinfo=timezone.utc))
        return actuals, forecasts, spec
    finally:
        await client.close()
