import type { Metadata, Viewport } from 'next';
import './globals.css';
import { BRAND_CREST_SMALL_SVG, BRAND_ICONS } from '../lib/brand';
import CompanionProvider from '../components/companion-provider';
import SiteSoundDock from '../components/site-sound-dock';
export const metadata: Metadata = { title: 'BEAST BOX // COSMIC CHAOS', description: 'Swap the brain. Keep the story. A cosmic workstation by Cory Davis.', robots: { index: false, follow: false }, manifest: '/manifest.webmanifest', icons: { icon: [{ url: BRAND_ICONS.favicon, sizes: '48x48' }, { url: BRAND_CREST_SMALL_SVG, type: 'image/svg+xml', sizes: 'any' }, { url: BRAND_ICONS.png32, type: 'image/png', sizes: '32x32' }, { url: BRAND_ICONS.png16, type: 'image/png', sizes: '16x16' }], apple: [{ url: BRAND_ICONS.apple180, sizes: '180x180', type: 'image/png' }] }, appleWebApp: { capable: true, title: 'BEAST BOX', statusBarStyle: 'black-translucent' } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b19' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><CompanionProvider>{children}</CompanionProvider><SiteSoundDock/></body></html>; }
