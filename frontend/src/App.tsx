import { useAuth } from "./hooks/useAuth";
import { Header } from "./components/Header";
import { BalanceCard } from "./components/BalanceCard";
import { ActionButtons } from "./components/ActionButtons";
import { LiveTransactions } from "./components/LiveTransactions";
import { TopPayouts } from "./components/TopPayouts";
import { TopReferrers } from "./components/TopReferrers";
import { Loader2 } from "lucide-react";

export default function App() {
  const { user, loading, error, refreshBalance } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-premium-900">
        <Loader2 className="w-10 h-10 text-gold-400 animate-spin" />
        <p className="text-gray-400 text-sm">Connecting to Earn Bot...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6 bg-premium-900">
        <p className="text-red-400 text-center mb-4">{error}</p>
        <p className="text-gray-500 text-sm text-center">
          Please open this app from the Telegram bot.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-premium-900 pb-10">
      <Header firstName={user?.first_name} username={user?.username} />
      
      <BalanceCard
        balance={user?.balance || "0"}
        onRefresh={refreshBalance}
      />

      <ActionButtons />

      <LiveTransactions />
      <TopPayouts />
      <TopReferrers />

      <div className="text-center text-xs text-gray-600 mt-4 pb-6">
        Earn Bot • 90% to users
      </div>
    </div>
  );
}
