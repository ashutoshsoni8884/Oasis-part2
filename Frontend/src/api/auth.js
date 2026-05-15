const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

async function request(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail || data?.message || `Request failed with status ${res.status}`);
  }
  return data;
}

export function login(username, password) {
  return request("/api/auth/login", { username, password });
}

export function register(username, email, password) {
  return request("/api/auth/register", { username, email, password });
}
