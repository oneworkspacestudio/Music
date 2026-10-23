export type Track={hash:string;title:string;album:string;albumhash:string;artists:string[];duration:number;image:string;color:string;year:string;explicit:boolean};
export type Collection={owner:number;ownerName:string;kind:string;id:string;name:string;description:string;count:number;duration:number;images:string[];editable:boolean;shared:boolean;tracks?:Track[]};
export type Person={id:number;name:string};
export const key=(c:Collection)=>[c.owner,c.kind,c.id].join('/');
export const duration=(n:number)=>Number.isFinite(n)?Math.floor(n/60)+':'+String(Math.floor(n%60)).padStart(2,'0'):'0:00';
