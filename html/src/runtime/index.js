import {chooseExecutionPath} from '../capabilities/index.js';
export class RuntimeAdapter{
  constructor({capabilities,providers}){this.capabilities=capabilities;this.providers=providers}
  plan(preference='auto'){return chooseExecutionPath(this.capabilities,preference)}
  async respond(input,{preference='auto',providerId}={}){const path=this.plan(preference);const id=providerId||(path==='reference'?'reference':path.startsWith('local')?'local':path==='remote'?'remote':'reference');const provider=this.providers.get(id);if(!provider)throw new Error(`No provider registered for execution path ${id}`);return provider.respond(input,{path,capabilities:this.capabilities})}
}
