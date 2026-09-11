import { Crown } from "lucide-react";

interface Props {
  firstName?: string | null;
  username?: string | null;
}

export function Header({ firstName, username }: Props) {
  return (
    <div className="flex items-center justify-between px-5 pt-4 pb-2">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold">
          <Crown className="w-6 h-6 text-premium-900" />
        </div>
        <div>
          <p className="text-sm text-gray-400">Welcome back</p>
          <p className="font-semibold text-white">
            {firstName || username || "User"}
          </p>
        </div>
      </div>
      <div className="text-xs font-medium px-3 py-1.5 rounded-full bg-premium-700 border border-gold-500/20 text-gold-400">
        PREMIUM
      </div>
    </div>
  );
}
