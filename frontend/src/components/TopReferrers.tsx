import { Users } from "lucide-react";
import { formatBalance, shortName } from "../lib/utils";

const MOCK = [
  { rank: 1, username: "referral_pro", first_name: null, referrals: 142, earnings: "89.30" },
  { rank: 2, username: "networker", first_name: null, referrals: 98, earnings: "61.20" },
  { rank: 3, username: null, first_name: "Mike", referrals: 76, earnings: "48.90" },
  { rank: 4, username: "invite_king", first_name: null, referrals: 54, earnings: "34.10" },
  { rank: 5, username: "growth_hacker", first_name: null, referrals: 41, earnings: "27.80" },
];

export function TopReferrers() {
  return (
    <div className="mx-5 mt-6 mb-8">
      <div className="flex items-center gap-2 mb-3">
        <Users className="w-4 h-4 text-gold-400" />
        <h3 className="font-semibold text-white">Top Referrers</h3>
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
                  item.rank <= 3
                    ? "bg-gold-500/20 text-gold-400"
                    : "bg-premium-600 text-gray-400"
                }`}
              >
                {item.rank}
              </span>
              <div>
                <p className="text-sm font-medium text-white">
                  {shortName(item)}
                </p>
                <p className="text-xs text-gray-500">
                  {item.referrals} referrals
                </p>
              </div>
            </div>
            <span className="font-semibold text-emerald-400">
              ${formatBalance(item.earnings)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
