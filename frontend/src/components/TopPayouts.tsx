import { Trophy } from "lucide-react";
import { formatBalance, shortName } from "../lib/utils";

const MOCK = [
  { rank: 1, username: "crypto_king", first_name: null, amount: "248.50" },
  { rank: 2, username: null, first_name: "Alex", amount: "189.20" },
  { rank: 3, username: "earn_master", first_name: null, amount: "156.80" },
  { rank: 4, username: "moonbag", first_name: null, amount: "132.10" },
  { rank: 5, username: null, first_name: "Sara", amount: "98.45" },
];

export function TopPayouts() {
  return (
    <div className="mx-5 mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-4 h-4 text-gold-400" />
        <h3 className="font-semibold text-white">Top Payouts</h3>
      </div>

      <div className="rounded-2xl glass overflow-hidden">
        {MOCK.map((item, i) => (
          <div
            key={item.rank}
            className={`flex items-center justify-between px-4 py-3.5 ${
              i !== MOCK.length - 1 ? "border-b border-white/5" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  item.rank === 1
                    ? "bg-gold-gradient text-premium-900"
                    : item.rank === 2
                    ? "bg-gray-400 text-premium-900"
                    : item.rank === 3
                    ? "bg-amber-700 text-white"
                    : "bg-premium-600 text-gray-300"
                }`}
              >
                {item.rank}
              </span>
              <span className="text-sm font-medium text-white">
                {shortName(item)}
              </span>
            </div>
            <span className="font-semibold text-gold-400">
              ${formatBalance(item.amount)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
