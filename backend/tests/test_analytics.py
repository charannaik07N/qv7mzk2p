"""All observations in this file are SYNTHETIC unit-test fixtures."""
import math
import pandas as pd
import pytest
from app.normalization import normalize_actuals, normalize_forecasts, stamp
from app.analytics import evaluate, metrics, residual, settlement_grid, decision_for

T='2026-01-01T00:00:00Z'
P='2025-12-31T08:00:00Z'

def actual(value=100, **kw):
    return {'fuelType':'WIND','startTime':T,'generation':value,**kw}

def forecast(value=120, **kw):
    return {'startTime':T,'publishTime':P,'generation':value,**kw}

def test_source_schemas_and_wind_filter():
    a,q=normalize_actuals([actual(),actual(500,fuelType='GAS')])
    f,_=normalize_forecasts([forecast()])
    assert len(a)==len(f)==1
    assert a.generation.iloc[0]==100
    assert f.publishTime.iloc[0]==stamp(P)
    with pytest.raises(ValueError): normalize_forecasts({'data':[]})

@pytest.mark.parametrize('value',[None,float('nan'),float('inf'),-1,True,'bad'])
def test_invalid_generation(value):
    a,q=normalize_actuals([actual(value)])
    assert len(a)==0 and q['invalid']==1

def test_cutoff_no_lookahead_and_exact_equality():
    a,_=normalize_actuals([actual()])
    f,_=normalize_forecasts([forecast(110),forecast(115,publishTime='2025-12-31T09:20:00Z'),forecast(999,publishTime='2025-12-31T09:21:00Z')])
    frame=evaluate(a,f,'2026-01-01')
    assert frame.iloc[0].forecast==115
    assert frame.iloc[0].forecastAgeHours==0
    assert frame.iloc[0].publishTime<=frame.iloc[0].decisionTime
    assert frame.iloc[0].error==15
    assert metrics(frame)['sampleSize']==1
    assert evaluate(a,f,'2026-01-01',mode='retrospective').iloc[0].forecast==999

def test_no_eligible_forecast_and_missing_join():
    a,_=normalize_actuals([actual()])
    f,_=normalize_forecasts([forecast(publishTime='2026-01-01T00:01:00Z')])
    m=metrics(evaluate(a,f,'2026-01-01'))
    assert m['missingForecast']==48 and m['missingActual']==47
    assert m['sampleSize']==0 and m['mae'] is None
    assert m['coverage']==0

def test_dedup_and_conflicts():
    f,q=normalize_forecasts([forecast(100),forecast(100),forecast(200)])
    assert f.empty and q['duplicates']==1 and q['conflicting_keys']==1
    a,q=normalize_actuals([actual(80,publishTime=P),actual(100,publishTime='2026-01-02T00:00:00Z')])
    assert len(a)==1 and a.generation.iloc[0]==100

def test_hand_calculated_metrics_zero_actual():
    a,_=normalize_actuals([actual(100),actual(0,startTime='2026-01-01T00:30:00Z'),actual(50,startTime='2026-01-01T01:00:00Z')])
    f,_=normalize_forecasts([forecast(120),forecast(10,startTime='2026-01-01T00:30:00Z'),forecast(20,startTime='2026-01-01T01:00:00Z')])
    frame=evaluate(a,f,'2026-01-01'); m=metrics(frame)
    assert m['mae']==20
    assert m['rmse']==pytest.approx(math.sqrt(1400/3))
    assert m['bias']==0
    assert m['wape']==40 and m['wapeDenominatorMW']==150
    assert m['sampleSize']==3 and m['percentageSampleSize']==2
    assert m['coverage']==6.25
    assert pd.isna(frame.iloc[1].percentageError)
    assert m['maxAbsoluteError']==30
    assert m['averageActual']==50 and m['averageForecast']==50

def test_zero_wape_denominator():
    a,_=normalize_actuals([actual(0)])
    f,_=normalize_forecasts([forecast(1)])
    assert metrics(evaluate(a,f,'2026-01-01'))['wape'] is None

def test_timezones_and_dst_grids():
    assert len(settlement_grid('2026-01-01'))==48
    assert len(settlement_grid('2026-03-29'))==46
    assert len(settlement_grid('2026-10-25'))==50
    assert stamp('2026-07-01T01:00:00+01:00')==stamp('2026-07-01T00:00:00Z')
    assert decision_for('2026-07-02').hour==8
    with pytest.raises(ValueError): stamp('2026-01-01T00:00:00')

def test_residual_saturation_and_separate_demand():
    assert residual(100,120,90)['estimatedResidualMW']==0
    assert residual(100,120,90)['actualResidualMW']==10
    assert residual(100,120,90)['residualErrorMW']==-10
    assert residual(200,100,120,250)['actualResidualMW']==130
    assert residual(100,20)['actualResidualMW'] is None
