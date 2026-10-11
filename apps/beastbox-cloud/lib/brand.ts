// One brand crest for every Beast Box surface: the owner-supplied Cosmic Forge Dragon.
// Bump BRAND_ICON_VERSION when the crest files change so browsers, iOS and PWAs refetch them.
export const BRAND_ICON_VERSION = '20261011';
export const BRAND_NAME = 'Beast Box';
const v = (path: string) => `${path}?v=${BRAND_ICON_VERSION}`;
/** Full crest (orbit ring, wing, forge crystal). Use at 64px and up. */
export const BRAND_CREST_SVG = v('/brand/cosmic-forge-dragon.svg');
/** Simplified bold crest for 16–48px (favicon, header marks, footers). */
export const BRAND_CREST_SMALL_SVG = v('/brand/cosmic-forge-dragon-small.svg');
export const BRAND_ICONS = {
  favicon: v('/favicon.ico'),
  png16: v('/brand/cosmic-forge-dragon-16.png'),
  png32: v('/brand/cosmic-forge-dragon-32.png'),
  png192: v('/brand/cosmic-forge-dragon-192.png'),
  png512: v('/brand/cosmic-forge-dragon-512.png'),
  maskable192: v('/brand/cosmic-forge-dragon-maskable-192.png'),
  maskable512: v('/brand/cosmic-forge-dragon-maskable-512.png'),
  apple180: v('/apple-touch-icon.png'),
};
