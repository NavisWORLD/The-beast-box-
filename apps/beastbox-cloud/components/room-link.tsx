import Link from 'next/link';
import type { ComponentProps } from 'react';

/**
 * Next <Link> for app routes; a plain <a> for static files such as
 * /spark/index.html. Linking a static .html page with <Link> makes Next
 * request an RSC payload that 404s (console error) before falling back.
 */
type Props = Omit<ComponentProps<typeof Link>, 'href'> & { href: string };
export default function RoomLink({ href, prefetch, children, ...rest }: Props) {
  if (/\.html(?:[?#]|$)/.test(href)) return <a href={href} {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}>{children}</a>;
  return <Link href={href} prefetch={prefetch} {...rest}>{children}</Link>;
}
