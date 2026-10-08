import type { Metadata, Viewport } from 'next';
import './globals.css';
import CompanionProvider from '../components/companion-provider';
import SiteSoundDock from '../components/site-sound-dock';
export const metadata: Metadata = { title: 'BEAST BOX // COSMIC CHAOS', description: 'Swap the brain. Keep the story. A cosmic workstation by Cory Davis.', robots: { index: false, follow: false }, manifest: '/manifest.webmanifest', icons: { icon: '/beast-icon.svg', apple: '/apple-icon' }, appleWebApp: { capable: true, title: 'BEAST BOX', statusBarStyle: 'black-translucent' } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b19' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><CompanionProvider>{children}<SiteSoundDock/></CompanionProvider></body></html>; }
