import { createSpeedTracker } from "../utils/uploadSpeed";
import { apiError } from "./apiErrors";

export type ArchiveKind = "save" | "world_save";

export interface ArchiveVersion { id: string; filename: string; size: number; uploaded_at: number; url: string; }
export interface GameArchiveData { id: string; name: string; kind: ArchiveKind; created_at: number; updated_at: number; versions: ArchiveVersion[]; }

function uploadWithProgress(url:string,method:"POST"|"PATCH",form:FormData|null,jsonBody:unknown|null,onProgress?:(fraction:number,speedLabel?:string)=>void):Promise<GameArchiveData>{
  const trackSpeed=createSpeedTracker();
  return new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();xhr.open(method,url);xhr.withCredentials=true;
    if(form){xhr.upload.onprogress=e=>{if(e.lengthComputable&&onProgress)onProgress(e.loaded/e.total,trackSpeed(e.loaded,e.total));};}
    else xhr.setRequestHeader("Content-Type","application/json");
    xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300){try{resolve(JSON.parse(xhr.responseText));}catch{reject(new Error("Request succeeded but the response could not be parsed."));}}else reject(new Error(`Request failed: ${xhr.status}`));};
    xhr.onerror=()=>reject(new Error("Request failed: network error."));xhr.send(form??JSON.stringify(jsonBody));
  });
}

export async function fetchArchives(gameId:string,kind:ArchiveKind):Promise<GameArchiveData[]>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return[];
  const response=await fetch(`/api/game/${gameId}/archives/${kind}`,{credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to fetch archives");
  return await response.json();
}
export async function createArchive(gameId:string,kind:ArchiveKind,name:string,file:File,onProgress?:(fraction:number,speedLabel?:string)=>void):Promise<GameArchiveData>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return{id:crypto.randomUUID(),name,kind,created_at:0,updated_at:0,versions:[]};
  const form=new FormData();form.append("name",name);form.append("file",file);return uploadWithProgress(`/api/game/${gameId}/archives/${kind}`,"POST",form,null,onProgress);
}
export async function addArchiveVersion(gameId:string,archiveId:string,file:File,onProgress?:(fraction:number,speedLabel?:string)=>void):Promise<GameArchiveData>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return{id:archiveId,name:"",kind:"save",created_at:0,updated_at:0,versions:[]};
  const form=new FormData();form.append("file",file);return uploadWithProgress(`/api/game/${gameId}/archives/${archiveId}/versions`,"POST",form,null,onProgress);
}
export async function renameArchive(gameId:string,archiveId:string,name:string):Promise<GameArchiveData>{
  const response=await fetch(`/api/game/${gameId}/archives/${archiveId}`,{method:"PATCH",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({name})});
  if(!response.ok)throw await apiError(response,"Failed to rename archive");return await response.json();
}
export async function deleteArchive(gameId:string,archiveId:string):Promise<void>{
  const response=await fetch(`/api/game/${gameId}/archives/${archiveId}`,{method:"DELETE",credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to delete archive");
}
export interface TrashedArchive extends GameArchiveData{deleted_at:number;purge_at:number}
export async function fetchArchiveTrash(gameId:string,kind:ArchiveKind):Promise<TrashedArchive[]>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return[];const response=await fetch(`/api/game/${gameId}/archives/${kind}/trash`,{credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to fetch archive trash");return await response.json();
}
export async function restoreArchive(gameId:string,archiveId:string):Promise<GameArchiveData>{
  const response=await fetch(`/api/game/${gameId}/archives/${archiveId}/restore`,{method:"POST",credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to restore archive");return await response.json();
}
export async function restoreArchiveVersion(gameId:string,archiveId:string,versionId:string):Promise<GameArchiveData>{
  const response=await fetch(`/api/game/${gameId}/archives/${archiveId}/versions/${versionId}/restore`,{method:"POST",credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to restore archive version");return await response.json();
}
export async function deleteArchiveVersion(gameId:string,archiveId:string,versionId:string):Promise<GameArchiveData>{
  const response=await fetch(`/api/game/${gameId}/archives/${archiveId}/versions/${versionId}`,{method:"DELETE",credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to delete archive version");return await response.json();
}
export type WorldMapStatus="idle"|"rendering"|"done"|"error";
export interface WorldMapEntry extends GameArchiveData{status:WorldMapStatus;detail:string|null;updated_at_status:number|null;has_thumbnail:boolean}
export async function fetchWorldMaps(gameId:string):Promise<WorldMapEntry[]>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return[];const response=await fetch(`/api/game/${gameId}/world-map/worlds`,{credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to fetch worlds");return await response.json();
}
export async function renderWorldMap(gameId:string,archiveId:string):Promise<void>{
  if(import.meta.env.VITE_USE_MOCK_DATA==="true")return;const response=await fetch(`/api/game/${gameId}/world-map/${archiveId}/render`,{method:"POST",credentials:"include"});
  if(!response.ok)throw await apiError(response,"Failed to start map render");
}
export function worldMapViewUrl(gameId:string,archiveId:string):string{return `/api/game/${gameId}/world-map/${archiveId}/view/`}
export function worldMapThumbnailUrl(gameId:string,archiveId:string):string{return `/api/game/${gameId}/world-map/${archiveId}/thumbnail`}
