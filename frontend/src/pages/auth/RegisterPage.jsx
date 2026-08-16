import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Mail, UserRound } from "lucide-react";
import { AuthBackground } from "../../components/AuthBackground";
import { PasswordStrength } from "../../components/PasswordStrength";
import { useAuth } from "../../context/useAuth";
import { useToast } from "../../context/useToast";

export function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await register(form);
      const role = String(result.user?.role || "USER").toUpperCase();
      toast.push("Your account is ready.");
      navigate(role === "ADMIN" ? "/admin" : "/app", { replace: true });
    } catch (caught) {
      const message = caught?.message || "We could not create your account.";
      setError(message);
      toast.push(message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthBackground eyebrow="New member registration">
      <section className="border border-carbon-950 bg-canvas-50 shadow-paper">
        <div className="border-b border-carbon-950 px-6 py-7 sm:px-8">
          <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-vermilion-600">Start with a clear identity</p>
          <h2 className="mt-2 font-display text-4xl tracking-tight">Create account</h2>
          <p className="mt-2 text-sm leading-6 text-carbon-500">Your workspace access is tied to your organization email.</p>
        </div>
        <form onSubmit={submit} className="space-y-5 px-6 py-7 sm:px-8">
          <Field id="register-name" label="Full name" value={form.name} onChange={update("name")} icon={UserRound} autoComplete="name" />
          <Field id="register-email" label="Work email" type="email" value={form.email} onChange={update("email")} icon={Mail} autoComplete="email" />
          <div>
            <label htmlFor="register-password" className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Password</label>
            <input id="register-password" type="password" value={form.password} onChange={update("password")} minLength={8} maxLength={128} autoComplete="new-password" required className="min-h-12 w-full border border-carbon-950 bg-canvas-50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-vermilion-500" />
            <PasswordStrength password={form.password} />
          </div>
          <div>
            <label htmlFor="register-confirm" className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Confirm password</label>
            <input id="register-confirm" type="password" value={form.confirm_password} onChange={update("confirm_password")} minLength={8} maxLength={128} autoComplete="new-password" required className="min-h-12 w-full border border-carbon-950 bg-canvas-50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-vermilion-500" />
          </div>
          {error && <p role="alert" className="border-l-4 border-vermilion-500 bg-[#F8E9E3] px-3 py-3 text-sm text-vermilion-600">{error}</p>}
          <button type="submit" disabled={busy} className="flex min-h-12 w-full items-center justify-between bg-carbon-950 px-4 text-sm font-semibold text-canvas-50 hover:bg-vermilion-500 disabled:cursor-wait disabled:opacity-60 focus-visible:outline-none">
            {busy ? "Creating account..." : "Create secure account"}<ArrowRight size={16} aria-hidden="true" />
          </button>
          <p className="text-center text-sm text-carbon-500">Already registered? <Link to="/login" className="font-semibold text-vermilion-600 underline underline-offset-4 focus-visible:outline-none">Sign in</Link></p>
        </form>
      </section>
    </AuthBackground>
  );
}

function Field({ id, label, type = "text", value, onChange, icon: Icon, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">{label}</label>
      <div className="relative">
        <Icon size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-carbon-500" aria-hidden="true" />
        <input id={id} type={type} value={value} onChange={onChange} maxLength={128} required className="min-h-12 w-full border border-carbon-950 bg-canvas-50 px-3 pl-10 text-sm focus:outline-none focus:ring-2 focus:ring-vermilion-500" {...props} />
      </div>
    </div>
  );
}
