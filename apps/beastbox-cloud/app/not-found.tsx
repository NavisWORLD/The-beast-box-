import Link from 'next/link';
// A plain 404: no quick dock or "Talk to {beast}" launcher on a page that does not exist (the dock is hidden by CSS while
// [data-not-found] is on the page). Nothing else changes: the site menu and honesty line still render from the layout.
export const metadata={title:'Page not found · Beast Box'};
export default function NotFound(){
 return <main data-not-found style={{minHeight:'60vh',display:'grid',placeContent:'center',textAlign:'center',gap:12,padding:24}}>
  <h1 style={{fontSize:28,margin:0}}>This corner of the universe isn’t here.</h1>
  <p style={{margin:0,opacity:.8}}>The link may be old. Let’s get you home.</p>
  <p style={{margin:0,display:'flex',gap:16,justifyContent:'center',flexWrap:'wrap'}}><Link href="/">Home</Link><Link href="/beast-cage">Beast Cage</Link><Link href="/universe">Tiny Universe</Link></p>
 </main>;
}
