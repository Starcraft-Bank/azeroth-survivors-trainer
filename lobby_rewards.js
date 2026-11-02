/* Queue native permanent-gear rewards; ordinary guests retain their own validation. */
globalThis.AZS_LOBBY_REWARDS = {setup(api) {
  const p = api.profile.trainer?.matchRewards;
  let last = null, previousRun=null, previousClock=0;
  const awarded=new Set();
  if (!p || api.profile.compatibilityUnverified) return {tick(){}, command(){return {ok:false,error:'Match rewards unavailable for this build'};}, status:()=>({supported:false,canGrant:false,reason:'Match rewards unavailable for this build'})};
  const native = (key,ret,args)=>new NativeFunction(api.base.add(p.functions[key]),ret,args,{traps:'all'});
  const pool = native('gearPool','void',['pointer','uint8','uint64','uint64']);
  const zoneIndex = native('zoneIndex','uint64',['pointer','uint64']);
  const alloc = native('allocate','pointer',['uint64','uint64']);
  const free = native('deallocate','void',['pointer','uint64','uint64']);
  function eligible(actor) {
    const cls=actor.add(p.fields.class).readU8(), zptr=actor.add(p.fields.zonePointer).readPointer();
    const zlen=actor.add(p.fields.zoneLength).readU64().toNumber();
    if(![1,2,3,4,5,7,8,9,11].includes(cls)||zlen<1||zlen>64)throw Error('Invalid active class or map');
    const zone=zoneIndex(zptr,zlen), ids=new Set();
    for(let slot=0;slot<5;slot++) {
      const v=Memory.alloc(24);pool(v,cls,zone,slot);
      const cap=v.readU64().toNumber(), ptr=v.add(8).readPointer(), len=v.add(16).readU64().toNumber();
      try {if(len>64||cap<len)throw Error('Unexpected gear pool');for(let i=0;i<len;i++)ids.add(ptr.add(i*8).readU32());}
      finally {if(cap)free(ptr,cap*8,4);}
    }
    return {class:cls,map:zptr.readUtf8String(zlen),ids:[...ids]};
  }
  function queue(actor,ids,isGuest) {
    const v=actor.add(isGuest?p.fields.partyPendingGear:p.fields.pendingGear),cap=v.readU64().toNumber(),old=v.add(8).readPointer(),len=v.add(16).readU64().toNumber();
    if(len>256||cap<len||cap>65536||(cap&&old.isNull()))throw Error('Invalid native reward queue');
    const existing=new Set();for(let i=0;i<len;i++)existing.add(old.add(i*12).readU32());
    ids=ids.filter(id=>!existing.has(id));
    if(!ids.length)return 0;
    const needed=len+ids.length;
    if(needed>16)throw Error('Wait for pending native rewards to finish, then try again');
    let ptr=old;
    if(cap<needed) {
      ptr=alloc(needed*12,4);if(ptr.isNull())throw Error('Could not allocate reward queue');
      if(len)ptr.writeByteArray(old.readByteArray(len*12));
      v.writeU64(needed);v.add(8).writePointer(ptr);if(cap)free(old,cap*12,4);
    }
    ids.forEach((id,i)=>{const e=ptr.add((len+i)*12);e.writeU32(id);e.add(4).writeU32(1);e.add(8).writeFloat(0);});
    v.add(16).writeU64(needed);return ids.length;
  }
  function reason() {
    const run=api.getRun(),game=api.getGame?.();
    if(!game||game.isNull()||game.add(16).readU64().toString()==='2'||!run||run.isNull())return 'Start a solo match or host a lobby first';
    if(![1,2].includes(run.add(p.fields.phase).readU8()))return 'Start a match before granting gear';
    const travel=api.getTravelStatus?.();
    if(travel?.busy)return 'Wait for the map transfer to finish';
    if(travel?.originZone&&travel.currentZone&&travel.currentZone!==travel.originZone)return 'Return to the starting map to grant permanent gear';
    return '';
  }
  function tick() {
    const run=api.getRun();
    if(!run||run.isNull()||run.add(p.fields.phase).readU8()===0){awarded.clear();last=null;previousRun=null;previousClock=0;return;}
    const clock=run.add(p.fields.clock).readFloat(),identity=run.toString();
    if(identity!==previousRun||clock+1<previousClock){awarded.clear();last=null;}
    previousRun=identity;previousClock=clock;
  }
  return {tick,command(name) {
    if(name!=='grantMatchGear')return false;
    const unavailable=reason();if(unavailable)throw Error(unavailable);
    tick();const run=api.getRun();
    const n=run.add(p.fields.partyLength).readU64().toNumber();if(n>64)throw Error('Invalid party state');
    const party=run.add(p.fields.partyPointer).readPointer();
    const actors=[run,...Array.from({length:n},(_,i)=>party.add(i*p.partyStride)).filter(actor=>actor.readU64().toString()!=='2')];
    last={ok:true,players:actors.map((actor,index)=>{const reward=eligible(actor),identity=actor.toString()+':'+reward.map+':'+reward.class;
      if(awarded.has(identity))return {...reward,queued:0,reason:'Already queued for this class and map in this match'};
      const queued=queue(actor,reward.ids,index>0);awarded.add(identity);return {...reward,queued};})};
    api.notice?.('Queued current-class gear for this map. Native guest reward limits apply.');
    return last;
  },status:()=>{try{tick();const why=reason();return {supported:true,canGrant:!why,reason:why,last};}catch(e){return {supported:true,canGrant:false,reason:'Match state unavailable',last};}}};
}};
