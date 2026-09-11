import { Play, Gift, ArrowUpRight } from "lucide-react";

export function ActionButtons() {
  return (
    <div className="grid grid-cols-3 gap-3 px-5 mt-5">
      <button className="flex flex-col items-center gap-2 p-4 rounded-2xl glass hover:border-gold-500/40 transition active:scale-95">
        <div className="w-12 h-12 rounded-2xl bg-gold-500/15 flex items-center justify-center">
          <Play className="w-6 h-6 text-gold-400" />
        </div>
        <span className="text-xs font-medium text-gray-300">Watch Ads</span>
      </button>

      <button className="flex flex-col items-center gap-2 p-4 rounded-2xl glass hover:border-gold-500/40 transition active:scale-95">
        <div className="w-12 h-12 rounded-2xl bg-gold-500/15 flex items-center justify-center">
          <Gift className="w-6 h-6 text-gold-400" />
        </div>
        <span className="text-xs font-medium text-gray-300">Offers</span>
      </button>

      <button className="flex flex-col items-center gap-2 p-4 rounded-2xl glass hover:border-gold-500/40 transition active:scale-95">
        <div className="w-12 h-12 rounded-2xl bg-gold-500/15 flex items-center justify-center">
          <ArrowUpRight className="w-6 h-6 text-gold-400" />
        </div>
        <span className="text-xs font-medium text-gray-300">Withdraw</span>
      </button>
    </div>
  );
}
