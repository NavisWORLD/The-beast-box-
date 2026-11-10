import type { Metadata, Viewport } from 'next';
import HonestLine from '../components/honest-line';
import './globals.css';
import { BRAND_CREST_SMALL_SVG, BRAND_ICONS } from '../lib/brand';
import CompanionProvider from '../components/companion-provider';
import SiteSoundDock from '../components/site-sound-dock';
import ZerefVoiceDock from '../components/zeref-voice-dock';
import SiteDock from '../components/site-dock';
import SiteNav from '../components/site-nav';
import ShareWorld from '../components/share-world';
import SensoriumProvider from '../components/sensorium-provider';
import OneWorldProvider from '../components/one-world-provider';
import GlDebugOverlay from '../components/gl-debug-overlay';
import {isOwner} from '../lib/security';
export const metadata: Metadata = { title: 'Beast Box', description: 'Swap the brain. Keep the story. A cosmic workstation by Cory Davis.', robots: { index: false, follow: false }, manifest: '/manifest.webmanifest', icons: { icon: [{ url: BRAND_ICONS.favicon, sizes: '48x48' }, { url: BRAND_CREST_SMALL_SVG, type: 'image/svg+xml', sizes: 'any' }, { url: BRAND_ICONS.png32, type: 'image/png', sizes: '32x32' }, { url: BRAND_ICONS.png16, type: 'image/png', sizes: '16x16' }], apple: [{ url: BRAND_ICONS.apple180, sizes: '180x180', type: 'image/png' }] }, appleWebApp: { capable: true, title: 'BEAST BOX', statusBarStyle: 'black-translucent' } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b19', viewportFit:'cover' };
export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Public and guest pages never mount the sensorium, so they never call its route.
  // The flag is read here by name. Unset or blank is on. The off switch is the exact value off.
  const livedFlag = process.env.BEASTBOX_LIVED_BACKBONE;
  const livedOn = livedFlag == null || livedFlag.trim() === '' || livedFlag === 'on';
  const sensorium = livedOn && await isOwner();
  return <html lang="en"><body><OneWorldProvider/><SiteNav/><CompanionProvider>{children}</CompanionProvider><HonestLine/><SiteSoundDock/><ZerefVoiceDock/><SiteDock/><ShareWorld/>{sensorium ? <SensoriumProvider enabled /> : null}<GlDebugOverlay/></body></html>;
}
