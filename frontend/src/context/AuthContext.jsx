import { createContext, useContext, useState, useEffect, useCallback } from "react";

import { API_BASE as API } from "../lib/apiBase";
const AuthContext = createContext(null);

const SESSION_KEY = "cs_session_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(SESSION_KEY));
  const [user, setUser] = useState(null);
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMe = useCallback(async (t) => {
    if (!t) { setLoading(false); return; }
    try {
      const res = await fetch(`${API}/api/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.status === 401) {
        localStorage.removeItem(SESSION_KEY);
        setToken(null);
        setUser(null);
        setCompany(null);
        setError("Your session has expired. Please sign in again.");
      } else {
        const data = await res.json();
        setUser({ email: data.email, full_name: data.full_name, role: data.role });
        setCompany(data.company);
      }
    } catch {
      setError("Unable to verify session.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMe(token); }, [token, fetchMe]);

  const login = (newToken, userData, companyData) => {
    localStorage.setItem(SESSION_KEY, newToken);
    setToken(newToken);
    setUser(userData);
    setCompany(companyData);
  };

  const logout = async () => {
    if (token) {
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    localStorage.removeItem(SESSION_KEY);
    setToken(null);
    setUser(null);
    setCompany(null);
  };

  const isAdmin = user?.role === "admin";
  const isMember = user?.role === "member" || isAdmin;

  return (
    <AuthContext.Provider value={{
      token, user, company, loading, error,
      login, logout, isAdmin, isMember,
      isAuthenticated: !!token && !!user,
      refetch: () => fetchMe(token),
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
