import React,{useEffect,useRef,useState} from 'react';
import {ImportSpotify} from './generated/Imports';
import {UI} from './components/ui';
const h=React.createElement;
const active=(job:any)=>['queued','running'].includes(job?.status);
export function SpotifyImports({api,refresh,onOpen}:any){
 const [link,setLink]=useState(''),[download,setDownload]=useState(true),[job,setJob]=useState<any>(null),[history,setHistory]=useState<any[]>([]),[working,setWorking]=useState(false),[error,setError]=useState(''),[connection,setConnection]=useState('');
 const serial=useRef(0),mounted=useRef(true),locked=useRef(false);
 const remember=(value:any)=>{setJob(value);setHistory(v=>[value,...v.filter(j=>j.id!==value.id)].slice(0,20))};
 useEffect(()=>{mounted.current=true;api('/imports').then((data:any)=>{if(!mounted.current)return;setHistory(data.jobs);setJob(data.jobs.find(active)||data.jobs[0]||null)}).catch((e:any)=>{if(mounted.current)setError(e.message)});return()=>{mounted.current=false;serial.current++}},[]);
 useEffect(()=>{if(!job||!active(job))return;let stopped=false,timer:any;const generation=serial.current;const poll=async()=>{try{const value=await api('/imports/'+job.id);if(stopped||generation!==serial.current)return;remember(value);setConnection('');if(!active(value))await refresh()}catch{if(!stopped)setConnection('Connection interrupted. Your import continues on the server. Reconnecting…')}finally{if(!stopped)timer=setTimeout(poll,2000)}};timer=setTimeout(poll,1200);return()=>{stopped=true;clearTimeout(timer)}},[job?.id,job?.status]);
 const mutate=async(action:string)=>{
  if(locked.current)return;locked.current=true;setWorking(true);setError('');setConnection('');const generation=action==='cancel'?serial.current:++serial.current;
  try{
   if(action==='preview'){const value=await api('/imports/preview','POST',{url:link});if(mounted.current&&generation===serial.current)remember(value)}
   else if(action==='start'||action==='resume'){const value=await api('/imports/'+job.id+'/start','POST',{download,retry:action==='resume'});if(mounted.current&&generation===serial.current)remember(value)}
   else if(action==='refresh-artwork'){const value=await api('/imports/'+job.id+'/artwork','POST',{});if(mounted.current&&generation===serial.current){remember(value);await refresh()}}
   else if(action==='cancel'){await api('/imports/'+job.id+'/cancel','POST',{});if(mounted.current)setConnection('Stopping the current download. Added songs will be kept.')}
  }catch(e:any){if(mounted.current){setError(e.message);if(action==='start'||action==='resume'){try{remember(await api('/imports/'+job.id))}catch{setConnection('The request may have been received. Reopen Imports to check its status before trying again.')}}}}
  finally{locked.current=false;if(mounted.current)setWorking(false)}
 };
 const choose=(id:string)=>{serial.current++;setJob(history.find(j=>j.id===id));setError('');setConnection('')};
 const onAction=(action:string)=>{if(action==='open-playlist'){onOpen(job.playlist);return}void mutate(action)};
 const running=active(job),canResume=job&&['partial','cancelled','interrupted','failed'].includes(job.status);
 const data={job,history:history.map(j=>({id:j.id,label:j.name+' · '+j.status})),hasHistory:history.length>0,tracks:job?.tracks||[],count:job?.tracks.length||0,available:job?.available||0,finished:job?.finished||0,statusLabel:job?.status||'',error,connection,working,downloadMissing:download,previewLabel:working?'Please wait…':'Preview playlist',canStart:job?.status==='preview',startLabel:download?'Import and download':'Import from my library',active:running,canResume,hasPlaylist:!!job?.playlist,canRefreshArtwork:!!job?.playlist&&!running};
 return h(UI.Provider,{value:{importLink:link,setImportLink:setLink,setImportDownload:setDownload,onValueAction:choose}},h(ImportSpotify,{data,onAction}));
}
