import type { Metadata, Viewport } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'BEAST BOX // COSMIC CHAOS', description: 'Swap the brain. Keep the story. A cosmic workstation by Cory Davis.', robots: { index: false, follow: false } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b19' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
