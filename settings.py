"""Explicit native trainer settings. Every match cheat starts disabled."""
SCHEMA={
 'god':(False,False,True),'rapid':(False,False,True),'gold':(False,False,True),
 'legendary':(False,False,True),'xp':(False,False,True),'area':(False,False,True),
 'oneHit':(False,False,True),'killAura':(False,False,True),'killAuraRadius':(25,5,100),
 'freeRerolls':(False,False,True),'freeChests':(False,False,True),'unlimitedBanish':(False,False,True),
 'bossEnemies':(False,False,True),'bossId':(0,0,59),
 'rapidSeconds':(.1,0,.25),'xpMultiplier':(10,1,100),
 'areaMultiplier':(10,1,100),'damageMultiplier':(1,1,100),'speedMultiplier':(1,1,5),
}
DEFAULTS={key:row[0] for key,row in SCHEMA.items()}
TOGGLES=['god','rapid','gold','legendary','xp','area','bossEnemies']
OPTIONS={'rapidSeconds':[0,.1,.25],'xpMultiplier':[2,5,10,25,100],
         'areaMultiplier':[2,5,10,25,100],'damageMultiplier':[1,2,5,10,25,100],
         'speedMultiplier':[1,1.25,1.5,2,3,5]}
def validate_settings(value):
 if not isinstance(value,dict) or set(value)!=set(SCHEMA):return False
 for key,(default,low,high) in SCHEMA.items():
  v=value[key]
  if isinstance(default,bool):
   if not isinstance(v,bool):return False
  elif not isinstance(v,(int,float)) or isinstance(v,bool) or not low<=v<=high:return False
  if key=='bossId' and (not isinstance(v,int)):return False
 return True
