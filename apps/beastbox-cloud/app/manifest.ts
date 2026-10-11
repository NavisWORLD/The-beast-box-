import type { MetadataRoute } from 'next';
import { BRAND_CREST_SVG, BRAND_ICONS } from '../lib/brand';
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
    icons: [
      { src: BRAND_ICONS.png192, sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: BRAND_ICONS.png512, sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: BRAND_ICONS.maskable192, sizes: '192x192', type: 'image/png', purpose: 'maskable' },
      { src: BRAND_ICONS.maskable512, sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      { src: BRAND_CREST_SVG, sizes: 'any', type: 'image/svg+xml', purpose: 'any' }
    ]
  };
}
