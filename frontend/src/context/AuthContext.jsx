import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../services/apiClient";
import { authService, clearStoredToken, hasStoredToken } from "../services/authService";
import { AuthContext } from "./authContextValue";

function isAdminUser(user) {
  return String(user?.role || "").toUpperCase() === "ADMIN"
    || user?.is_admin === true
    || user?.roles?.some?.((role) => String(role).toUpperCase() === "ADMIN");
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      clearStoredToken();
      setUser(null);
    }
  }, []);

  const loadUser = useCallback(async () => {
    if (!hasStoredToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await authService.me());
    } catch {
      clearStoredToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const cleanup = typeof apiClient.setUnauthorizedHandler === "function"
      ? apiClient.setUnauthorizedHandler(() => {
        clearStoredToken();
        setUser(null);
      })
      : undefined;
    loadUser();
    return () => {
      if (typeof cleanup === "function") cleanup();
    };
  }, [loadUser]);

  const signIn = useCallback(async (credentials) => {
    const result = await authService.login(credentials);
    const nextUser = result.user || await authService.me();
    setUser(nextUser);
    return nextUser;
  }, []);

  const register = useCallback(async (details) => {
    const result = await authService.register(details);
    if (result.user) setUser(result.user);
    return result;
  }, []);

  const updateProfile = useCallback(async (details) => {
    const nextUser = await authService.updateProfile(details);
    setUser(nextUser);
    return nextUser;
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    isAuthenticated: Boolean(user),
    isAdmin: isAdminUser(user),
    signIn,
    register,
    signOut,
    updateProfile,
    refreshUser: loadUser,
  }), [loadUser, loading, register, signIn, signOut, updateProfile, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
