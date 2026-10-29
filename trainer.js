/* Native host/solo trainer orchestrator. No Mayhem waves or balance changes. */
(() => {
 'use strict';
 const profile=globalThis.AZS_PROFILE,base=Process.mainModule.base;
 const F=o=>profile.fieldOffsets?.['0x'+o.toString(16)]??o,E=o=>profile.enemyOffsets?.['0x'+o.toString(16)]??o;
 const schema=globalThis.AZS_SCHEMA,defaults=Object.fromEntries(Object.entries(schema).map(([k,v])=>[k,v[0]]));
 let settings={...defaults,...globalThis.AZS_SETTINGS},run=null,game=null,fault='',lastNotice='',seq=0,queue=[],results=[],lastReport=0,modules={};
 function notice(text){lastNotice=String(text);send({kind:'notice',text:lastNotice});}
 function disable(){settings={...defaults,bossId:settings.bossId};queue=[];}
 function guarded(fn){try{return fn();}catch(e){
  const first=!fault;fault=String(e.stack||e);disable();
  // Hooks still execute after a module fault. Disable their settings first,
  // then make one bounded attempt to restore reversible combat stats.
  if(first&&run){try{modules.combat?.tick?.(run);}catch(restoreError){/* The original fault remains the diagnostic. */}}
  send({kind:'fault',error:fault});return null;
 }}
 function valid(v){return v&&Object.keys(v).length===Object.keys(schema).length&&Object.entries(schema).every(([k,[d,lo,hi]])=>typeof d==='boolean'?typeof v[k]==='boolean':typeof v[k]==='number'&&Number.isFinite(v[k])&&v[k]>=lo&&v[k]<=hi&&(k!=='bossId'||Number.isInteger(v[k])));}
 const api={profile,base,F,E,getSettings:()=>settings,getRun:()=>run,guarded,notice};
 const travel=AZS_MAP_TRAVEL.setup({profile,base,F,getRun:()=>run,getGame:()=>game,notice,externalDamageGuard:true});
 modules={combat:AZS_TRAINER_COMBAT.setup(api),economy:AZS_TRAINER_ECONOMY.setup(api),actions:AZS_TRAINER_ACTIONS.setup(api)};
 function match(){if(!run||run.isNull())return null;
  return {phase:run.add(F(0xca2)).readU8(),worldPhase:run.add(F(0xca3)).readU8(),coop:!!run.add(F(0xc9d)).readU8(),
   clock:run.add(F(0xbf4)).readFloat(),hp:run.add(F(0x508)).readFloat(),maxHp:run.add(F(0x4a0)).readFloat(),
   gold:run.add(F(0x510)).readU32(),level:run.add(F(0x500)).readU32(),endless:!!run.add(F(0xc90)).readU8()};}
 function status(){return {ready:!fault,fault,settings:{...settings},match:guarded(match),notice:lastNotice,travel:travel.status(),
  results:results.slice(-10),modules:Object.fromEntries(Object.entries(modules).map(([k,m])=>[k,m.status?.()??{}]))};}
 function drain(){
  for(const item of queue.splice(0,4)){
   let result;try{result=modules.actions.command(item.name,item.args);if(result===false)throw Error('Action is not available in this match.');}
   catch(e){result={ok:false,error:String(e.message||e)};notice(result.error);}
   results.push({id:item.id,name:item.name,result});if(results.length>20)results.shift();
  }
 }
 Interceptor.attach(base.add(profile.functions.gameUpdate),{onEnter(a){game=a[0];},onLeave(){guarded(()=>{
  run=game.add(16).readU64().toString()==='2'?null:game.add(16);if(!run)travel.reset(true);
  // Native level-up menus may pause runTick. Refresh cached economy UI and
  // service explicit actions on this same game thread while choosing a card.
  if(run&&!fault&&run.add(F(0xca2)).readU8()===2){modules.economy.tick?.(run);drain();}
  if(Date.now()-lastReport>300){lastReport=Date.now();send({kind:'status',...status()});}
 });}});
 Interceptor.attach(base.add(profile.functions.runTick),{onEnter(a){guarded(()=>{
  run=a[0];if(fault)return;travel.tick(run);const phase=run.add(F(0xca2)).readU8();
  if(phase!==1&&phase!==2){if(queue.length){queue=[];notice('Start a live match before using match actions.');}return;}
  if(travel.status().busy)return;
  for(const module of Object.values(modules))module.tick?.(run);
  drain();
 });}});
 rpc.exports={status,travel(zone){if(fault)return false;return travel.request(zone);},catalog:()=>modules.actions.catalog(),configure(v){if(!valid(v))return false;
   if(fault&&Object.keys(defaults).some(k=>k!=='bossId'&&v[k]!==defaults[k]))return false;
   settings={...v};return true;},
  action(name,args={}){if(typeof name!=='string'||!args||typeof args!=='object'||Array.isArray(args)||queue.length>=8||fault)return false;
   const m=guarded(match);if(!m||![1,2].includes(m.phase))return false;const id=++seq;queue.push({id,name,args});return id;},reset(){disable();return true;}};
 send({kind:'ready',version:profile.version});
})();
