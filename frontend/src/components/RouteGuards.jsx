import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth";

function GuardLoading() {
  return (
    <main className="grid min-h-[100dvh] place-items-center bg-canvas-100 px-6 text-carbon-950" aria-live="polite">
      <div className="w-full max-w-sm border border-carbon-950 bg-canvas-50 p-6 shadow-paper">
        <div className="h-2 w-24 animate-pulse bg-canvas-300" />
        <div className="mt-5 h-4 w-3/4 animate-pulse bg-canvas-200" />
        <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-carbon-500">Checking workspace access</p>
      </div>
    </main>
  );
}

export function RequireAuth() {
  const { loading, isAuthenticated } = useAuth();
  const location = useLocation();
  if (loading) return <GuardLoading />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}

export function RequireAdmin() {
  const { loading, isAuthenticated, isAdmin } = useAuth();
  if (loading) return <GuardLoading />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function PublicOnly() {
  const { loading, isAuthenticated, isAdmin } = useAuth();
  if (loading) return <GuardLoading />;
  if (isAuthenticated) return <Navigate to={isAdmin ? "/admin" : "/"} replace />;
  return <Outlet />;
}
