import { BRAND_CREST_SMALL_SVG, BRAND_CREST_SVG, BRAND_NAME } from '../lib/brand';

/**
 * The Cosmic Forge Dragon brand crest. Small sizes use the simplified bold variant so the
 * dragon stays readable at 16–48px. Pass decorative when visible "BEAST BOX" text sits beside it.
 */
export default function BrandCrest({ size = 40, className, decorative = false, style }: { size?: number; className?: string; decorative?: boolean; style?: React.CSSProperties }) {
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={size <= 64 ? BRAND_CREST_SMALL_SVG : BRAND_CREST_SVG} width={size} height={size} className={className} style={{ display: 'inline-block', flex: 'none', ...style }} alt={decorative ? '' : BRAND_NAME} aria-label={decorative ? undefined : BRAND_NAME} aria-hidden={decorative ? true : undefined} decoding="async" draggable={false} data-brand-crest="cosmic-forge-dragon" />;
}
