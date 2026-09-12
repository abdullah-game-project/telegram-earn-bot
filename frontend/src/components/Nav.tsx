import {House, Zap, Users, WalletCards, Trophy} from 'lucide-react';
export type Tab='home'|'earn'|'friends'|'wallet'|'leaderboard';
export default function Nav({tab,setTab}:{tab:Tab;setTab:(t:Tab)=>void}){const items:[[Tab,string,any],...any[]]=[['home','Home',House],['earn','Earn',Zap],['friends','Friends',Users],['wallet','Wallet',WalletCards],['leaderboard','Rank',Trophy]];return <nav className="bottom-nav">{items.map(([id,label,Icon])=><button key={id} onClick={()=>setTab(id)} className={tab===id?'active':''}><Icon size={20} strokeWidth={2.2}/><span>{label}</span></button>)}</nav>}
