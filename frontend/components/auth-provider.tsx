"use client";
import {createContext,useContext,useEffect,useMemo,useState} from "react";
import {usePathname,useRouter} from "next/navigation";
import {api,AuthUser,clearAuth} from "@/lib/api";

type AuthContextValue={user:AuthUser|null;loading:boolean;refresh:()=>Promise<void>;logout:()=>void};
const AuthContext=createContext<AuthContextValue>({user:null,loading:true,refresh:async()=>{},logout:()=>{}});

export function AuthProvider({children}:{children:React.ReactNode}){
  const [user,setUser]=useState<AuthUser|null>(null);const [loading,setLoading]=useState(true);
  const router=useRouter();const pathname=usePathname();
  async function refresh(){
    try{setUser(await api<AuthUser>("/api/auth/me"))}
    catch{setUser(null);if(pathname!=="/login"&&pathname!=="/signup")router.replace(`/login?next=${encodeURIComponent(pathname)}`)}
    finally{setLoading(false)}
  }
  useEffect(()=>{refresh()},[]);
  function logout(){clearAuth();setUser(null);router.replace("/login")}
  const value=useMemo(()=>({user,loading,refresh,logout}),[user,loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth(){return useContext(AuthContext)}
