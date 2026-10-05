import {buildGenome} from './genome.mjs';

export const CORE_RECIPES=[
 {body:'pup',traits:{focus:0,calm:0,spark:100},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'fox',traits:{focus:0,calm:100,spark:0},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'sprout',traits:{focus:0,calm:40,spark:80},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'moth',traits:{focus:0,calm:0,spark:40},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'axolotl',traits:{focus:0,calm:40,spark:60},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'golem',traits:{focus:0,calm:0,spark:60},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'dragonling',traits:{focus:0,calm:0,spark:0},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'bird',traits:{focus:0,calm:20,spark:20},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'fish',traits:{focus:0,calm:40,spark:0},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'serpent',traits:{focus:0,calm:0,spark:80},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
 {body:'biped',traits:{focus:0,calm:40,spark:100},run:'ibm_marrakesh:d93d8pgoamcc73dc3afg'},
];
export const CHARLET={body:'dragonling',traits:{focus:40,calm:0,spark:40},run:'ibm_fez:d6lmid0bfi7c73a2lae0'};
export const RARE_KEYS=[
 'ibm_kingston:da5qu843jnrc73ahka2g#pub0','ibm_kingston:da5qu843jnrc73ahka2g#pub1',
 'ibm_kingston:da5quo6aa69c739l6jl0#pub0','ibm_kingston:da5quo6aa69c739l6jl0#pub1',
 'ibm_kingston:da5qv8maa69c739l6k3g#pub0','ibm_kingston:da5qv8maa69c739l6k3g#pub1',
 'ibm_marrakesh:da5qvqs3jnrc73ahkbj0#pub0','ibm_marrakesh:da5qvqs3jnrc73ahkbj0#pub1',
 'ibm_marrakesh:da5r0c3otlns739c8h10#pub0','ibm_marrakesh:da5r0c3otlns739c8h10#pub1',
 'ibm_marrakesh:da5r0ts3jnrc73ahkck0#pub0','ibm_marrakesh:da5r0ts3jnrc73ahkck0#pub1'
];

function form(entry,run,stage,rare=false,label=''){
 const gen=buildGenome(entry.traits,run,null,10);
 return {entry,gen,stage,name:gen.names[stage],body:gen.body,island:gen.island,rare,label};
}
export function catalogForms(byKey){
 const forms=[];
 for(const recipe of CORE_RECIPES){
  const run=byKey.get(recipe.run);if(!run)continue;
  const entry={traits:recipe.traits,run:recipe.run,user:null};
  for(const stage of [1,2,3])forms.push(form(entry,run,stage,false,recipe.body));
 }
 const charRun=byKey.get(CHARLET.run);
 if(charRun){const entry={traits:CHARLET.traits,run:CHARLET.run,user:null};for(const stage of [1,2,3]){const row=form(entry,charRun,stage,false,'Charlet line');if(stage===1)row.name='Charlet';forms.push(row);}}
 for(const key of RARE_KEYS){
  const run=byKey.get(key);if(!run)continue;
  const entry={traits:{focus:40,calm:40,spark:40},run:key,user:null};
  for(const stage of [1])forms.push(form(entry,run,stage,true,'rare recorded form'));
 }
 return forms;
}
