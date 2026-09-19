export class BeastBoxClient{
  constructor({baseUrl='',fetchImpl=globalThis.fetch}={}){this.baseUrl=baseUrl.replace(/\/$/,'');this.fetch=fetchImpl}
  url(path){return `${this.baseUrl}${path}`}
  async request(path,{method='GET',body,headers={}}={}){const h={'Accept':'application/json',...headers};if(body!==undefined)h['Content-Type']='application/json';const r=await this.fetch(this.url(path),{method,headers:h,body:body===undefined?undefined:JSON.stringify(body)});let data={};try{data=await r.json()}catch{}if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}
  get(path){return this.request(path)} post(path,body){return this.request(path,{method:'POST',body})}
}
