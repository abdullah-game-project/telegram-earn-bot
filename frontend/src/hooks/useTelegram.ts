import { useEffect, useState } from "react";

declare global {
  interface Window {
    Telegram: {
      WebApp: any;
    };
  }
}

export function useTelegram() {
  const [webApp, setWebApp] = useState<any>(null);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      tg.setHeaderColor("#0a0a0f");
      tg.setBackgroundColor("#0a0a0f");
      setWebApp(tg);
      setUser(tg.initDataUnsafe?.user || null);
    }
  }, []);

  return { webApp, user, initData: webApp?.initData || "" };
}
