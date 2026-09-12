export type User={telegram_id:number;username:string|null;first_name:string|null;balance:string;is_banned:boolean;referral_code?:string};
export type Auth={access_token:string;refresh_token:string;token_type:string;user:User};
export type Tx={id:number;amount:string;type:string;balance_after:string;description:string|null;created_at:string};
export type Withdrawal={id:number;amount:string;status:string;payout_method:string;payout_address:string;requested_at:string;processed_at:string|null;admin_note:string|null};
export type Referral={referral_code:string;referral_count:number;total_referral_earnings:string};
export type Leader={rank:number;telegram_id:number;username:string|null;first_name:string|null;value:string;display_name:string};
