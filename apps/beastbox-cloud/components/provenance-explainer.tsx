import {formatGenesisReceipt,formatGrowthReceipt,formatTeacherAttribution} from '../lib/provenance-labels.mjs';

type Props={
 variant:'genesis'|'growth'|'teacher';
 // eslint-disable-next-line @typescript-eslint/no-explicit-any
 data?:any;
 teacher?:{route?:string;model?:string|null;verifiedAt?:string|null};
 defaultOpen?:boolean;
 className?:string;
};

/**
 * Friendly one-liner plus an Advanced <details> field list. Display-only:
 * it renders whatever receipt object it is given and never synthesizes
 * job IDs, counts, or provider claims.
 */
export default function ProvenanceExplainer({variant,data,teacher,defaultOpen=false,className=''}:Props){
 const formatted=variant==='genesis'?formatGenesisReceipt(data||{})
  :variant==='growth'?formatGrowthReceipt(data||{})
  :formatTeacherAttribution(teacher||{});
 const entries=Object.entries(formatted.advanced as Record<string,unknown>)
  .filter(([,value])=>value!==null&&value!==undefined&&value!=='');
 return <div className={'provenance-explainer '+className} data-provenance-explainer={variant}>
  <p className="provenance-friendly">{formatted.friendly}</p>
  <details className="provenance-advanced" open={defaultOpen||undefined}>
   <summary>Advanced details</summary>
   <dl>{entries.map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd><code>{String(value)}</code></dd></div>)}
   {entries.length===0?<div><dt>receipt</dt><dd>none recorded yet</dd></div>:null}</dl>
  </details>
 </div>;
}
