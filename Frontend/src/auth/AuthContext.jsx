import { createContext, useContext, useEffect, useState } from "react";
import { login as loginApi, register as registerApi } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem("appToken") || "");
  const [user, setUser] = useState(() => {
    const stored = sessionStorage.getItem("appUser");
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      sessionStorage.removeItem("appUser");
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
      sessionStorage.setItem("appToken", data.access_token);
      setUser(authUser);
      sessionStorage.setItem("appUser", JSON.stringify(authUser));
      return data;
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (username, email, password) => {
    setLoading(true);
    try {
      await registerApi(username, email, password);
      // Auto-login after successful registration
      return await signIn(username, password);
    } finally {
      setLoading(false);
    }
  };

  const signOut = () => {
    setToken("");
    setUser(null);
    sessionStorage.removeItem("appToken");
    sessionStorage.removeItem("appUser");
    localStorage.removeItem("bearerToken");
  };

  return (
    <AuthContext.Provider value={{ token, user, loading, signIn, signUp, signOut }}>
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
