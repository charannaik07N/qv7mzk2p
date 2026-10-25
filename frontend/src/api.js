import {useEffect,useState} from 'react';
export const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/,'');
export async function request(path, options={}) {
  const response=await fetch(`${API}/api${path}`,options);
  let body;try{body=await response.json();}catch{throw new Error('The API returned an unreadable response. Check the configured backend URL.');}
  if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:'Invalid request. Check the selected inputs.');
  return body;
}
export function useApi(path){
  const [state,setState]=useState({data:null,loading:true,error:null});
  const [revision,reload]=useState(0);
  useEffect(()=>{const controller=new AbortController();setState({data:null,loading:true,error:null});
    request(path,{signal:controller.signal}).then(data=>setState({data,loading:false,error:null})).catch(e=>{if(e.name!=='AbortError')setState({data:null,loading:false,error:e.message});});
    return()=>controller.abort();
  },[path,revision]);
  return {...state,retry:()=>reload(v=>v+1)};
}
