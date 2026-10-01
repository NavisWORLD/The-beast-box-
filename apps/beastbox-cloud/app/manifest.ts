import type { MetadataRoute } from 'next';
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'BEAST BOX // COSMOS',
    short_name: 'BEAST BOX',
    description: 'Cory Davis / NavisWORLD. Replaceable brains, persistent substrate, owner authority.',
    id: '/',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#080b19',
    theme_color: '#080b19',
    icons: [{ src: '/beast-icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }]
  };
}
