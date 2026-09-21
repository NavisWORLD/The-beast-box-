/** Browser-only ImageNet classifier. Lazy-loaded after owner clicks Start vision.
 * No frames are uploaded to Beast Box or the model host. MediaPipe may transmit
 * anonymized product telemetry; the model/WASM assets are downloaded on demand.
 */
import type {ImageClassifier} from '@mediapipe/tasks-vision';
export const VISION_ENGINE='EfficientNet-Lite0/ImageNet (MediaPipe 0.10.17)';
export const VISION_MODEL='https://storage.googleapis.com/mediapipe-models/image_classifier/efficientnet_lite0/float32/1/efficientnet_lite0.tflite';
const WASM='https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm';
let pending:Promise<ImageClassifier>|null=null;
export function loadVision():Promise<ImageClassifier>{
 if(!pending){
  pending=(async()=>{
   const {FilesetResolver,ImageClassifier}=await import('@mediapipe/tasks-vision');
   const files=await FilesetResolver.forVisionTasks(WASM);
   return ImageClassifier.createFromOptions(files,{baseOptions:{modelAssetPath:VISION_MODEL},
    runningMode:'IMAGE',maxResults:1,scoreThreshold:0.32});
  })().catch(e=>{pending=null;throw e;});
 }
 return pending;
}
export type VisionReading={source:'camera_classifier';text:string;timestamp:string;confidence:number};
export function visionReading(result:ReturnType<ImageClassifier['classify']>,at=new Date()):VisionReading|null{
 const cat=result.classifications?.[0]?.categories?.[0];
 const raw=cat?.displayName||cat?.categoryName;
 const score=cat?.score;
 if(typeof raw!=='string'||typeof score!=='number'||!Number.isFinite(score)||score<0.32||score>1)return null;
 const text=raw.trim().replace(/[^\p{L}\p{N} ,.'()/-]/gu,' ').slice(0,96).trim();
 if(!text)return null;
 return {source:'camera_classifier',text,timestamp:at.toISOString(),confidence:Math.round(score*1000)/1000};
}
