import { useEffect, useState } from "react";
import { Save, UserRound } from "lucide-react";
import { useAuth } from "../../context/useAuth";
import { useToast } from "../../context/useToast";

export function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const toast = useToast();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => setName(user?.name || ""), [user]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await updateProfile({ name });
      toast.push("Profile updated.");
    } catch (caught) {
      toast.push(caught?.message || "Profile could not be updated.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-canvas-100">
      <div className="mx-auto max-w-4xl px-5 py-10 sm:px-8 lg:py-14">
        <header className="border-b border-carbon-950 pb-8">
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-600">Account / identity</p>
          <h1 className="mt-3 font-display text-[clamp(3rem,7vw,6rem)] leading-[0.84] tracking-[-0.055em]">Your <span className="italic text-vermilion-500">profile.</span></h1>
        </header>
        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <form onSubmit={submit} className="border border-carbon-950 bg-canvas-50 p-5 sm:p-7">
            <div className="flex items-center gap-3 border-b border-canvas-300 pb-5">
              <span className="flex h-10 w-10 items-center justify-center bg-moss-500 text-white"><UserRound size={18} aria-hidden="true" /></span>
              <div><h2 className="font-display text-2xl">Identity details</h2><p className="text-xs text-carbon-500">Keep your workspace profile current.</p></div>
            </div>
            <label htmlFor="profile-name" className="mb-2 mt-6 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Full name</label>
            <input id="profile-name" value={name} onChange={(event) => setName(event.target.value)} minLength={1} maxLength={120} required className="min-h-12 w-full border border-carbon-950 bg-canvas-50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-vermilion-500" />
            <label htmlFor="profile-email" className="mb-2 mt-5 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Work email</label>
            <input id="profile-email" value={user?.email || ""} readOnly className="min-h-12 w-full border border-canvas-300 bg-canvas-100 px-3 text-sm text-carbon-500" />
            <p className="mt-2 text-xs text-carbon-500">Email changes are managed by your organization administrator.</p>
            <button type="submit" disabled={busy} className="mt-7 flex min-h-11 items-center gap-2 bg-carbon-950 px-4 text-xs font-semibold text-canvas-50 hover:bg-vermilion-500 disabled:opacity-50 focus-visible:outline-none"><Save size={14} aria-hidden="true" /> {busy ? "Saving..." : "Save profile"}</button>
          </form>
          <aside className="border-t border-carbon-950 pt-4 lg:border-l lg:border-t-0 lg:pl-6">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Account status</p>
            <p className="mt-3 font-display text-3xl text-moss-500">{user?.is_active === false ? "Inactive" : "Active"}</p>
            <dl className="mt-5 space-y-3 text-xs"><div><dt className="text-carbon-500">Role</dt><dd className="mt-1 font-semibold uppercase">{user?.role || "USER"}</dd></div><div><dt className="text-carbon-500">Member since</dt><dd className="mt-1 font-semibold">{formatDate(user?.created_at)}</dd></div></dl>
          </aside>
        </div>
      </div>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleDateString();
}
