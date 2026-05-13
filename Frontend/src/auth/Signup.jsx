import { useState } from "react";
import { useAuth } from "./AuthContext";

export default function Signup({ onBackToLogin }) {
  const { signUp, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const u = username.trim();
    const e = email.trim();

    if (!u || !e || !password) {
      setError("Username, email, and password are required.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      await signUp(u, e, password);
    } catch (err) {
      setError(err.message || "Sign up failed. Please try again.");
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#F7F9FC", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div style={{ width: "100%", maxWidth: "460px", background: "#fff", borderRadius: "18px", boxShadow: "0 18px 38px rgba(15, 23, 42, 0.08)", padding: "32px" }}>
        <h1 style={{ fontSize: "24px", marginBottom: "12px", color: "#0F172A" }}>Create account</h1>
        <p style={{ marginBottom: "22px", color: "#64748B" }}>Sign up to access Oracle Agent Hub.</p>

        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Choose a username"
            autoComplete="username"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />

          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />

          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Password</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Create a password"
            autoComplete="new-password"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />

          <label style={{ display: "block", fontSize: "12px", marginBottom: "6px", color: "#475569" }}>Confirm password</label>
          <input
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            type="password"
            placeholder="Re-enter your password"
            autoComplete="new-password"
            style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #CBD5E0", marginBottom: "16px", fontSize: "14px" }}
          />

          {error && <div style={{ marginBottom: "14px", color: "#B91C1C", fontSize: "13px" }}>{error}</div>}

          <button
            type="submit"
            disabled={loading}
            style={{ width: "100%", padding: "12px", borderRadius: "12px", border: "none", background: "#1D4ED8", color: "#fff", fontWeight: 700, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "18px", fontSize: "12px", color: "#64748B" }}>
          <button
            type="button"
            onClick={onBackToLogin}
            style={{ border: "none", background: "transparent", color: "#1D4ED8", cursor: "pointer", fontWeight: 600, padding: 0 }}
          >
            ← Back to sign in
          </button>
        </div>
      </div>
    </div>
  );
}

