import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

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
 for(const id of ["care","play","train","talk-text"])assert.ok(bridge.includes("'"+id+"'"),id);
 assert.match(spark,/window\.BeastBoxDevice=\{version:2,getState:nativeBridgeState,onCommand:nativeCommand\}/);
 assert.match(spark,/beastbox:session-changed/);
 assert.doesNotMatch(bridge,/OLLAMA_API_KEY|HF_TOKEN|Bearer\s/);
});

test('Android native messages require a top-level exact HTTPS origin',()=>{
 const activity=read('../beastbox-android/app/src/main/java/dev/beastbox/device/MainActivity.kt');
 assert.match(activity,/WebViewCompat\.addWebMessageListener/);
 assert.match(activity,/WebOrigin\.accepts\(allowedOrigin, sourceOrigin\.toString\(\), isMainFrame\)/);
 assert.match(activity,/window\.location\.origin===/);
 assert.doesNotMatch(activity,/addJavascriptInterface|setOf\("\*"\)/);
});

function bridgeHarness() {
 const events=[], messages=[], hookCommands=[];
 const state={displayName:'Wraith',species:'moth',stage:2,xp:23,bond:46,energy:67};
 const window={BeastBoxNative:{postMessage:value=>messages.push(JSON.parse(value))},
  BeastBoxDevice:{getState:()=>state,onCommand:c=>{hookCommands.push(c);return true;}},
  addEventListener(){},dispatchEvent:e=>{events.push(e);return true;},localStorage:{getItem:()=>null}};
 vm.runInNewContext(read('../beastbox-android/app/src/main/assets/beastbox-bridge.js'),
  {window,document:{getElementById:()=>null},setInterval(){},setTimeout(){},
   Event:class{constructor(type){this.type=type;}},CustomEvent:class{constructor(type,init){this.type=type;Object.assign(this,init);}}});
 return {window,events,messages,hookCommands,state};
}

test('Android reports the actual page state through its message channel',()=>{
 const {messages,state}=bridgeHarness();
 assert.deepEqual(JSON.parse(messages[0].json),state);
 assert.equal(messages[0].kind,'state');
});

test('BLE Talk opens a bounded draft and cannot trigger hidden inference',()=>{
 const {window,events,hookCommands}=bridgeHarness();
 assert.equal(window.__beastBoxDevice.receive(JSON.stringify({command:'talk',text:'x'.repeat(400),source:'test-ble'})),true);
 const open=events.find(event=>event.type==='beastbox:open-chat');
 assert.equal(open.detail.draft.length,120);
 assert.equal(hookCommands.length,0);
 assert.equal(events.some(event=>event.type==='submit'),false);
});

test('Android wrapper keeps Bluetooth authority native',()=>{
 const bridge=read('../beastbox-android/app/src/main/assets/beastbox-bridge.js');
 const kotlin=read('../beastbox-android/app/src/main/java/dev/beastbox/device/BeastBridge.kt');
 assert.match(kotlin,/never exposes Bluetooth control to JS/);
 assert.doesNotMatch(bridge,/BluetoothLeAdvertiser|BluetoothGattServer|requestDevice\(/);
 assert.match(bridge,/window\.__beastBoxDevice = \{ receive: receive, report: report, version: 2 \}/);
});
