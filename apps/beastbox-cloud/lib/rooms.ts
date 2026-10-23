// One shared list of the seven Beast Box rooms so every header offers the
// same journey. Labels stay plain; the emoji is decorative (aria-hidden).
export type Room = { key: string; label: string; href: string; icon: string };
export const ROOMS: readonly Room[] = [
  { key: 'home', label: 'Home', href: '/', icon: '🏠' },
  { key: 'beast', label: 'My Beast', href: '/spark/index.html', icon: '🐣' },
  { key: 'cage', label: 'Beast Cage', href: '/beast-cage', icon: '🏰' },
  { key: 'talk', label: 'Talk to your beast', href: '/beast-cage/talk?with=beast', icon: '💬' },
  { key: 'game', label: 'Lost COSMOS', href: '/sol-game', icon: '🎮' },
  { key: 'brain', label: 'Brain Bay', href: '/brain-bay', icon: '🧠' },
  { key: 'lab', label: 'Research Lab', href: '/research', icon: '🔬' },
  { key: 'settings', label: 'Settings', href: '/settings', icon: '⚙️' },
];
