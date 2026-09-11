import { useState, useEffect } from "react";
import { authenticate, getMe } from "../lib/api";
import { User } from "../types";
import { useTelegram } from "./useTelegram";

export function useAuth() {
  const { initData } = useTelegram();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!initData) {
      // For local development without Telegram
      setLoading(false);
      return;
    }

    (async () => {
      try {
        setLoading(true);
        const auth = await authenticate(initData);
        setToken(auth.access_token);
        setUser(auth.user);
        localStorage.setItem("earn_token", auth.access_token);
      } catch (err: any) {
        setError(err.message || "Auth failed");
      } finally {
        setLoading(false);
      }
    })();
  }, [initData]);

  const refreshBalance = async () => {
    if (!token) return;
    try {
      const data = await getMe(token);
      setUser((prev) => (prev ? { ...prev, balance: data.balance } : null));
    } catch (e) {
      console.error(e);
    }
  };

  return { token, user, loading, error, refreshBalance };
}
