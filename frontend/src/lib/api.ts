import type {Auth,Leader,Referral,Tx,User,Withdrawal} from '../types';
// Configure via .env / .env.local: VITE_API_BASE=http://localhost:8000
const API = import.meta.env.VITE_API_BASE || 'https://earn-bot-api.onrender.com';
async function req<T>(path:string, token:string, init:RequestInit={}){const r=await fetch(API+path,{...init,headers:{'Content-Type':'application/json',...(init.headers||{}),Authorization:`Bearer ${token}`}}); if(!r.ok){let e:any={};try{e=await r.json()}catch{};throw new Error(e.detail||'Something went wrong');}return r.json() as Promise<T>}
export const auth=(initData:string,referral_code?:string)=>fetch(API+'/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({init_data:initData,referral_code})}).then(async r=>{if(!r.ok){let e:any={};try{e=await r.json()}catch{};throw new Error(e.detail||'Authentication failed')}return r.json() as Promise<Auth>});
export const me=(t:string)=>req<{balance:string;telegram_id:number}>('/api/me',t);
export const transactions=(t:string)=>req<{transactions:Tx[];total:number}>('/api/transactions?limit=50',t);
export const withdrawals=(t:string)=>req<Withdrawal[]>('/api/withdrawals',t);
export const referral=(t:string)=>req<Referral>('/api/referrals/me',t);
export const payouts=(t:string)=>req<{leaderboard:Leader[]}>('/api/leaderboard/payouts?limit=10',t);
export const referrers=(t:string)=>req<{leaderboard:Leader[]}>('/api/leaderboard/referrers?limit=10',t);
export const withdraw=(t:string,body:{amount:number;payout_method:string;payout_address:string;idempotency_key:string})=>req<Withdrawal>('/api/withdrawals',t,{method:'POST',body:JSON.stringify(body)});
export const apiBase=API;
