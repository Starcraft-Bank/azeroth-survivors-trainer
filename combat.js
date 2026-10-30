/* Exact-build native combat hooks. No code or save file is patched on disk. */
(() => {
 'use strict';
 globalThis.AZS_TRAINER_COMBAT={setup(api){
  const {base,profile,getSettings,getRun,guarded}=api,p=profile.trainer.combat,f=p.fields;
  const retained=[],listeners=[],stats=new Map();
  const counters={incomingCalls:0,blockedHits:0,modifiedHits:0,xpAwards:0,rapidTicks:0};
  const sameRun=r=>{const current=getRun();return current&&!current.isNull()&&current.equals(r);};
  function replace(name,ret,types,body){
   const address=base.add(p.functions[name]);
   const original=new NativeFunction(address,ret,types);
   const replacement=new NativeCallback((...args)=>body(original,...args),ret,types);
   retained.push(original,replacement);Interceptor.replace(address,replacement);
  }
  // This entry handles both enemy attacks and damaging ground hazards. Skipping
  // it prevents death in the same call, including damage larger than max HP.
  const damageTypes=['pointer','float','uint64','uint32',...(p.playerDamageExtraArgs===2?['uint32','uint32']:[])];
  replace('playerDamage','void',damageTypes,(original,r,damage,attacker,flags,...source)=>{
   counters.incomingCalls++;if(sameRun(r)&&(getSettings().god||globalThis.AZS_MAP_TRAVEL_PROTECTED?.(r))&&damage>0){counters.blockedHits++;return;}
   original(r,damage,attacker,flags,...source);
  });
  // Preserve the native dodge, immunity, kill-credit and reward paths. Large
  // finite damage avoids NaN/Infinity in floating-point damage arithmetic.
  replace('enemyDamage','void',['pointer','uint64','float','uint32','uint32','uint32','uint32'],
   (original,r,guid,damage,a,b,c,d)=>{
    if(sameRun(r)&&Number.isFinite(damage)&&damage>0){
     const s=getSettings();
     if(s.oneHit||s.damageMultiplier!==1){damage=s.oneHit?1e25:Math.min(1e25,damage*s.damageMultiplier);counters.modifiedHits++;}
    }
    original(r,guid,damage,a,b,c,d);
   });
  listeners.push(Interceptor.attach(base.add(p.functions.xpAward),{onEnter(a){guarded(()=>{
   const s=getSettings();if(!s.xp||!sameRun(a[0]))return;
   const current=a[0].add(f.xp).readU32(),amount=a[1].toUInt32();
   const scaled=Math.min(0xffffffff-current,Math.floor(amount*s.xpMultiplier));
   a[1]=ptr(scaled);counters.xpAwards++;
  });}}));
  function clampTimer(address,seconds){const value=address.readFloat();if(Number.isFinite(value)&&value>seconds)address.writeFloat(seconds);}
  function rapid(r,passive=false){
   const s=getSettings();if(!s.rapid||!sameRun(r))return;
   const seconds=s.rapidSeconds;
   if(!passive){clampTimer(r.add(f.baseRemaining),seconds);clampTimer(r.add(f.starterRemaining),seconds);}
   const n=r.add(passive?f.passiveLength:f.skillsLength).readU64().toNumber();
   if(n<0||n>256)throw Error('Unexpected skill count; rapid skills stopped.');
   const data=r.add(passive?f.passivePointer:f.skillsPointer).readPointer(),stride=passive?f.passiveStride:f.skillStride;
   for(let i=0;i<n;i++)clampTimer(data.add(i*stride+f.skillRemaining),seconds);
   counters.rapidTicks++;
  }
  for(const [name,passive] of [['skillTick',false],['passiveSkillTick',true]])listeners.push(Interceptor.attach(base.add(p.functions[name]),{
   onEnter(a){this.run=a[0];guarded(()=>{applyStats(this.run);rapid(this.run,passive);});},
   onLeave(){guarded(()=>rapid(this.run,passive));}
  }));
  // Store each player context separately because native co-op swaps guest
  // state into Run. Recalculation overwrites both stats with fresh base values.
  function applyStats(r,fresh=false){
   if(!sameRun(r))return;
   const key=r.toString()+':'+r.add(f.playerGuid).readU64().toString();
   let state=stats.get(key);if(!state){state={};stats.set(key,state);}
   const s=getSettings();
   for(const [name,multiplier] of [['speed',s.speedMultiplier],['area',s.area?s.areaMultiplier:1]]){
    const addr=r.add(f[name]),value=addr.readFloat(),old=state[name];
    if(!Number.isFinite(value)||value<=0)continue;
    const natural=!fresh&&old&&value===old.applied?old.natural:value;
    const applied=Math.fround(natural*multiplier);
    if(value!==applied)addr.writeFloat(applied);
    state[name]={natural,applied};
   }
  }
  listeners.push(Interceptor.attach(base.add(p.functions.statRecompute),{
   onEnter(a){this.run=a[0];},onLeave(){guarded(()=>applyStats(this.run,true));}
  }));
  return {tick(r){applyStats(r);rapid(r);},status(){return {...counters,areaCoverage:'Native area scaling; fixed ranges and native soft caps remain.'};}};
 }};
})();
