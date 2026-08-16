const LEVELS = ["Too short", "Needs work", "Fair", "Good", "Strong"];

function getPasswordScore(password = "") {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  return Math.min(score, 4);
}

export function PasswordStrength({ password = "" }) {
  const score = password ? getPasswordScore(password) : 0;
  const label = password ? LEVELS[score] : "Enter a password";
  return (
    <div className="mt-3" aria-live="polite">
      <div className="flex gap-1" role="progressbar" aria-label="Password strength" aria-valuemin="0" aria-valuemax="4" aria-valuenow={score} aria-valuetext={label}>
        {[0, 1, 2, 3].map((index) => (
          <span key={index} className={`h-1.5 flex-1 ${index < score ? (score >= 3 ? "bg-moss-500" : "bg-vermilion-500") : "bg-canvas-300"}`} />
        ))}
      </div>
      <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.15em] text-carbon-500">{label}</p>
    </div>
  );
}
