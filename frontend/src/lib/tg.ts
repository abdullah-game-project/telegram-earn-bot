export type TG=any;
export function getTG():TG{return (window as any).Telegram?.WebApp}
export function setupTG(){const tg=getTG();if(!tg)return;tg.ready();tg.expand();tg.setHeaderColor('#0b0d12');tg.setBackgroundColor('#0b0d12');tg.enableClosingConfirmation?.();}
export function haptic(type:'light'|'medium'|'success'='light'){const tg=getTG();try{type==='success'?tg?.HapticFeedback?.notificationOccurred('success'):tg?.HapticFeedback?.impactOccurred(type)}catch{}}
