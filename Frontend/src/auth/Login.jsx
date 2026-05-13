import { useState } from "react";
import { useAuth } from "./AuthContext";
import Signup from "./Signup";

export default function Login() {
  const { signIn, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [mode, setMode] = useState("login"); // "login" | "signup"

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!username || !password) {
      setError("Username and password are required.");
      return;
    }

    try {
      await signIn(username.trim(), password);
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
    }
  };

  if (mode === "signup") {
    return <Signup onBackToLogin={() => setMode("login")} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#F7F9FC", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div style={{ width: "100%", maxWidth: "420px", background: "#fff", borderRadius: "18px", boxShadow: "0 18px 38px rgba(15, 23, 42, 0.08)", padding: "32px" }}>
        <h1 style={{ fontSize: "24px", marginBottom: "12px", color: "#0F172A" }}>Oracle Agent Hub</h1>
        <p style={{ marginBottom: "22px", color: "#64748B" }}>Sign in with your application credentials to continue.</p>
        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />
          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Password</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Enter your password"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />
          {error && <div style={{ marginBottom: "14px", color: "#B91C1C", fontSize: "13px" }}>{error}</div>}
          <button
            type="submit"
            disabled={loading}
            style={{ width: "100%", padding: "12px", borderRadius: "12px", border: "none", background: "#1D4ED8", color: "#fff", fontWeight: 700, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <div style={{ marginTop: "18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "12px", color: "#64748B" }}>New here?</span>
          <button
            type="button"
            onClick={() => setMode("signup")}
            style={{ border: "none", background: "transparent", color: "#1D4ED8", cursor: "pointer", fontWeight: 700, fontSize: "12px", padding: 0 }}
          >
            Create an account
          </button>
        </div>
      </div>
    </div>
  );
}
