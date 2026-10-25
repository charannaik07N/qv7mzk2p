// All observations are SYNTHETIC test data; never included in application snapshots.
import React from 'react';
import {describe,it,expect,vi,afterEach} from 'vitest';
import {render,screen,cleanup,waitFor} from '@testing-library/react';
import {Empty,LoadState,Kpis} from './components';
import {useApi} from './api';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('data availability states',()=>{
 it('announces loading accessibly',()=>{render(<LoadState loading/>);expect(screen.getByRole('status').getAttribute('aria-label')).toBe('Loading analysis');});
 it('shows an actionable error',()=>{render(<LoadState error="Offline" retry={()=>{}}/>);expect(screen.getByRole('alert').textContent).toContain('Offline');expect(screen.getByRole('button').textContent).toContain('Retry');});
 it('never invents generation in the empty state',()=>{render(<Empty/>);expect(screen.getByText(/No observations/)).toBeTruthy();expect(screen.getByText(/Missing values are never/)).toBeTruthy();});
 it('uses supplied backend KPI values',()=>{render(<Kpis metrics={{averageForecast:120,averageActual:100,mae:20,rmse:20,bias:20,coverage:100,sampleSize:1,expectedIntervals:1}}/>);expect(screen.getByText('Forecast average')).toBeTruthy();expect(screen.getByText('120')).toBeTruthy();});
});
function Probe(){const state=useApi('/overview');return <>{state.loading?<LoadState loading/>:state.error?<LoadState error={state.error} retry={state.retry}/>:<span>matched: {state.data.metrics.sampleSize}</span>}</>;}
it('fetches a representative overview through the data hook',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({metrics:{sampleSize:48}})}));render(<Probe/>);await waitFor(()=>expect(screen.getByText('matched: 48')).toBeTruthy());});
it('surfaces HTTP failure without substituting data',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:'Source unavailable'})}));render(<Probe/>);await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Source unavailable'));});
