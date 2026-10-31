import GrowingChat from '@/components/growing-chat';
export const metadata={title:'Growing Zeref · not the pin'};
export default function Page(){
 return <main style={{maxWidth:720,margin:'0 auto',padding:'24px 16px'}}>
  <h1>Growing Zeref · not the pin</h1>
  <p>This is Zeref&apos;s always-learning side branch. It trains every 4 hours on its own reading and chat lessons and is saved without a gate, so it can be better or worse than the pinned Zeref. The pinned Zeref on the main page only changes when a round passes the fair check. Each reply shows which growing checkpoint answered.</p>
  <GrowingChat/>
 </main>;
}
