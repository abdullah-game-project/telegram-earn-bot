import { Activity } from "lucide-react";
import { formatBalance, formatDate } from "../lib/utils";
import { Transaction } from "../types";

// Mock data for now (will be replaced by real API)
const MOCK_TX: Transaction[] = [
  { id: 1, type: "earn", amount: "0.42", description: "Rewarded Ad", created_at: new Date().toISOString() },
  { id: 2, type: "earn", amount: "1.85", description: "CPA Offer - Survey", created_at: new Date(Date.now() - 3600000).toISOString() },
  { id: 3, type: "earn", amount: "0.18", description: "Rewarded Ad", created_at: new Date(Date.now() - 7200000).toISOString() },
  { id: 4, type: "withdraw", amount: "12.50", description: "USDT Withdrawal", created_at: new Date(Date.now() - 86400000).toISOString() },
];

export function LiveTransactions() {
  return (
    <div className="mx-5 mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-gold-400" />
        <h3 className="font-semibold text-white">Live Transactions</h3>
      </div>

      <div className="space-y-2">
        {MOCK_TX.map((tx) => (
          <div
            key={tx.id}
            className="flex items-center justify-between p-3.5 rounded-2xl glass"
          >
            <div>
              <p className="text-sm font-medium text-white">
                {tx.description || tx.type}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {formatDate(tx.created_at)}
              </p>
            </div>
            <span
              className={`font-semibold ${
                tx.type === "earn" ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {tx.type === "earn" ? "+" : "-"}${formatBalance(tx.amount)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
