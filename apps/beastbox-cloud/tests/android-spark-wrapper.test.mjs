import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('Android v0.2 wraps the live Spark HTML and current QBEAST controls',()=>{
 const settings=read('../beastbox-android/app/src/main/java/dev/beastbox/device/BeastSettings.kt');
 const bridge=read('../beastbox-android/app/src/main/assets/beastbox-bridge.js');
 const spark=read('public/spark/app.mjs');
 const gradle=read('../beastbox-android/app/build.gradle.kts');
 assert.match(settings,/https:\/\/www\.beastboxcosmos\.xyz\/spark\/index\.html/);
 assert.match(settings,/https:\/\/www\.beastboxcosmos\.xyz\//);
 assert.match(gradle,/versionCode = 2/);
 assert.match(gradle,/versionName = "0\.2\.0-experimental"/);
 assert.match(bridge,/beastbox-companion-session-v1/);
 for(const id of ["care","play","train","talk-text","talk-form"])assert.ok(bridge.includes("'"+id+"'"),id);
 assert.match(spark,/window\.BeastBoxDevice=\{version:2,getState:nativeBridgeState,onCommand:nativeCommand\}/);
 assert.match(spark,/beastbox:session-changed/);
 assert.doesNotMatch(bridge,/OLLAMA_API_KEY|HF_TOKEN|Bearer\s/);
});

test('Android wrapper keeps Bluetooth authority native',()=>{
 const bridge=read('../beastbox-android/app/src/main/assets/beastbox-bridge.js');
 const kotlin=read('../beastbox-android/app/src/main/java/dev/beastbox/device/BeastBridge.kt');
 assert.match(kotlin,/never exposes Bluetooth control to JS/);
 assert.doesNotMatch(bridge,/BluetoothLeAdvertiser|BluetoothGattServer|requestDevice\(/);
 assert.match(bridge,/window\.__beastBoxDevice = \{ receive: receive, report: report, version: 2 \}/);
});
