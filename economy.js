/* Version-reviewed native economy hooks. All switches default off in settings. */
(() => {
 'use strict';
 globalThis.AZS_TRAINER_ECONOMY={setup(api){
  const {profile,base,F,getSettings,getRun,guarded}=api,p=profile.trainer.economy,MAX=0xffffffff;
  const counts={goldAwards:0,freeRerolls:0,freeChests:0,banishes:0,legendaryCards:0,legendaryGear:0,uiRefreshes:0};
  const zero=Memory.alloc(4);zero.writeU32(0);
  const bases=new Set(p.generatedGearBases);
  const native=(r,ret,args)=>new NativeFunction(base.add(r),ret,args,{traps:'all'});
  const serialize=native(p.choiceSerializer,'void',['pointer','pointer','pointer','uint64']);
  const reserve=native(profile.functions.reserveUi,'void',['pointer']);
  const allocate=native(profile.functions.allocate,'pointer',['uint64','uint64']),deallocate=native(profile.functions.deallocate,'void',['pointer','uint64','uint64']);
  const settings=()=>getSettings(),active=()=>{const r=getRun();return r&&!r.isNull()&&[1,2].includes(r.add(p.phaseOffset).readU8());};
  const freeR=()=>active()&&(settings().gold||settings().freeRerolls);
  const freeC=()=>active()&&(settings().gold||settings().freeChests);
  const unlimitedB=()=>active()&&settings().unlimitedBanish;
  const hook=(r,fn)=>Interceptor.attach(base.add(r),function(){const c=this.context;guarded(()=>fn(c));});
  let previous='',owner='',refreshPending=false;
  // Saturating pickup arithmetic remains necessary after max gold is switched off.
  // It changes nothing until a uint32 addition would actually overflow.
  for(const s of p.goldSites)hook(s.rva,c=>{
   if(!active())return;const r=c[s.runRegister];if(settings().gold)r.add(p.goldOffset).writeU32(MAX);
   const amount=c[s.amountRegister].toUInt32(),gold=r.add(p.goldOffset).readU32(),earned=r.add(p.earnedGoldOffset).readU32();
   c[s.amountRegister]=ptr(Math.min(amount,MAX-gold,MAX-earned));counts.goldAwards++;
  });
  for(const s of p.copperSites)hook(s.rva,c=>{
   if(!active())return;const gold=c[s.runRegister].add(p.goldOffset).readU32();c.r8=ptr(Math.min(MAX,gold*10000));
  });
  for(const s of p.costSites)hook(s.rva,c=>{
   if(!freeR())return;c[s.costRegister]=ptr(0);c[s.overflowRegister]=c[s.overflowRegister].and(ptr('0xfffffffffffffffe'));counts.freeRerolls++;
  });
  hook(p.freeRerollStore,c=>{if(freeR())c.rax=ptr(c.rcx.add(p.freeRerollsOffset).readU32());});
  // Give the native chest affordability check a temporary budget. Its original
  // price still drives the next chest's price; only the deduction is refunded.
  const chestStack=[];
  Interceptor.attach(base.add(p.chest),{
   onEnter(a){guarded(()=>{this.free=freeC();this.r=a[0];if(!this.free)return;
    this.gold=this.r.add(p.goldOffset).readU32();chestStack.push(this);this.r.add(p.goldOffset).writeU32(MAX);
   });},
   onLeave(){guarded(()=>{if(!this.free)return;this.r.add(p.goldOffset).writeU32(settings().gold?MAX:this.gold);chestStack.pop();counts.freeChests++;});}
  });
  hook(p.chestStore,c=>{const t=chestStack[chestStack.length-1];if(t&&c.rsi.equals(t.r))c.rax=ptr(settings().gold?MAX:t.gold);});
  hook(p.chestHud,c=>{if(freeC())c.rax=zero;});
  hook(p.chestJson,c=>{if(freeC())c.rax=ptr(0);});
  // The native banish list/selection rules remain intact. Only allowance is
  // bypassed, and the stored legitimate balance is never spent or inflated.
  hook(p.banishGate,c=>{if(unlimitedB()&&c.rdi.toUInt32()===0)c.rdi=ptr(1);});
  hook(p.banishStore,c=>{if(unlimitedB()){c.rdi=ptr(c.rsi.add(p.banishOffset).readU32());counts.banishes++;}});
  hook(p.banishUi,c=>{if(unlimitedB())c.r13=ptr(9999);});
  Interceptor.attach(base.add(p.card),{onEnter(a){guarded(()=>{
   if(!active()||!settings().legendary||a[2].readU64().toString(16)==='8000000000000004')return;
   a[3]=ptr(4);counts.legendaryCards++;
  });}});
  hook(p.generatedGear,c=>{
   if(!active()||!settings().legendary)return;const id=c[p.generatedGearRegister].toUInt32(),delta=id-100000;
   if(delta<0||delta>11999||delta%10!==0)return;
   const tier=Math.floor(delta/10)%10,bare=id-id%10,promoted=id-tier*10+40;
   if(tier<7&&bases.has(bare)&&bases.has(promoted-promoted%10)){c[p.generatedGearRegister]=ptr(promoted);counts.legendaryGear++;}
  });
  function refresh(r){
   const type=r.add(p.offerTypeOffset).readU8();if(r.add(p.phaseOffset).readU8()!==2||type>2)return;
   const result=Memory.alloc(24),length=base.add(p.choiceTypeLengths+type*8).readU64(),name=base.add(p.choiceTypePointers+type*8).readPointer();
   // Frida suppresses re-entrant hooks inside tick. Supply temporary native
   // allowances for this serialization only, then restore the player's budget.
   const oldFree=r.add(p.freeRerollsOffset).readU32(),oldBanish=r.add(p.banishOffset).readU32();
   try{if(freeR())r.add(p.freeRerollsOffset).writeU32(1);if(unlimitedB())r.add(p.banishOffset).writeU32(9999);serialize(result,r,name,length);}
   finally{r.add(p.freeRerollsOffset).writeU32(oldFree);r.add(p.banishOffset).writeU32(oldBanish);}
   if(freeR()){
    const data=result.add(8).readPointer(),size=result.add(16).readU64().toNumber(),cap=result.readU64().toNumber();
    const object=JSON.parse(data.readUtf8String(size));object.rerolls=oldFree;object.rerollCost=0;
    const text=JSON.stringify(object),bytes=unescape(encodeURIComponent(text)).length;
    let target=data;
    if(bytes+1>cap){target=allocate(bytes+1,1);if(target.isNull())throw Error('Cannot refresh native offer');deallocate(data,cap,1);result.writeU64(bytes+1);result.add(8).writePointer(target);}
    target.writeUtf8String(text);result.add(16).writeU64(bytes);
   }
   const v=r.add(p.uiVectorOffset),n=v.add(16).readU64().toNumber(),cap=v.readU64().toNumber();
   if(n>=cap)reserve(v);
   Memory.copy(v.add(8).readPointer().add(n*24),result,24);v.add(16).writeU64(n+1);counts.uiRefreshes++;
  }
  function tick(r){
   const s=settings(),key=JSON.stringify([s.gold,s.freeRerolls,s.freeChests,s.unlimitedBanish]);
   if(owner!==String(r)){owner=String(r);previous=key;refreshPending=false;}
   if(previous!==key){previous=key;refreshPending=true;}
   if(s.gold){
    r.add(p.goldOffset).writeU32(MAX);
    const n=Math.min(63,r.add(F(0x998)).readU64().toNumber()),party=r.add(F(0x990)).readPointer();
    for(let i=0;i<n;i++)party.add(i*profile.partyStride+p.goldOffset).writeU32(MAX);
   }
   if(refreshPending){refreshPending=false;refresh(r);}
  }
  return {tick,status:()=>({...counts,maxGold:MAX})};
 }};
})();

