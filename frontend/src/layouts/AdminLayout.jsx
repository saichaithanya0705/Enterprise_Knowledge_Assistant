import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Menu, ShieldCheck, X, LogOut } from "lucide-react";
import { useAuth } from "../context/useAuth";

const links = [
  ["/admin", "Overview", "01"],
  ["/admin/users", "People", "02"],
  ["/admin/documents", "Documents", "03"],
  ["/admin/conversations", "Conversations", "04"],
  ["/admin/restore-requests", "Restore requests", "05"],
  ["/admin/audit-log", "Audit log", "06"],
];

export function AdminLayout() {
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const close = () => setOpen(false);
  const logout = async () => { await signOut(); navigate("/login", { replace: true }); };

  return (
    <div className="min-h-[100dvh] bg-canvas-100 text-carbon-950 lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <button type="button" aria-label="Open admin navigation" onClick={() => setOpen(true)} className="fixed left-4 top-4 z-30 flex h-10 w-10 items-center justify-center border border-carbon-950 bg-carbon-950 text-canvas-50 lg:hidden"><Menu size={18} aria-hidden="true" /></button>
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[17rem] flex-col border-r border-carbon-950 bg-carbon-950 text-canvas-50 transition-transform lg:static lg:w-auto lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-start justify-between border-b border-white/10 px-5 py-6">
          <div><p className="font-display text-2xl">Control<span className="text-vermilion-400">.</span>room</p><p className="mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-canvas-500">Administrator access</p></div>
          <button type="button" aria-label="Close admin navigation" onClick={close} className="flex h-9 w-9 items-center justify-center border border-white/15 text-canvas-500 hover:bg-white/10 focus-visible:outline-none lg:hidden"><X size={16} aria-hidden="true" /></button>
        </div>
        <nav aria-label="Admin navigation" className="flex-1 px-3 py-6">
          <p className="px-3 pb-3 font-mono text-[9px] uppercase tracking-[0.2em] text-canvas-500">Workspace control</p>
          {links.map(([to, label, index]) => <NavLink key={to} to={to} end={to === "/admin"} onClick={close} className={({ isActive }) => `group flex min-h-12 items-center justify-between border-l-2 px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vermilion-400 ${isActive ? "border-vermilion-400 bg-white/10 text-white" : "border-transparent text-canvas-500 hover:bg-white/5 hover:text-canvas-50"}`}><span>{label}</span><span className="font-display text-lg italic text-vermilion-400">{index}</span></NavLink>)}
        </nav>
        <div className="border-t border-white/10 p-4">
          <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center bg-moss-500 text-sm font-semibold text-white"><ShieldCheck size={17} aria-hidden="true" /></span><div className="min-w-0"><p className="truncate text-sm text-canvas-50">{user?.name || "Administrator"}</p><p className="font-mono text-[9px] uppercase tracking-[0.12em] text-canvas-500">Admin account</p></div></div>
          <button type="button" onClick={logout} className="mt-5 flex min-h-10 w-full items-center gap-2 border border-white/15 px-3 text-xs text-canvas-300 hover:bg-white/10 hover:text-white focus-visible:outline-none"><LogOut size={14} aria-hidden="true" /> Sign out</button>
        </div>
      </aside>
      {open && <button type="button" aria-label="Close admin navigation overlay" onClick={close} className="fixed inset-0 z-30 bg-carbon-950/55 lg:hidden" />}
      <main className="min-w-0 pt-16 lg:pt-0"><Outlet /></main>
    </div>
  );
}
