/**
 * Browser-only, owner-gesture image classification. It yields a short, unverified
 * ImageNet CATEGORY, not scene understanding. The image never enters the API
 * request; only the owner-approved textual observation can be staged as context.
 * MediaPipe/WASM/model are downloaded on first use and may expose usage telemetry.
 */
import {loadVision,visionReading} from './vision-classifier';

export async function classifyLocalPhoto(file:File,objectUrl:string){
 if(!/^(image\/(png|jpeg|webp))$/.test(file.type)||file.size<=0||file.size>10*1024*1024)
  throw new Error('Choose a PNG, JPEG or WebP image of 10 MB or less.');
 if(!objectUrl.startsWith('blob:'))
  throw new Error('Only already-staged local images can be classified.');
 const image=new Image();
 image.src=objectUrl;
 // Decode the owner's locally staged file rather than ever fetching a remote URL.
 try{await image.decode();}
 catch{throw new Error('Your browser could not decode this image; no image was sent.');}
 const classifier=await loadVision();
 const reading=visionReading(classifier.classify(image));
 return reading;
}
