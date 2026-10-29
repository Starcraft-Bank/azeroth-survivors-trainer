/* Native trainer actions. Commands are dispatched on the host simulation thread. */
(() => {
  'use strict';
  globalThis.AZS_TRAINER_ACTIONS = {setup(api) {
    const {profile,base,F,E,getSettings,getRun,guarded,notice}=api,p=profile.trainer.actions;
    const fn=(rva,result,args)=>new NativeFunction(base.add(rva),result,args,{traps:'all'});
    const spawnBoss=fn(profile.functions.bossSpawn,'void',['pointer','pointer','float']);
    const spawnMob=fn(profile.functions.mobSpawn,'void',['pointer','uint64','pointer']);
    const damage=fn(profile.functions.enemyDamage,'void',['pointer','uint64','float','uint32','uint32','uint32','uint32']);
    const loot=fn(profile.rewards.spawnLoot,'void',['pointer','uint32','uint32','pointer']);
    const finish=fn(p.victory,'void',['pointer']);
    const allocate=fn(profile.functions.allocate,'pointer',['uint64','uint64']);
    const deallocate=fn(profile.functions.deallocate,'void',['pointer','uint64','uint64']);
    const xyz=Memory.alloc(12),zones=[],bosses=[],guardians=[],guardianById=new Map();
    const text=(ptr,n)=>n>4096?'':ptr.readUtf8String(n);
    const num=(ptr,off)=>ptr.add(off).readU64().toNumber();
    const marker=0x100000;
    for(let z=0;z<profile.zoneCount;z++) {
      const zone=base.add(profile.zoneTable+z*profile.zoneStride);
      const row={id:z,key:text(zone.add(8).readPointer(),num(zone,16)),name:text(zone.add(24).readPointer(),num(zone,32)),keyPointer:zone.add(8).readPointer(),keyLength:num(zone,16)};
      zones.push(row);
      const bp=zone.add(0x88).readPointer(),bn=num(zone,0x90),gp=zone.add(0x78).readPointer(),gn=num(zone,0x80);
      if(bn!==5||gn>32)throw Error('Unsupported native action catalog');
      for(let i=0;i<bn;i++){const def=bp.add(i*profile.bossStride);bosses.push({id:z*5+i,zone:z,index:i,name:text(def.readPointer(),num(def,8)),final:!!def.add(100).readU8(),pointer:def});}
      for(let i=0;i<gn;i++){const def=gp.add(i*p.creatureStride),g={id:z*32+i,zone:z,index:i,name:text(def.add(16).readPointer(),num(def,24)),pointer:def};guardians.push(g);guardianById.set(g.id,g);}
    }
    if(bosses.length!==60||guardians.length!==p.creatureCount)throw Error('Native action catalog count changed');
    let owner='',lastClock=-1,nextAura=0,nextKill=0,killQueue=[],auraQueue=[],foreign=new Map(),lastAction='',spawnedBosses=0,spawnedGuardians=0,kills=0,converted=0,limited=0,converting=false;
    const running=r=>r&&!r.isNull()&&r.add(F(0xca2)).readU8()===1;
    const active=r=>r&&!r.isNull()&&[1,2].includes(r.add(F(0xca2)).readU8());
    const time=r=>r.add(F(0xbf4)).readFloat();
    const enemies=r=>{const n=num(r,F(0x590));if(n>100000)throw Error('Invalid enemy vector');return {n,pointer:r.add(F(0x588)).readPointer()};};
    const alive=e=>e.add(E(0xb0)).readU32()===0&&e.add(E(0x160)).readFloat()>0;
    const boss=e=>e.add(E(0x18)).readS64().toString()!=='-1';
    function reset(r){owner=String(r);lastClock=time(r);nextAura=0;nextKill=0;killQueue=[];auraQueue=[];foreign.clear();lastAction='';spawnedBosses=0;spawnedGuardians=0;kills=0;converted=0;limited=0;}
    function prepare(r){if(owner!==String(r)||time(r)<lastClock-1)reset(r);lastClock=time(r);}
    function requireRun(){const r=getRun();if(!active(r))throw Error('Start a match as the host first.');prepare(r);return r;}
    function position(r){return [0x4f0,0x4f4,0x4f8].map(o=>r.add(F(o)).readFloat());}
    function enemyPosition(r,e){const start=e.add(E(0x194)).readFloat(),duration=e.add(E(0x198)).readFloat(),t=duration>0?Math.min(1,Math.max(0,(time(r)-start)/duration)):1;return [0,4,8].map(o=>e.add(E(0x17c+o)).readFloat()*(1-t)+e.add(E(0x188+o)).readFloat()*t);}
    function zoneIndex(r){const key=text(r.add(F(0x2b8)).readPointer(),num(r,F(0x2c0)));return zones.findIndex(z=>z.key===key);}
    function bossCount(r){const v=enemies(r);let count=0;for(let i=0;i<v.n;i++){const e=v.pointer.add(i*profile.enemyStride);if(alive(e)&&boss(e))count++;}return count;}
    function summonBoss(r,id){const def=bosses[id];if(!def)throw Error('Select a valid boss.');if(bossCount(r)>=64)throw Error('The arena already has 64 living bosses.');const before=num(r,F(0x590));spawnBoss(r,def.pointer,1.0);if(num(r,F(0x590))<=before)throw Error('The game rejected the boss spawn.');spawnedBosses++;return def;}

    // Foreign guardians retain valid local kind=0 in every native record.
    // Their actual definition is selected at the four native resolution sites;
    // no invalid catalog index is serialized or left in a Run after unloading.
    const recordChoice=(r,index)=>owner===String(r)?foreign.get(index):null;
    function inline(rva,body){Interceptor.attach(base.add(rva),function(){const c=this.context;guarded(()=>body(c));});}
    inline(p.guardianSpawnDefinition,c=>{const g=recordChoice(c.rsi,c.rbx.toUInt32());if(g){c.r15=g.pointer;c.r12=ptr(0);c.r14=ptr(marker+g.id);}});
    inline(p.guardianAnnouncementDefinition,c=>{const g=recordChoice(c.rsi,c.rbx.toUInt32());if(g){c.rdi=g.pointer;c.r15=ptr(0);}});
    inline(p.guardianTargetDefinition,c=>{const g=recordChoice(c.rsi,c.r15.toUInt32()/5);if(g){c.rdi=g.pointer;c.rbx=ptr(0);}});
    inline(p.guardianRehealthIndex,c=>{const r=c.rbp.add(0x3a0).readPointer(),g=recordChoice(r,c.rax.toUInt32()/5);if(g)c.rdi=ptr(marker+g.id);});
    for(const rva of [p.guardianHealth,p.guardianDamage])Interceptor.attach(base.add(rva),{
      onEnter(args){this.restore=null;const g=guardianById.get(args[1].toUInt32()-marker);if(!g)return;const r=args[0],z=zones[g.zone];this.restore={r,pointer:r.add(F(0x2b8)).readPointer(),length:r.add(F(0x2c0)).readU64()};r.add(F(0x2b8)).writePointer(z.keyPointer);r.add(F(0x2c0)).writeU64(z.keyLength);args[1]=ptr(g.index);},
      onLeave(){if(this.restore){const x=this.restore;x.r.add(F(0x2b8)).writePointer(x.pointer);x.r.add(F(0x2c0)).writeU64(x.length);}}
    });
    function summonGuardian(r,id){
      const g=guardianById.get(id);if(!g)throw Error('Select a valid guardian.');if(r.add(p.guardianDisabled).readU8())throw Error('Guardians are unavailable in this game mode.');
      let n=num(r,p.guardianLength),cap=num(r,p.guardianCapacity),vector=r.add(p.guardianPointer).readPointer();if(n>=512||cap<n||cap>100000)throw Error('Guardian limit reached.');
      // Reuse a dead trainer guardian of the same definition; never duplicate a live one.
      for(const [i,choice] of foreign){if(choice.id!==id||i>=n)continue;const record=vector.add(i*p.guardianStride);if(!record.readU64().equals(0))throw Error('That trainer guardian is already alive.');const pos=position(r);record.add(24).writeFloat(pos[0]+12);record.add(28).writeFloat(pos[1]);record.add(32).writeFloat(pos[2]);record.add(36).writeFloat(time(r));spawnedGuardians++;return g;}
      if(n===cap){const newCap=Math.max(8,Math.min(1024,cap*2)),next=allocate(newCap*p.guardianStride,8);if(next.isNull())throw Error('Could not allocate guardian record.');if(n)next.writeByteArray(vector.readByteArray(n*p.guardianStride));r.add(p.guardianPointer).writePointer(next);r.add(p.guardianCapacity).writeU64(newCap);if(cap)deallocate(vector,cap*p.guardianStride,8);vector=next;}
      const record=vector.add(n*p.guardianStride),pos=position(r);record.writeByteArray(new Uint8Array(p.guardianStride));record.add(16).writeU64(0);record.add(24).writeFloat(pos[0]+12);record.add(28).writeFloat(pos[1]);record.add(32).writeFloat(pos[2]);record.add(36).writeFloat(time(r));foreign.set(n,g);r.add(p.guardianLength).writeU64(n+1);spawnedGuardians++;return g;
    }
    const mobReplacement=new NativeCallback(function(r,index,pos){
      let substitute=false;guarded(()=>{if(!converting&&running(r)&&getSettings().bossEnemies&&getRun()?.equals(r)){prepare(r);substitute=true;if(bossCount(r)>=64){limited++;return;}converting=true;try{summonBoss(r,getSettings().bossId??0);converted++;}finally{converting=false;}}});
      if(!substitute)spawnMob(r,index,pos);
    },'void',['pointer','uint64','pointer']);
    Interceptor.replace(base.add(profile.functions.mobSpawn),mobReplacement);
    function queueKills(r,radius){const queue=radius==null?killQueue:auraQueue,v=enemies(r),p0=position(r),seen=new Set(queue);for(let i=0;i<v.n;i++){const e=v.pointer.add(i*profile.enemyStride);if(!alive(e))continue;if(radius!=null){const pos=enemyPosition(r,e);if((pos[0]-p0[0])**2+(pos[1]-p0[1])**2>radius*radius)continue;}const id=e.add(E(0xf0)).readU64().toString();if(!seen.has(id)){queue.push(id);seen.add(id);}}return queue.length;}
    function drainKills(r){if(time(r)<nextKill)return;nextKill=time(r)+.2;let budget=32;while(budget--&&(killQueue.length||auraQueue.length)&&running(r)){const id=(killQueue.length?killQueue:auraQueue).shift(),v=enemies(r);for(let i=0;i<v.n;i++){const e=v.pointer.add(i*profile.enemyStride);if(e.add(E(0xf0)).readU64().toString()===id&&alive(e)){damage(r,uint64(id),1e30,0,0,0,0);kills++;break;}}}}
    function pickup(r,kind,amount=1){if(num(r,profile.rewards.lootLengthOffset)>=500)throw Error('The map already has 500 pickups.');const pos=position(r);pos[0]+=5;pos.forEach((v,i)=>xyz.add(i*4).writeFloat(v));loot(r,kind,amount,xyz);}
    function command(name,args={}){const r=requireRun();let result;
      if(name==='spawnBoss'){const b=summonBoss(r,Number(args.id));result='Spawned '+b.name;}
      else if(name==='spawnNextBoss'){const zone=zoneIndex(r),index=num(r,p.nextBossIndex);if(zone<0||index>=5)throw Error('All scheduled bosses have already spawned.');const b=summonBoss(r,zone*5+index);r.add(p.nextBossIndex).writeU64(index+1);result='Spawned next boss: '+b.name;}
      else if(name==='spawnGuardian'){const g=summonGuardian(r,Number(args.id));result='Summoning guardian: '+g.name;}
      else if(name==='instantWin'){if(r.add(F(0xb10)).readU32())throw Error('This match has already been won.');r.add(F(0xb10)).writeU32(1);r.add(p.winTime).writeFloat(time(r));r.add(F(0xca2)).writeU8(1);finish(r);result='Match completed.';}
      else if(name==='killAll'){result='Queued '+queueKills(r,null)+' enemies for defeat.';}
      else if(name==='spawnChest'){pickup(r,2);result='Spawned a chest.';}
      else if(name==='spawnPowerup'){const kind=Number(args.kind??3);if(!Number.isInteger(kind)||kind<3||kind>6)throw Error('Select a valid powerup.');pickup(r,kind);result='Spawned a powerup.';}
      else if(name==='spawnGold'||name==='spawnXp'){const amount=Number(args.amount??1000);if(!Number.isInteger(amount)||amount<1||amount>100000)throw Error('Amount must be between 1 and 100000.');pickup(r,name==='spawnGold'?1:0,amount);result='Spawned '+amount+' '+(name==='spawnGold'?'gold.':'XP.');}
      else throw Error('Unknown trainer action.');
      lastAction=result;if(notice)notice(result);return {ok:true,message:result};
    }
    function tick(r){if(!active(r))return;prepare(r);if(!running(r))return;const s=getSettings(),t=time(r);if(!s.killAura)auraQueue=[];if(s.killAura&&t>=nextAura){queueKills(r,Math.min(100,Math.max(5,Number(s.killAuraRadius??25))));nextAura=t+.2;}drainKills(r);}
    function catalog(){return {zones:zones.map(({id,key,name})=>({id,key,name})),bosses:bosses.map(({id,zone,name,final})=>({id,zone,name,final})),guardians:guardians.map(({id,zone,name})=>({id,zone,name}))};}
    return {tick,command,catalog,status:()=>({lastAction,spawnedBosses,spawnedGuardians,kills,converted,conversionLimited:limited,queuedKills:killQueue.length+auraQueue.length,queuedExplicitKills:killQueue.length,queuedAuraKills:auraQueue.length})};
  }};
})();
