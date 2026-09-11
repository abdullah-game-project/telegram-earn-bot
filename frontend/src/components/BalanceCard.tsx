import { Wallet, RefreshCw } from "lucide-react";
import { formatBalance } from "../lib/utils";

interface Props {
  balance: string;
  onRefresh?: () => void;
  loading?: boolean;
}

export function BalanceCard({ balance, onRefresh, loading }: Props) {
  return (
    <div className="mx-5 mt-2 relative overflow-hidden rounded-3xl p-6 bg-card-gradient border border-gold-500/20 shadow-gold">
      {/* Decorative glow */}
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-gold-500/10 rounded-full blur-3xl" />
      
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-gray-400">
            <Wallet className="w-4 h-4" />
            <span className="text-sm font-medium">Available Balance</span>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 rounded-xl bg-premium-700/80 hover:bg-premium-600 transition"
            >
              <RefreshCw className={`w-4 h-4 text-gold-400 ${loading ? "animate-spin" : ""}`} />
            </button>
          )}
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-extrabold gold-text tracking-tight">
            ${formatBalance(balance)}
          </span>
          <span className="text-sm text-gray-500 font-medium">USD</span>
        </div>

        <p className="mt-3 text-xs text-gray-500">
          90% of all revenue goes to you
        </p>
      </div>
    </div>
  );
}
