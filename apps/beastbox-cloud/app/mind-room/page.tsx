import {ZerefMindRoom} from '@/components/zeref-mind-room';
import {ZerefSparkPulse} from '@/components/zeref-spark-pulse';
export const metadata={title:"Zeref's Mind Room"};
export default function MindRoomPage(){
 return <main style={{padding:12,maxWidth:900,margin:'0 auto'}}>
  <h1 style={{fontSize:22}}>🧠 Zeref&apos;s Mind Room</h1>
  <ZerefSparkPulse/>
  <ZerefMindRoom/>
  <p style={{fontSize:12}}>Fed by <a href="/loop">his scheduled read-only reader</a>. JSON: <a href="/zeref-chooses/mind-room.json">/zeref-chooses/mind-room.json</a> · Spark pulse (RECORDED): <a href="/api/zeref/spark-pulse">/api/zeref/spark-pulse</a></p>
 </main>;
}
