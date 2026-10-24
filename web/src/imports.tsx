import React,{useEffect,useRef,useState} from 'react';
import {ImportSpotify} from './generated/Imports';
import {UI} from './components/ui';
const h=React.createElement;
const active=(job:any)=>['queued','running'].includes(job?.status);
export function SpotifyImports({api,refresh,onOpen}:any){
 const [link,setLink]=useState(''),[download,setDownload]=useState(true),[job,setJob]=useState<any>(null),[history,setHistory]=useState<any[]>([]),[working,setWorking]=useState(false),[error,setError]=useState(''),[connection,setConnection]=useState('');
 const serial=useRef(0),mounted=useRef(true),locked=useRef(false),selected=useRef<any>(null),known=useRef<any[]>([]);
 selected.current=job;known.current=history;
 const remember=(value:any)=>{selected.current=value;setJob(value);setHistory(v=>[value,...v.filter(j=>j.id!==value.id)]);if(value.mode)setDownload(value.mode==='download')};
 useEffect(()=>{
  mounted.current=true;let stopped=false,timer:any,initial=true;
  const poll=async()=>{if(locked.current){timer=setTimeout(poll,2000);return}const generation=serial.current;try{
   const data=await api('/imports');if(stopped||generation!==serial.current)return;
   const changed=data.jobs.some((value:any)=>!active(value)&&known.current.some(old=>old.id===value.id&&active(old)));
   known.current=data.jobs;setHistory(data.jobs);
   const value=initial&&!selected.current?(data.jobs.find(active)||data.jobs[0]||null):data.jobs.find((value:any)=>value.id===selected.current?.id);
   if(value){selected.current=value;setJob(value);if(initial&&value.mode)setDownload(value.mode==='download')}
   initial=false;setConnection('');if(changed)await refresh();
  }catch(e:any){if(!stopped)setConnection(initial?e.message:'Connection interrupted. Your queue is saved on the server. Reconnecting…')}
  finally{if(!stopped)timer=setTimeout(poll,2000)}};
  void poll();return()=>{stopped=true;mounted.current=false;serial.current++;clearTimeout(timer)}
 },[]);
 const mutate=async(action:string)=>{
  if(locked.current)return;locked.current=true;setWorking(true);setError('');setConnection('');const generation=++serial.current;
  try{
   if(action==='preview'){const value=await api('/imports/preview','POST',{url:link});if(mounted.current&&generation===serial.current)remember(value)}
   else if(action==='start'||action==='resume'){const value=await api('/imports/'+job.id+'/start','POST',{download,retry:action==='resume'});if(mounted.current&&generation===serial.current)remember(value)}
   else if(action==='refresh-artwork'){const value=await api('/imports/'+job.id+'/artwork','POST',{});if(mounted.current&&generation===serial.current){remember(value);await refresh()}}
   else if(action==='cancel'){const value=await api('/imports/'+job.id+'/cancel','POST',{});if(mounted.current&&generation===serial.current)remember(value)}
  }catch(e:any){if(mounted.current){setError(e.message);if(action==='start'||action==='resume'){try{remember(await api('/imports/'+job.id))}catch{setConnection('The request may have been received. Reopen Imports to check its status before trying again.')}}}}
  finally{locked.current=false;if(mounted.current)setWorking(false)}
 };
 const choose=(id:string)=>{serial.current++;remember(history.find(j=>j.id===id));setError('');setConnection('')};
 const onAction=(action:string)=>{if(action==='open-playlist'){onOpen(job.playlist);return}void mutate(action)};
 const running=active(job),canResume=job&&['partial','cancelled','interrupted','failed'].includes(job.status);
 const queued=history.filter(active).length;
 const label=(j:any)=>j.status==='queued'?'Queued · '+j.queuePosition:j.status;
 const data={job,queueMessage:queued?`${queued} playlist${queued===1?'':'s'} in your queue. Imports continue automatically while you browse or close this page.`:'',hasQueue:queued>0,history:history.map(j=>({id:j.id,label:j.name+' · '+label(j)})),hasHistory:history.length>0,tracks:job?.tracks||[],count:job?.tracks.length||0,available:job?.available||0,finished:job?.finished||0,statusLabel:job?label(job):'',error,connection,working,downloadMissing:download,previewLabel:working?'Please wait…':'Preview playlist',canStart:job?.status==='preview',startLabel:download?'Queue and download':'Queue from my library',cancelLabel:job?.status==='queued'?'Remove from queue':'Stop import',queuePosition:job?.status==='queued'?`Queue position ${job.queuePosition}. Starts automatically after earlier playlists.`:'',isQueued:job?.status==='queued',active:running,canResume,hasPlaylist:!!job?.playlist,canRefreshArtwork:!!job?.playlist&&!running};
 return h(UI.Provider,{value:{importLink:link,setImportLink:setLink,setImportDownload:setDownload,onValueAction:choose}},h(ImportSpotify,{data,onAction}));
}
