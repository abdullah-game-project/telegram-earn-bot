export interface User {
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  balance: string;
  is_banned: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Transaction {
  id: number;
  type: "earn" | "withdraw" | "adjustment";
  amount: string;
  description: string | null;
  created_at: string;
}

export interface TopPayout {
  rank: number;
  username: string | null;
  first_name: string | null;
  amount: string;
}

export interface TopReferrer {
  rank: number;
  username: string | null;
  first_name: string | null;
  referrals: number;
  earnings: string;
}
