import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, LockKeyhole, Mail } from "lucide-react";
import { AuthBackground } from "../../components/AuthBackground";
import { useAuth } from "../../context/useAuth";
import { useToast } from "../../context/useToast";

export function LoginPage() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { signIn } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const submit = async (event) => { event.preventDefault(); setError(""); setBusy(true); try { const user = await signIn(form); const destination = location.state?.from?.pathname || (String(user.role).toUpperCase() === "ADMIN" ? "/admin" : "/app"); navigate(destination, { replace: true }); } catch (caught) { const message = caught?.message || "We could not sign you in."; setError(message); toast.push(message, "error"); } finally { setBusy(false); } };
  return <AuthBackground><section className="border border-carbon-950 bg-canvas-50 shadow-paper"><div className="border-b border-carbon-950 px-6 py-7 sm:px-8"><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-vermilion-600">Return to your workspace</p><h2 className="mt-2 font-display text-4xl tracking-tight">Sign in</h2><p className="mt-2 text-sm leading-6 text-carbon-500">Use your organization account to continue.</p></div><form onSubmit={submit} className="space-y-5 px-6 py-7 sm:px-8"><Field id="login-email" label="Work email" type="email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} icon={Mail} autoComplete="email" required /><Field id="login-password" label="Password" type="password" value={form.password} onChange={(value) => setForm({ ...form, password: value })} icon={LockKeyhole} autoComplete="current-password" required /><div aria-live="polite">{error && <p role="alert" className="border-l-4 border-vermilion-500 bg-[#F8E9E3] px-3 py-3 text-sm text-vermilion-600">{error}</p>}</div><button type="submit" disabled={busy} className="flex min-h-12 w-full items-center justify-between bg-carbon-950 px-4 text-sm font-semibold text-canvas-50 transition-colors hover:bg-vermilion-500 disabled:cursor-wait disabled:opacity-60 focus-visible:outline-none">{busy ? "Signing in..." : "Sign in to knowledge desk"}<ArrowRight size={16} aria-hidden="true" /></button><p className="text-center text-sm text-carbon-500">New to the desk? <Link to="/register" className="font-semibold text-vermilion-600 underline underline-offset-4 focus-visible:outline-none">Create an account</Link></p></form></section></AuthBackground>;
}

function Field({ id, label, type, value, onChange, icon: Icon, ...props }) { return <div><label htmlFor={id} className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">{label}</label><div className="relative"><Icon size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-carbon-500" aria-hidden="true" /><input id={id} type={type} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-12 w-full border border-carbon-950 bg-canvas-50 px-3 pl-10 text-sm text-carbon-950 placeholder:text-carbon-500 focus:outline-none focus:ring-2 focus:ring-vermilion-500" {...props} /></div></div>; }
