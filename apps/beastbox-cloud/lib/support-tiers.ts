/** Public voluntary-support catalog. No keys, customer data or creature authority.
 * Live Stripe links/prices audited 2026-10-07. Only server-verified payment data
 * may use verifiedSuccessLine; a link click never does.
 */
export type SupportGroup = 'monthly' | 'once';
export type SupportForm = 'spark' | 'keeper' | 'builder' | 'patron' | 'snack' | 'compute' | 'hardware' | 'launch';
export type SupportSound = {
  notes: readonly number[];
  wave: 'sine' | 'triangle';
  duration: number;
  spacing: number;
  bend: number;
};
export type SupportTier = {
  id: string;
  group: SupportGroup;
  kind: 'subscription' | 'one-time';
  name: string;
  priceLabel: string;
  amount: number; // USD cents, not a balance or a game stat
  url: string;
  badge: string;
  subtitle: string;
  description: string;
  cta: string;
  mascot: { form: SupportForm; accent: string; glow: string };
  animation: { reaction: string; particle: string };
  sound: SupportSound;
  interactionLines: readonly string[];
  verifiedSuccessLine: string;
};

export const SUPPORT_PORTALS = {
  sponsors: 'https://github.com/sponsors/NavisWORLD',
  coffee: 'https://buymeacoffee.com/Cosmic_syanpse',
} as const;

export const SUPPORT_TIERS: readonly SupportTier[] = [
  {
    id: 'pocket-spark', group: 'monthly', kind: 'subscription', name: 'Pocket Spark',
    priceLabel: '$5/month', amount: 500,
    url: 'https://buy.stripe.com/3cIbJ27zN7kO8mN97pa7C01', badge: 'SMALL CHAOS',
    subtitle: 'A tiny monthly spark that keeps the beast awake.',
    description: 'A small monthly boost for hosting, experiments, creature evolution, and keeping my weird little machines running.',
    cta: 'Keep the spark alive', mascot: { form: 'spark', accent: '#77e4ff', glow: '#ae91ff' },
    animation: { reaction: 'perk', particle: '✦' },
    sound: { notes: [880, 1174.66, 1567.98], wave: 'sine', duration: 0.1, spacing: 0.055, bend: 1.06 },
    interactionLines: ['oh??? a very small chaos', 'tiny spark sneeze. excuse us.'],
    verifiedSuccessLine: '✨ Monthly spark received. Thank you for supporting the workshop.',
  },
  {
    id: 'beast-keeper', group: 'monthly', kind: 'subscription', name: 'Beast Keeper',
    priceLabel: '$15/month', amount: 1500,
    url: 'https://buy.stripe.com/fZueVe5rF7kO9qR3N5a7C02', badge: 'CREATURE CARE',
    subtitle: 'For the people helping the creature grow teeth.',
    description: 'Supports Beast Box development, creature systems, experiments, game work, testing, and the general madness required to keep this ecosystem evolving.',
    cta: 'Help raise the beast', mascot: { form: 'keeper', accent: '#ffbc86', glow: '#ee839d' },
    animation: { reaction: 'wag', particle: '♥' },
    sound: { notes: [261.63, 392, 523.25], wave: 'triangle', duration: 0.18, spacing: 0.07, bend: 0.96 },
    interactionLines: ['tail wag detected. supervision questionable.', 'tiny magical growl. mostly friendly.'],
    verifiedSuccessLine: '🐉 Support verified. Thank you for helping raise the Beast.',
  },
  {
    id: 'cosmos-builder', group: 'monthly', kind: 'subscription', name: 'COSMOS Builder',
    priceLabel: '$50/month', amount: 5000,
    url: 'https://buy.stripe.com/3cI28s2ft7kO6eF0ATa7C03', badge: 'LAB FUEL',
    subtitle: 'Fuel for the actual construction of the weird little universe.',
    description: 'Helps fund compute, hosting, storage, simulations, hardware ideas, and engineering time connecting Beast Box, COSMOS, CST, Lost COSMOS, and Synapse OS.',
    cta: 'Build the universe', mascot: { form: 'builder', accent: '#76edd4', glow: '#739eff' },
    animation: { reaction: 'signal', particle: '·' },
    sound: { notes: [349.23, 523.25, 698.46, 1046.5], wave: 'sine', duration: 0.22, spacing: 0.055, bend: 1.02 },
    interactionLines: ['blueprint awake. please ignore the prototype goblins.', 'systems thinking. small creature edition.'],
    verifiedSuccessLine: '⚛️ Support verified. The workshop just got weirder.',
  },
  {
    id: 'universe-patron', group: 'monthly', kind: 'subscription', name: 'Universe Patron',
    priceLabel: '$150/month', amount: 15000,
    url: 'https://buy.stripe.com/6oU00kaLZax0eLb5Vda7C04', badge: 'BIG STARDUST',
    subtitle: 'For the people funding the larger dream, not just the current page.',
    description: 'High-level support for infrastructure, hardware, prototypes, research, compute, games, documentation, and pushing the NavisWORLD universe forward.',
    cta: 'Patron the universe', mascot: { form: 'patron', accent: '#f4dba3', glow: '#bf9ffa' },
    animation: { reaction: 'bloom', particle: '✧' },
    sound: { notes: [196, 293.66, 587.33, 1174.66], wave: 'sine', duration: 0.35, spacing: 0.09, bend: 1.005 },
    interactionLines: ['the universe nodded. politely.', 'celestial awakening. still mildly supervised.'],
    verifiedSuccessLine: '🌌 Cosmic patronage verified. Thank you for supporting the larger dream.',
  },
  {
    id: 'feed-the-beast', group: 'once', kind: 'one-time', name: 'Feed the Beast',
    priceLabel: '$10 once', amount: 1000,
    url: 'https://donate.stripe.com/cNiaEY4nBcF87iJ1EXa7C05', badge: 'SIMULATION SNACK',
    subtitle: 'Quick snack. Immediate morale improvement.',
    description: 'A one-time snack for the workshop: hosting, experiments, storage, and keeping the project moving. The munch is a cosmetic reaction.',
    cta: 'Feed the beast', mascot: { form: 'snack', accent: '#eea1cc', glow: '#b5a3ff' },
    animation: { reaction: 'munch', particle: '♥' },
    sound: { notes: [440, 330, 660], wave: 'triangle', duration: 0.07, spacing: 0.075, bend: 0.82 },
    interactionLines: ['munch. cosmetic crumbs everywhere.', 'that button looks suspiciously edible.'],
    verifiedSuccessLine: '☄️ Support verified. Thank you for feeding the workshop.',
  },
  {
    id: 'compute-burst', group: 'once', kind: 'one-time', name: 'Compute Burst',
    priceLabel: '$50 once', amount: 5000,
    url: 'https://donate.stripe.com/3cI8wQ8DRbB446x5Vda7C06', badge: 'COMPUTE FUEL',
    subtitle: 'A battery injection for the workshop.',
    description: 'A one-time boost for model runs, simulations, infrastructure, hosting spikes, storage, and experiments.',
    cta: 'Charge the machine', mascot: { form: 'compute', accent: '#92e6ff', glow: '#759bff' },
    animation: { reaction: 'charge', particle: 'ϟ' },
    sound: { notes: [164.81, 329.63, 659.25, 1318.51], wave: 'triangle', duration: 0.12, spacing: 0.04, bend: 1.22 },
    interactionLines: ['battery wiggle. no actual overclocking occurred.', 'workshop status: gently humming.'],
    verifiedSuccessLine: '⚡ Compute support verified. Thank you for charging the workshop.',
  },
  {
    id: 'hardware-rune', group: 'once', kind: 'one-time', name: 'Hardware Rune',
    priceLabel: '$100 once', amount: 10000,
    url: 'https://donate.stripe.com/4gM00kdYb5cG8mN0ATa7C07', badge: 'HARDWARE RITUAL',
    subtitle: 'For the physical body and prototype goblins.',
    description: 'Supports prototype hardware, local AI rigs, portable experiments, testing equipment, and the physical side of Beast Box and Synapse OS.',
    cta: 'Forge the next body', mascot: { form: 'hardware', accent: '#f7c78c', glow: '#81c7d1' },
    animation: { reaction: 'forge', particle: '⌁' },
    sound: { notes: [698.46, 1046.5, 523.25], wave: 'sine', duration: 0.12, spacing: 0.08, bend: 0.99 },
    interactionLines: ['prototype goblins are pleased. do not lick the chip.', 'goggles on. questionable ideas ready.'],
    verifiedSuccessLine: '🛠️ Hardware support verified. Prototype goblins say thank you.',
  },
  {
    id: 'launch-fuel', group: 'once', kind: 'one-time', name: 'Launch Fuel',
    priceLabel: '$500 once', amount: 50000,
    url: 'https://donate.stripe.com/fZu7sM4nB20u0UlfvNa7C08', badge: 'MILDLY UNHOLY',
    subtitle: 'A major push toward the next absurd milestone.',
    description: 'A major contribution toward infrastructure, hardware, compute, prototype builds, documentation, testing, and shipping larger NavisWORLD milestones.',
    cta: 'Push the universe forward', mascot: { form: 'launch', accent: '#ffb68c', glow: '#de9bfa' },
    animation: { reaction: 'ignition', particle: '✦' },
    sound: { notes: [98, 196, 392, 784], wave: 'triangle', duration: 0.27, spacing: 0.065, bend: 1.18 },
    interactionLines: ['ignition rehearsal. the floor is probably fine.', 'something mildly unholy is on the drawing board.'],
    verifiedSuccessLine: '🚀 Launch support verified. Thank you for helping push the next milestone.',
  },
];
