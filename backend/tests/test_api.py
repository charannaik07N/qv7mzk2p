"""Synthetic fixture data injected only into isolated TestClient stores."""
import pytest
from fastapi.testclient import TestClient
from app import main
from app.storage import Store
from app.normalization import normalize_actuals,normalize_forecasts

@pytest.fixture
def client(tmp_path,monkeypatch):
    s=Store(tmp_path)
    monkeypatch.setattr(main,'store',s)
    return TestClient(main.app)

def test_unavailable_dashboard(client):
    assert client.get('/api/health').json()['status']=='ok'
    data=client.get('/api/overview').json()
    assert data['metadata']['status']=='unavailable'
    assert len(data['intervals'])==48 and data['metrics']['sampleSize']==0
    assert data['metrics']['mae'] is None
    assert client.get('/api/accuracy').status_code==200
    assert client.get('/api/forecasts').json()['total']==48
    assert client.get('/api/forecast-history').json()['items']==[]

@pytest.mark.parametrize('query',['delivery_date=2026-02-01','delivery_date=2025-12-31','decision_time=2025-12-31T09:00:00','mode=wrong','cutoff=25:00'])
def test_validation(client,query):
    assert client.get('/api/overview?'+query).status_code==422

def test_api_parameter_ranges(client):
    assert client.get('/api/forecasts?page=0').status_code==422
    assert client.get('/api/forecast-history?settlement_period=49').status_code==422
    assert client.get('/api/accuracy?start_date=2026-01-31&end_date=2026-01-01').status_code==422
    assert client.get('/api/accuracy?decision_time=2026-01-01T09:00:00Z').status_code==422
    assert client.post('/api/scenarios/residual-procurement',json={'demand_mw':-1}).status_code==422

def test_refresh_protected(client,monkeypatch):
    monkeypatch.setattr(main,'ADMIN_TOKEN','')
    assert client.post('/api/admin/refresh').status_code==503
    monkeypatch.setattr(main,'ADMIN_TOKEN','test-only-secret')
    assert client.post('/api/admin/refresh').status_code==403

def test_representative_dashboard_and_scenario(client):
    main.store.actuals,_=normalize_actuals([{'fuelType':'WIND','startTime':'2026-01-15T00:00:00Z','generation':100}])
    main.store.forecasts,_=normalize_forecasts([{'startTime':'2026-01-15T00:00:00Z','publishTime':'2026-01-14T08:00:00Z','generation':120}])
    response=client.get('/api/overview').json()
    assert response['metrics']['mae']==20
    assert response['intervals'][0]['publishTime']=='2026-01-14T08:00:00.000Z'
    ledger=client.get('/api/forecasts?sort=absoluteError&descending=true').json()
    assert ledger['items'][0]['error']==20
    response=client.post('/api/scenarios/residual-procurement',json={'demand_mw':200,'delivery_date':'2026-01-15','settlement_period':1})
    assert response.status_code==200
    assert response.json()['estimatedResidualMW']==80
    assert response.json()['actualResidualMW']==100
    assert client.post('/api/scenarios/residual-procurement',json={'demand_mw':200,'delivery_date':'2026-01-15','settlement_period':2}).status_code==409


def test_local_refresh_disabled_by_default(client,monkeypatch):
    monkeypatch.setattr(main,'ENABLE_LOCAL_REFRESH',False)
    assert client.post('/api/local/refresh').status_code==403


def test_local_refresh_origin_and_content_type(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'ENABLE_LOCAL_REFRESH',True)
    monkeypatch.setattr(main,'store',Store(tmp_path))
    local=TestClient(main.app,base_url='http://localhost',client=('127.0.0.1',12345))
    assert local.post('/api/local/refresh',headers={'Origin':'https://untrusted.example','Content-Type':'application/json'}).status_code==403
    assert local.post('/api/local/refresh',headers={'Origin':'http://localhost:5173'}).status_code==415
    remote=TestClient(main.app,base_url='http://localhost',client=('203.0.113.1',12345))
    assert remote.post('/api/local/refresh',headers={'Origin':'http://localhost:5173','Content-Type':'application/json'}).status_code==403


def test_local_refresh_starts_once_and_reports_completion(tmp_path,monkeypatch):
    import asyncio
    monkeypatch.setattr(main,'ENABLE_LOCAL_REFRESH',True)
    monkeypatch.setattr(main,'store',Store(tmp_path))
    async def refreshed():
        main.store.refresh_state={'state':'complete','message':'Loaded synthetic test snapshot'}
    monkeypatch.setattr(main.store,'refresh',refreshed)
    with TestClient(main.app,base_url='http://localhost',client=('127.0.0.1',12345)) as local:
        headers={'Origin':'http://localhost:5173','Content-Type':'application/json'}
        response=local.post('/api/local/refresh',headers=headers,json={})
        assert response.status_code==202
        assert local.get('/api/metadata').json()['refresh']['state']=='complete'
        assert local.post('/api/local/refresh',headers=headers,json={}).status_code==429
