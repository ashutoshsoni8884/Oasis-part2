import { createContext, useContext, useEffect, useState } from "react";
import { login as loginApi } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("appToken") || "");
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("appUser");
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      localStorage.removeItem("appUser");
      setUser(null);
    }
  }, [token]);

  const signIn = async (username, password) => {
    setLoading(true);
    try {
      const data = await loginApi(username, password);
      const authUser = {
        username,
        name: username,
        initials: username.slice(0, 1).toUpperCase(),
      };
      setToken(data.access_token);
      localStorage.setItem("appToken", data.access_token);
      setUser(authUser);
      localStorage.setItem("appUser", JSON.stringify(authUser));
      return data;
    } finally {
      setLoading(false);
    }
  };

  const signOut = () => {
    setToken("");
    setUser(null);
    localStorage.removeItem("appToken");
    localStorage.removeItem("appUser");
  };

  return (
    <AuthContext.Provider value={{ token, user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
