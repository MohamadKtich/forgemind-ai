"use client";
import Link from "next/link";
import {useState} from "react";
import {CheckCircle2,KeyRound} from "lucide-react";
import {api} from "@/lib/api";

export default function ForgotPassword(){
  const [email,setEmail]=useState("");
  const [recoveryKey,setRecoveryKey]=useState("");
  const [password,setPassword]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [done,setDone]=useState(false);
  async function submit(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError("");
    try{await api("/api/auth/recover-local",{method:"POST",body:JSON.stringify({email,recovery_key:recoveryKey,new_password:password})});setDone(true)}
    catch(e:any){setError(e.message)}finally{setBusy(false)}
  }
  return <main className="auth-page"><section className="auth-art"><Link href="/" className="public-brand"><img src="/brand/forgemind-mark.svg" alt="ForgeMind AI"/><span>ForgeMind AI</span></Link><div className="auth-art-content"><h1>Recover access without deleting factory data.</h1><p>The local recovery key is controlled by the installation owner in the backend environment file. Cloud email recovery can replace this workflow later.</p><img className="hero-mini" src="/brand/machine-network.svg" alt="Secure industrial network"/></div></section><section className="auth-form-wrap"><div className="auth-card"><div className="feature-icon" style={{marginBottom:18}}>{done?<CheckCircle2/>:<KeyRound/>}</div><h1>{done?"Password updated":"Recover local account"}</h1>{done?<><p>Your password was changed successfully. The database, reports, inspections, and machine history remain untouched.</p><Link className="btn btn-primary" href="/login">Return to sign in</Link></>:<><p>Enter the account email, the installation recovery key, and a new password.</p><form className="auth-form" onSubmit={submit}><label className="field"><span>Email address</span><input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label><label className="field"><span>Local recovery key</span><input className="input" type="password" value={recoveryKey} onChange={e=>setRecoveryKey(e.target.value)} required minLength={8}/><small>Configured as LOCAL_RECOVERY_KEY in backend/.env.</small></label><label className="field"><span>New password</span><input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={8}/></label>{error&&<div className="error-box">{error}</div>}<button className="btn btn-primary" disabled={busy}>{busy?"Updating…":"Update password"}</button></form><div className="auth-links"><Link href="/login">Return to sign in</Link><Link href="/docs">Open installation guide</Link></div></>}</div></section></main>
}
