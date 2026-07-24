"use client";
import {createContext,useContext,useState} from "react";
import {CheckCircle2,TriangleAlert,X} from "lucide-react";
type Toast={id:number;text:string;kind:"success"|"error"};
const ToastContext=createContext({show:(text:string,kind:"success"|"error"="success")=>{}});
export function ToastProvider({children}:{children:React.ReactNode}){const [items,setItems]=useState<Toast[]>([]);function show(text:string,kind:"success"|"error"="success"){const id=Date.now()+Math.random();setItems(v=>[...v,{id,text,kind}]);setTimeout(()=>setItems(v=>v.filter(x=>x.id!==id)),3600)}return <ToastContext.Provider value={{show}}>{children}<div className="toast-stack">{items.map(t=><div key={t.id} className={`toast ${t.kind}`}>{t.kind==="success"?<CheckCircle2 size={18}/>:<TriangleAlert size={18}/>}<span>{t.text}</span><button onClick={()=>setItems(v=>v.filter(x=>x.id!==t.id))}><X size={16}/></button></div>)}</div></ToastContext.Provider>}
export function useToast(){return useContext(ToastContext)}
