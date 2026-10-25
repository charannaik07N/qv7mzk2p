import asyncio
import httpx
import pytest
from app.source import ElexonClient
from app.storage import Store

def test_retries_and_nonretryable_http(monkeypatch):
    calls=[]
    async def no_sleep(n):pass
    monkeypatch.setattr(asyncio,'sleep',no_sleep)
    def handler(request):
        calls.append(request)
        if len(calls)<3:return httpx.Response(429,headers={'Retry-After':'0'})
        return httpx.Response(200,json=[])
    async def run():
        c=ElexonClient(httpx.MockTransport(handler))
        assert await c.get('https://example.test')==[]
        await c.close()
    asyncio.run(run()); assert len(calls)==3
    def bad(request):return httpx.Response(400,json={'detail':'bad query'})
    async def run_bad():
        c=ElexonClient(httpx.MockTransport(bad))
        with pytest.raises(httpx.HTTPStatusError):await c.get('https://example.test')
        await c.close()
    asyncio.run(run_bad())

def test_failed_refresh_preserves_snapshot(tmp_path,monkeypatch):
    from app import storage
    s=Store(tmp_path)
    async def fail():raise ValueError('API unavailable')
    monkeypatch.setattr(storage,'acquire',fail)
    with pytest.raises(ValueError):asyncio.run(s.refresh())
    assert not (tmp_path/'current.json').exists()
    assert s.meta['status']=='unavailable'

def test_atomic_snapshot_and_reload(tmp_path,monkeypatch):
    from app import storage
    async def fixture():
        return ([{'startTime':'2026-01-01T00:00:00Z','fuelType':'WIND','generation':100}],
                [{'startTime':'2026-01-01T00:00:00Z','publishTime':'2025-12-31T08:00:00Z','generation':120}],{'paths':{}})
    monkeypatch.setattr(storage,'acquire',fixture)
    s=Store(tmp_path);asyncio.run(s.refresh())
    reloaded=Store(tmp_path)
    assert len(reloaded.actuals)==len(reloaded.forecasts)==1
    assert reloaded.meta['status']=='cached'
    old=(tmp_path/'current.json').read_text()
    async def fail():raise OSError('network')
    monkeypatch.setattr(storage,'acquire',fail)
    with pytest.raises(OSError):asyncio.run(s.refresh())
    assert (tmp_path/'current.json').read_text()==old
