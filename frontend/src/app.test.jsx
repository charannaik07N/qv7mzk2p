import React from 'react';
import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,waitFor,fireEvent,cleanup} from '@testing-library/react';
import {App} from './main';
// Synthetic availability response only; no generation observations are provided.
const response={metrics:{sampleSize:0,expectedIntervals:48,coverage:0,missingForecast:48},intervals:[],metadata:{status:'unavailable',localRefreshEnabled:true,refresh:{state:'idle'},lastSuccessfulRefresh:null},decisionTime:'2026-01-14T09:20:00Z'};
afterEach(()=>{cleanup();vi.unstubAllGlobals();window.location.hash='';});
it('lets a local user request real source loading and shows progress',async()=>{
 const fetch=vi.fn(async(url,options)=>({ok:true,json:async()=>url.endsWith('/local/refresh')?{state:'loading'}:response}));
 vi.stubGlobal('fetch',fetch);
 render(<App/>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Load Elexon data'})).toBeTruthy());
 fireEvent.click(screen.getByRole('button',{name:'Load Elexon data'}));
 await waitFor(()=>expect(screen.getByText('Loading January wind data…')).toBeTruthy());
 expect(fetch.mock.calls.some(([url,opts])=>url.endsWith('/local/refresh')&&opts.method==='POST')).toBe(true);
});
it('explains a load failure without inserting observations',async()=>{
 vi.stubGlobal('fetch',vi.fn(async url=>({ok:!url.endsWith('/local/refresh'),json:async()=>url.endsWith('/local/refresh')?{detail:'Elexon is unreachable'}:response})));
 render(<App/>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Load Elexon data'})).toBeTruthy());
 fireEvent.click(screen.getByRole('button',{name:'Load Elexon data'}));
 await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Elexon is unreachable'));
});
