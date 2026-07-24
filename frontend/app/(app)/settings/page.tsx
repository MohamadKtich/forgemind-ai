"use client";

import {API} from "@/lib/api";
import {usePreferences} from "@/components/preferences-provider";
import {Cloud, Database, HardDrive, KeyRound, Languages, MonitorCog, Moon, Server, ShieldCheck, Sun} from "lucide-react";
import {PageHeader, RiskBadge} from "@/components/ui";

export default function SettingsPage(){
  const {locale,theme,setLocale,setTheme}=usePreferences();
  const items=[
    [HardDrive,"Application mode","Local-first installation","Frontend, backend, database, model registry, uploaded images, and generated reports run on this computer."],
    [Database,"Database","SQLite with foreign keys and WAL","All operational records persist locally in backend/forgemind.db. PostgreSQL or Supabase can replace it later."],
    [Server,"Operations API",API,"FastAPI, OpenAPI documentation, machine workflows, inference, reports, assistant, administration, and device gateway."],
    [KeyRound,"Authentication","Signed local bearer tokens","PBKDF2 password hashing, role authorization, active accounts, audit activity, and 12-hour sessions."],
    [ShieldCheck,"Device ingestion","X-Device-Key protected","Hardware readings require the local device API key configured in backend/.env."],
    [Cloud,"Cloud readiness","Deferred by design","Hosted storage, managed auth, production domain, TLS, email recovery, and managed database are the next deployment layer."],
  ] as const;

  return <>
    <PageHeader eyebrow="System configuration" title="Local installation details" subtitle="Choose the display language and theme, then review what is running locally and what is intentionally deferred until cloud deployment."/>

    <section className="card" style={{marginBottom:15}}>
      <div className="panel-head"><div><h2 className="panel-title">Display preferences</h2><p className="panel-subtitle">The interface remembers these choices on this browser. Arabic enables a full right-to-left layout.</p></div></div>
      <div className="panel-body display-preferences-grid">
        <div>
          <div className="preference-label"><Languages size={17}/><span>Interface language</span></div>
          <div className="segmented-control" role="group" aria-label="Interface language">
            <button type="button" data-active={locale==="en"} onClick={()=>setLocale("en")}>English</button>
            <button type="button" data-active={locale==="ar"} onClick={()=>setLocale("ar")}>العربية</button>
          </div>
        </div>
        <div>
          <div className="preference-label"><MonitorCog size={17}/><span>Color theme</span></div>
          <div className="segmented-control" role="group" aria-label="Color theme">
            <button type="button" data-active={theme==="light"} onClick={()=>setTheme("light")}><Sun size={15}/>Light</button>
            <button type="button" data-active={theme==="dark"} onClick={()=>setTheme("dark")}><Moon size={15}/>Dark</button>
            <button type="button" data-active={theme==="system"} onClick={()=>setTheme("system")}><MonitorCog size={15}/>System</button>
          </div>
        </div>
      </div>
    </section>

    <div className="grid-auto">{items.map(([Icon,title,value,copy]:any)=><section className="card" style={{padding:20}} key={title}><div className="feature-icon"><Icon/></div><h2 style={{fontSize:15,margin:"17px 0 5px"}}>{title}</h2><RiskBadge risk="informational"/><p style={{fontSize:12,margin:"10px 0 4px",wordBreak:"break-word"}}>{value}</p><p className="muted" style={{fontSize:11,lineHeight:1.65,margin:0}}>{copy}</p></section>)}</div>
    <section className="card" style={{marginTop:15}}><div className="panel-head"><div><h2 className="panel-title">Important production transition</h2><p className="panel-subtitle">The local edition is complete for application development and controlled industrial evaluation.</p></div></div><div className="panel-body"><p className="muted" style={{fontSize:12,lineHeight:1.75}}>Before connecting real machines or exposing the system publicly, replace the local secret and device key, use HTTPS, move identity to a managed provider, migrate SQLite to PostgreSQL, configure object storage, validate every model and threshold on the target factory data, add an industrial protocol gateway, and conduct safety and security reviews.</p></div></section>
  </>;
}
