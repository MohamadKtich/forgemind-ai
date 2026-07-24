export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export type AuthUser = {id:number;full_name:string;email:string;role:string;active:boolean;created_at:string;last_login_at?:string|null};

export function getToken():string|null{
  if(typeof window === "undefined") return null;
  return localStorage.getItem("fm_token");
}

export function persistAuth(token:string,user:AuthUser){
  localStorage.setItem("fm_token",token);
  localStorage.setItem("fm_user",JSON.stringify(user));
  document.cookie=`fm_session=1; path=/; max-age=${60*60*12}; SameSite=Lax`;
}

export function clearAuth(){
  if(typeof window !== "undefined"){
    localStorage.removeItem("fm_token");
    localStorage.removeItem("fm_user");
    document.cookie="fm_session=; Max-Age=0; path=/";
  }
}

export async function api<T>(path:string,init?:RequestInit):Promise<T>{
  const token=getToken();
  const headers:Record<string,string>={};
  if(!(init?.body instanceof FormData)) headers["Content-Type"]="application/json";
  if(token) headers.Authorization=`Bearer ${token}`;
  Object.assign(headers,init?.headers||{});
  const res=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});
  if(!res.ok){
    let message=`Request failed (${res.status})`;
    try{const payload=await res.json();message=payload.detail||message}catch{}
    if(res.status===401 && typeof window!=="undefined") clearAuth();
    throw new Error(message);
  }
  if(res.status===204) return undefined as T;
  const type=res.headers.get("content-type")||"";
  if(!type.includes("application/json")) return await res.text() as T;
  return res.json();
}

export async function downloadAuthenticated(path:string,filename?:string){
  const token=getToken();
  const res=await fetch(`${API}${path}`,{headers:token?{Authorization:`Bearer ${token}`}:{}});
  if(!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob=await res.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=filename||path.split("/").pop()||"download";a.click();
  URL.revokeObjectURL(url);
}

export function apiAsset(path?:string|null){return path?`${API}${path}`:""}
