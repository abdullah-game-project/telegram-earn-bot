const API_BASE = "https://earn-bot-api.onrender.com";

export async function authenticate(initData: string) {
  const res = await fetch(`${API_BASE}/api/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Authentication failed");
  }

  return res.json();
}

export async function getMe(token: string) {
  const res = await fetch(`${API_BASE}/api/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Failed to fetch balance");
  return res.json();
}

// These will be real once we add backend endpoints
export async function getTransactions(token: string): Promise<any[]> {
  // Placeholder – returns empty until backend endpoint is ready
  return [];
}
