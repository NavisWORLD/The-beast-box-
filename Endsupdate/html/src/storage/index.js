export class BrowserStorageAdapter{
  constructor({dbName='beastbox-web-v1',storeName='state'}={}){this.dbName=dbName;this.storeName=storeName}
  async db(){return new Promise((resolve,reject)=>{const r=indexedDB.open(this.dbName,1);r.onupgradeneeded=()=>r.result.createObjectStore(this.storeName);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
  async put(key,value){const db=await this.db();return new Promise((resolve,reject)=>{const t=db.transaction(this.storeName,'readwrite');t.objectStore(this.storeName).put(value,key);t.oncomplete=()=>{db.close();resolve()};t.onerror=()=>{db.close();reject(t.error)}})}
  async get(key){const db=await this.db();return new Promise((resolve,reject)=>{const r=db.transaction(this.storeName).objectStore(this.storeName).get(key);r.onsuccess=()=>{db.close();resolve(r.result)};r.onerror=()=>{db.close();reject(r.error)}})}
  async clear(){const db=await this.db();return new Promise((resolve,reject)=>{const t=db.transaction(this.storeName,'readwrite');t.objectStore(this.storeName).clear();t.oncomplete=()=>{db.close();resolve()};t.onerror=()=>{db.close();reject(t.error)}})}
}
export const LOCAL_ONLY_FIELDS=Object.freeze(['modelMetadata','uiPreferences','apiBase']);
