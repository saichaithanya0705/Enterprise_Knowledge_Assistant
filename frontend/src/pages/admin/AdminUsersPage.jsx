import { useCallback, useEffect, useMemo, useState } from "react";
import { Power, Search, UserCog } from "lucide-react";
import { adminService } from "../../services/adminService";
import { useToast } from "../../context/useToast";

export function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setUsers(await adminService.listUsers());
    } catch (caught) {
      setError(caught?.message || "Users could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => users.filter((user) => (
    `${user.name || ""} ${user.email || ""} ${user.role || ""}`.toLowerCase().includes(query.toLowerCase())
  )), [query, users]);

  const update = async (user, payload, message) => {
    try {
      await adminService.updateUser(user.id, payload);
      setUsers((current) => current.map((item) => item.id === user.id ? { ...item, ...payload } : item));
      toast.push(message);
    } catch (caught) {
      toast.push(caught?.message || "User could not be updated.", "error");
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
        <header className="border-b border-carbon-950 pb-8">
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-600">Control room / access registry</p>
          <h1 className="mt-3 font-display text-[clamp(3rem,7vw,6.5rem)] leading-[0.82] tracking-[-0.055em]">People <span className="italic text-vermilion-500">index.</span></h1>
          <p className="mt-5 max-w-xl text-sm leading-7 text-carbon-500">Review account roles and keep administrative access intentional.</p>
        </header>
        <section className="mt-8">
          <label className="relative mb-5 block max-w-md"><span className="sr-only">Search users</span><Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-carbon-500" aria-hidden="true" /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, email, or role" className="min-h-11 w-full border border-carbon-950 bg-canvas-50 px-3 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-vermilion-500" /></label>
          {error && <p role="alert" className="mb-5 border-l-4 border-vermilion-500 bg-[#F8E9E3] px-4 py-3 text-sm text-vermilion-600">{error}</p>}
          <div className="overflow-x-auto border-y border-carbon-950">
            {loading ? <div className="h-48 animate-pulse bg-canvas-50" aria-label="Loading users" /> : (
              <table className="w-full min-w-[48rem] text-left">
                <thead className="border-b border-carbon-950 font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500"><tr><th className="px-3 py-3 font-normal">Person</th><th className="px-3 py-3 font-normal">Role</th><th className="px-3 py-3 font-normal">Status</th><th className="px-3 py-3 text-right font-normal">Actions</th></tr></thead>
                <tbody>{filtered.map((user) => {
                  const isAdmin = String(user.role).toUpperCase() === "ADMIN";
                  return <tr key={user.id} className="border-b border-canvas-300 last:border-0"><td className="px-3 py-4"><p className="font-semibold">{user.name}</p><p className="mt-1 text-xs text-carbon-500">{user.email}</p></td><td className="px-3 py-4 font-mono text-[9px] uppercase">{user.role}</td><td className={`px-3 py-4 font-mono text-[9px] uppercase ${user.is_active ? "text-moss-500" : "text-vermilion-600"}`}>{user.is_active ? "active" : "inactive"}</td><td className="px-3 py-4"><div className="flex justify-end gap-2"><button type="button" onClick={() => update(user, { role: isAdmin ? "USER" : "ADMIN" }, `${user.email} role updated.`)} className="inline-flex min-h-9 items-center gap-2 border border-carbon-950 px-3 text-xs hover:bg-carbon-950 hover:text-canvas-50 focus-visible:outline-none"><UserCog size={14} aria-hidden="true" /> {isAdmin ? "Make user" : "Make admin"}</button><button type="button" onClick={() => update(user, { is_active: !user.is_active }, `${user.email} status updated.`)} className="inline-flex min-h-9 items-center gap-2 border border-carbon-950 px-3 text-xs hover:bg-carbon-950 hover:text-canvas-50 focus-visible:outline-none"><Power size={14} aria-hidden="true" /> {user.is_active ? "Deactivate" : "Activate"}</button></div></td></tr>;
                })}</tbody>
              </table>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
