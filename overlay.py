"""Native trainer control panel. All actions belong to the launched game."""
import queue
import tkinter as tk
from tkinter import ttk,messagebox
from settings import DEFAULTS,OPTIONS,TOGGLES
from window_bridge import GameWindow,InsertHotkey
BG='#10141c';CARD='#1a2230';TEXT='#edf1f7';MUTED='#97a7bd';GOLD='#e6bd75';LINE='#2d394c';DANGER='#f0a19a'

def theme(window):
 s=ttk.Style(window);s.theme_use('clam')
 s.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10))
 s.configure('TFrame',background=BG);s.configure('TLabel',background=BG)
 s.configure('TButton',padding=(13,9),background=CARD,borderwidth=0)
 s.map('TButton',background=[('active','#2d3b50')],foreground=[('disabled','#64748b')])
 s.configure('Gold.TButton',background=GOLD,foreground=BG,font=('Segoe UI',10,'bold'))
 s.map('Gold.TButton',background=[('active','#f4d395'),('disabled','#39414b')],foreground=[('disabled',MUTED)])
 s.configure('TNotebook',background=BG,borderwidth=0)
 s.configure('TNotebook.Tab',padding=(17,11),background=CARD)
 s.map('TNotebook.Tab',background=[('selected','#2c3542')],foreground=[('selected',GOLD)])
 s.configure('TCombobox',fieldbackground=CARD,background=LINE,padding=5)
 s.map('TCombobox',fieldbackground=[('readonly',CARD)],foreground=[('readonly',TEXT)])
 window.option_add('*TCombobox*Listbox.background',CARD);window.option_add('*TCombobox*Listbox.foreground',TEXT)

class Overlay:
 def __init__(self,app):
  self.app=app;self.bridge=GameWindow();self.visible=False;self.last_geometry=None;self.catalog_data={};self.action_buttons=[];self.travel_state={}
  self.window=tk.Toplevel(app.window);self.window.withdraw();self.window.overrideredirect(True);self.window.configure(bg=LINE);self.window.attributes('-topmost',True)
  self.window.bind('<Escape>',lambda e:self.hide());self.hotkey=InsertHotkey(self.bridge,self.window.winfo_id())
  body=tk.Frame(self.window,bg=BG);body.pack(fill='both',expand=True,padx=1,pady=1)
  head=tk.Frame(body,bg=BG);head.pack(fill='x',padx=25,pady=(20,5))
  tk.Label(head,text='AZEROTH  /  TRAINER',font=('Segoe UI',20,'bold'),fg=TEXT,bg=BG).pack(side='left')
  tk.Label(head,text='NATIVE  2.1',font=('Segoe UI',9,'bold'),fg=GOLD,bg=CARD,padx=10,pady=6).pack(side='right')
  self.summary=tk.StringVar(value='Start a solo match or host a co-op lobby.')
  tk.Label(body,textvariable=self.summary,fg=MUTED,bg=BG,font=('Segoe UI',10),anchor='w').pack(fill='x',padx=26,pady=(0,13))
  metrics=tk.Frame(body,bg=BG);metrics.pack(fill='x',padx=25,pady=(0,16));self.metrics={}
  for col,(key,label) in enumerate([('health','HEALTH'),('level','LEVEL'),('gold','GOLD'),('clock','MATCH TIME')]):
   metrics.columnconfigure(col,weight=1);tile=tk.Frame(metrics,bg=CARD);tile.grid(row=0,column=col,sticky='ew',padx=(0,8 if col<3 else 0))
   tk.Label(tile,text=label,font=('Segoe UI',8,'bold'),fg=MUTED,bg=CARD).pack(anchor='w',padx=12,pady=(9,2))
   var=tk.StringVar(value='—');self.metrics[key]=var;tk.Label(tile,textvariable=var,font=('Segoe UI',14,'bold'),fg=TEXT,bg=CARD).pack(anchor='w',padx=12,pady=(0,10))
  self.tabs=ttk.Notebook(body);self.tabs.pack(fill='both',expand=True,padx=18)
  self.pages={};self.canvases={};self.switches={};self.values={k:tk.StringVar(value=str(app.settings[k])) for k in OPTIONS}
  for name in ['Combat','Rewards','Spawners','Collection','Session']:
   outer=ttk.Frame(self.tabs);self.tabs.add(outer,text=name);canvas=tk.Canvas(outer,bg=BG,highlightthickness=0)
   bar=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview);bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
   page=ttk.Frame(canvas,padding=(12,16));win=canvas.create_window((0,0),window=page,anchor='nw')
   page.bind('<Configure>',lambda e,c=canvas:c.configure(scrollregion=c.bbox('all')));canvas.bind('<Configure>',lambda e,c=canvas,w=win:c.itemconfigure(w,width=e.width));canvas.configure(yscrollcommand=bar.set)
   self.pages[name]=page;self.canvases[str(outer)]=canvas
  self.window.bind('<MouseWheel>',self.scroll)
  p=self.pages['Combat'];self.heading(p,'Control the fight','Changes apply immediately. All cheats start off each time you launch.')
  for key,title,detail in [('god','God mode','Prevent incoming damage to players simulated by your host, including co-op guests.'),('oneHit','One-Hit Kill','Defeat enemies with a successful hit.'),('killAura','Kill Aura','Defeat nearby enemies automatically, including bosses.'),('rapid','Rapid skills','Shorten base-attack and learned-skill cooldowns.'),('xp','XP boost','Multiply incoming match experience.'),('area','Skill area','Increase supported skill ranges and radii.')]:self.toggle(p,key,title,detail)
  for key,title in [('rapidSeconds','Rapid cooldown · seconds'),('xpMultiplier','Experience multiplier'),('areaMultiplier','Skill-area multiplier'),('damageMultiplier','Damage multiplier'),('speedMultiplier','Movement-speed multiplier')]:self.combo(p,key,title)
  self.values['killAuraRadius']=tk.StringVar(value='25');self.combo(p,'killAuraRadius','Kill Aura radius',values=[5,10,15,25,50,100])
  self.note(p,'Skills still need valid targets. Killing a final boss can finish the match. Turning a cheat off restores its normal behavior; earned XP and loot remain.')
  p=self.pages['Rewards'];self.heading(p,'Rewards without the grind','Use each economy control independently.')
  for key,title,detail in [('gold','Unlimited gold','Maintain the game’s maximum run balance: 4,294,967,295.'),('freeChests','Free chests','Open paid chests for 0 gold.'),('freeRerolls','Free rerolls','Generate another choice for 0 gold.'),('unlimitedBanish','Unlimited banishes','Keep using the native banish action.'),('legendary','All Legendary rolls','Generate supported choices and class gear at Legendary quality.')]:self.toggle(p,key,title,detail)
  self.heading(p,'Drop supplies','Spawn native collectibles near your hero.')
  self.action_row(p,[('Spawn chest','spawnChest',{}),('Spawn Speed Rune','spawnPowerup',{'kind':3})])
  self.powerup=tk.StringVar(value='Speed Rune');self.powerup_box=ttk.Combobox(p,textvariable=self.powerup,values=['Speed Rune','Berserker Rune','Restoration Rune','Magnet'],state='readonly');self.powerup_box.pack(fill='x',pady=(4,8))
  self.action_row(p,[('Spawn selected power-up','selectedPowerup',{}),('Drop 10,000 gold','spawnGold',{'amount':10000}),('Drop 1,000 XP','spawnXp',{'amount':1000})])
  p=self.pages['Spawners'];self.heading(p,'Build your own encounter','Choose a map, then a boss or guardian. These actions require the host.')
  self.zone=tk.StringVar();self.boss=tk.StringVar();self.guardian=tk.StringVar()
  self.zone_box=self.select(p,'Map',self.zone,[]);self.zone_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_zone())
  self.travel_button=ttk.Button(p,text='Travel to selected map…',command=self.travel,state='disabled');self.travel_button.pack(anchor='w',pady=(0,8))
  self.travel_info=tk.StringVar(value='Start a solo match or host a match to transfer maps.')
  ttk.Label(p,textvariable=self.travel_info,foreground=MUTED,wraplength=640,justify='left').pack(fill='x',pady=(0,8))
  self.note(p,'Map travel moves the whole party and keeps player levels, items and match time. The original run still determines completion rewards.')
  self.boss_box=self.select(p,'Boss',self.boss,[]);self.boss_box.bind('<<ComboboxSelected>>',lambda e:self.select_boss())
  self.action_row(p,[('Spawn selected boss','selectedBoss',{}),('Spawn next scheduled boss','spawnNextBoss',{})])
  self.toggle(p,'bossEnemies','Boss enemies','Replace new normal enemy spawns with the selected boss.')
  self.guardian_box=self.select(p,'Guardian / rare',self.guardian,[])
  self.action_row(p,[('Spawn selected guardian','selectedGuardian',{})])
  self.note(p,'Manual boss spawns preserve the normal schedule. Spawn next advances it. Guardians keep their native interactions and cannot be duplicated while present.')
  p=self.pages['Collection'];self.heading(p,'Unlock the collection','A permanent change to your own native account, with a verified backup first.')
  self.note(p,'Unlock supported achievements and rewards, all classes’ zone clears, gear entries, Codex discoveries, perks, companions, races, tabards and appearances. Equipped choices, statistics and existing talent allocations are preserved.')
  self.note(p,'This grants the normal talent-point capacity. Native Marks and item-star upgrade currency are not filled. Other players’ accounts are unchanged.')
  box=tk.Frame(p,bg=CARD);box.pack(fill='x',pady=14)
  tk.Label(box,text='LEAVE YOUR MATCH FIRST',fg=GOLD,bg=CARD,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=16,pady=(14,5))
  tk.Label(box,text='Return to the character menu. The trainer closes its game,\nbacks up your save, applies the unlocks and restarts it.',fg=MUTED,bg=CARD,font=('Segoe UI',10),justify='left').pack(anchor='w',padx=16,pady=(0,14))
  self.unlock_button=ttk.Button(p,text='Unlock collection…',command=app.unlock_collection,style='Gold.TButton');self.unlock_button.pack(anchor='w',pady=6)
  ttk.Button(p,text='Open verified backups',command=app.open_backups).pack(anchor='w',pady=6)
  p=self.pages['Session'];self.heading(p,'Match actions','One-shot controls for the active run.')
  self.action_row(p,[('Instant win…','instantWin',{}),('Clear all enemies…','killAll',{})])
  self.note(p,'Instant win uses native victory processing. Clearing enemies can also finish a match if its final boss is present. These actions cannot be undone during the run.')
  self.heading(p,'Shortcuts','Insert opens or closes this panel. Escape closes it.')
  self.note(p,'1 God mode   ·   2 Rapid skills   ·   3 Unlimited gold\n4 Legendary rolls   ·   5 XP boost   ·   6 Skill area\n7 Boss enemies\n\nNumber keys are reserved while the game is focused: click cards to choose them. Other apps keep their normal keyboard input.')
  self.note(p,'Use windowed or borderless mode. Online games continue while this panel is open. Keep the trainer open; closing it closes the game it launched.')
  foot=tk.Frame(body,bg=BG);foot.pack(fill='x',padx=25,pady=(12,18));self.feedback=tk.StringVar(value='Ready. Settings apply immediately.')
  tk.Label(foot,textvariable=self.feedback,fg=MUTED,bg=BG,font=('Segoe UI',9),wraplength=680,justify='left',anchor='w').pack(fill='x',pady=(0,10))
  ttk.Button(foot,text='Disable all cheats',command=self.disable_all).pack(side='left');ttk.Button(foot,text='Done  [ INS ]',command=self.hide,style='Gold.TButton').pack(side='right')
  self.sync();self.window.after(50,self.poll)
 def heading(self,p,title,detail):
  ttk.Label(p,text=title,font=('Segoe UI',13,'bold'),foreground=GOLD).pack(anchor='w',pady=(3,4));self.note(p,detail)
 def note(self,p,text):ttk.Label(p,text=text,foreground=MUTED,wraplength=640,justify='left').pack(fill='x',pady=(2,10))
 def toggle(self,p,key,title,detail):
  row=tk.Frame(p,bg=CARD);row.pack(fill='x',pady=4);left=tk.Frame(row,bg=CARD);left.pack(side='left',fill='x',expand=True,padx=12,pady=10)
  number=str(TOGGLES.index(key)+1)+'  ' if key in TOGGLES else ''
  tk.Label(left,text=number+title,bg=CARD,fg=TEXT,font=('Segoe UI',10,'bold'),anchor='w').pack(fill='x')
  tk.Label(left,text=detail,bg=CARD,fg=MUTED,font=('Segoe UI',9),anchor='w',wraplength=480,justify='left').pack(fill='x',pady=(3,0))
  button=tk.Button(row,text='OFF',command=lambda:self.toggle_key(key),relief='flat',bd=0,font=('Segoe UI',10,'bold'),width=6,pady=7,cursor='hand2');button.pack(side='right',padx=12);self.switches[key]=button
 def combo(self,p,key,title,values=None):
  row=ttk.Frame(p);row.pack(fill='x',pady=6);ttk.Label(row,text=title).pack(side='left')
  c=ttk.Combobox(row,textvariable=self.values[key],values=values or OPTIONS[key],state='readonly',width=11);c.pack(side='right');c.bind('<<ComboboxSelected>>',lambda e,k=key:self.change_value(k))
 def select(self,p,title,var,values):
  ttk.Label(p,text=title,foreground=MUTED).pack(anchor='w',pady=(8,3));c=ttk.Combobox(p,textvariable=var,values=values,state='readonly');c.pack(fill='x',pady=(0,8));return c
 def action_row(self,p,entries):
  row=ttk.Frame(p);row.pack(fill='x',pady=6)
  for title,name,args in entries:
   b=ttk.Button(row,text=title,command=lambda n=name,a=args:self.action(n,a));b.pack(side='left',padx=(0,8));self.action_buttons.append(b)
 def toggle_key(self,key):
  settings=dict(self.app.settings);settings[key]=not settings[key];self.commit(settings)
 def change_value(self,key):
  settings=dict(self.app.settings);value=float(self.values[key].get());settings[key]=int(value) if value.is_integer() else value;self.commit(settings)
 def commit(self,settings):
  try:self.app.apply_settings(settings);self.feedback.set('Applied.');self.sync()
  except Exception as e:self.feedback.set(str(e));self.sync()
 def disable_all(self):self.commit(dict(DEFAULTS,bossId=self.app.settings['bossId']))
 def sync(self):
  for k,b in self.switches.items():
   on=self.app.settings[k];b.configure(text='ON' if on else 'OFF',bg=GOLD if on else LINE,fg=BG if on else MUTED,activebackground=GOLD if on else LINE)
  for k,v in self.values.items():v.set(str(self.app.settings[k]))
 def set_catalog(self,data):
  self.catalog_data=data;self.zone_box.configure(values=[z['name'] for z in data.get('zones',[])])
  if data.get('zones'):self.zone.set(data['zones'][0]['name']);self.refresh_zone()
 def refresh_zone(self):
  zones=self.catalog_data.get('zones',[]);z=next((v['id'] for v in zones if v['name']==self.zone.get()),0)
  self.bosses=[b for b in self.catalog_data.get('bosses',[]) if b['zone']==z];self.guardians=[g for g in self.catalog_data.get('guardians',[]) if g['zone']==z]
  self.boss_box.configure(values=[b['name']+('  [Final]' if b.get('final') else '') for b in self.bosses]);self.guardian_box.configure(values=[g['name'] for g in self.guardians])
  if self.bosses:self.boss_box.current(0);self.select_boss()
  if self.guardians:self.guardian_box.current(0)
  else:self.guardian.set('No guardian entries')
  self.refresh_travel()
 def update_travel(self,state):
  self.travel_state=dict(state or {});self.refresh_travel()
 def refresh_travel(self):
  state=self.travel_state;catalog=state.get('catalog') or [];selected=next((z for z in catalog if z['name']==self.zone.get()),None)
  current=state.get('currentZone');same=bool(selected and current in (selected['key'],selected['id']))
  ready=bool(state.get('supported') and state.get('canTravel') and not state.get('busy') and selected and not same)
  self.travel_button.configure(state='normal' if ready else 'disabled')
  names=lambda value:next((z['name'] for z in catalog if value in (z['key'],z['id'])),str(value or '—'))
  reason='Moving the party…' if state.get('busy') else 'Choose another map.' if same and state.get('canTravel') else state.get('reason') or ('Ready to move the party.' if ready else 'Map transfer is unavailable in this state.')
  self.travel_info.set(f'Current: {names(current)} · Original: {names(state.get("originZone"))}\n{reason}')
 def travel(self):
  selected=next((z for z in self.travel_state.get('catalog',[]) if z['name']==self.zone.get()),None)
  if not selected or not self.travel_state.get('canTravel') or self.travel_state.get('busy'):return
  if not messagebox.askyesno('Move the whole party?',f'Move every player in this match to {selected["name"]}?\n\nPlayer levels, carried items, gold and match time are kept. Existing enemies, hazards and uncollected drops are cleared. Completion rewards remain tied to the original run.',parent=self.window):return
  try:self.app.travel(selected['key']);self.feedback.set('Party map transfer queued.');self.travel_button.configure(state='disabled')
  except Exception as e:self.feedback.set(str(e))
 def select_boss(self):
  i=self.boss_box.current()
  if i>=0 and i<len(self.bosses):settings=dict(self.app.settings);settings['bossId']=self.bosses[i]['id'];self.commit(settings)
 def action(self,name,args):
  args=dict(args)
  if name=='selectedBoss':
   i=self.boss_box.current()
   if i<0:return
   name='spawnBoss';args={'id':self.bosses[i]['id']}
  elif name=='selectedGuardian':
   i=self.guardian_box.current()
   if i<0:return
   name='spawnGuardian';args={'id':self.guardians[i]['id']}
  elif name=='selectedPowerup':name='spawnPowerup';args={'kind':3+self.powerup_box.current()}
  if name in ('instantWin','killAll') and not messagebox.askyesno('Confirm match action','This can finish the current match and award normal progression. Continue?',parent=self.window):return
  try:self.app.action(name,args);self.feedback.set('Action queued for the game.')
  except Exception as e:self.feedback.set(str(e))
 def update_status(self,item):
  m=item.get('match');active=bool(m and m['phase'] in (1,2));fault=item.get('fault')
  travel=dict(item.get('travel') or {})
  if fault:travel.update(canTravel=False,reason='Resolve the trainer error before transferring maps.')
  self.update_travel(travel)
  if fault:
   # A native fault automatically disables its hooks; reflect that reset rather
   # than continuing to display enabled controls from the last user update.
   self.app.settings=dict(DEFAULTS,bossId=self.app.settings['bossId']);self.sync()
  n=sum(bool(self.app.settings[k]) for k in self.switches)
  self.summary.set(('TRAINER ERROR' if fault else 'CO-OP HOST' if m and m.get('coop') else 'SOLO' if active else 'CHARACTER MENU')+f'  ·  {n} toggles on  ·  '+('Endless' if m and m.get('endless') else 'Ready'))
  for k,v in self.metrics.items():
   if not m:v.set('—');continue
   if k=='health':v.set(f'{max(0,m["hp"]):,.0f} / {m["maxHp"]:,.0f}')
   elif k=='clock':t=max(0,int(m['clock']));v.set(f'{t//60:02}:{t%60:02}')
   else:v.set(f'{m[k]:,}')
  for b in self.action_buttons:b.configure(state='normal' if active and not fault else 'disabled')
  self.unlock_button.configure(state='normal' if not self.app.unlocking and not fault and (m is None or m['phase']==0) else 'disabled')
  if fault:self.feedback.set(fault.splitlines()[0])
  elif item.get('notice'):self.feedback.set(item['notice'])
 def scroll(self,e):
  c=self.canvases.get(self.tabs.select())
  if c:c.yview_scroll(-int(e.delta/120),'units')
  return 'break'
 def show(self):
  if not self.app.game or not self.app.game.ready or not self.bridge.find(self.app.game.pid):return
  self.visible=True;self.place();self.window.deiconify();self.window.lift();self.window.focus_force()
 def hide(self,return_focus=True):
  self.visible=False;self.window.withdraw()
  if return_focus:self.bridge.focus_game()
 def place(self):
  rect=self.bridge.rect()
  if not rect:return
  x,y,w,h=rect;pw=min(780,max(540,w-24));ph=min(820,max(440,h-24));geometry=f'{pw}x{ph}+{max(0,x+(w-pw)//2)}+{max(0,y+(h-ph)//2)}'
  if geometry!=self.last_geometry:self.window.geometry(geometry);self.last_geometry=geometry
 def poll(self):
  try:
   game=self.app.game
   if not game or not game.ready:
    if self.visible:self.hide(False)
    self.bridge.hwnd=None
   else:
    if not self.bridge.hwnd:self.bridge.find(game.pid)
    focused=self.bridge.focused(self.window.winfo_id())
    try:
     while True:
      token=self.hotkey.events.get_nowait()
      if not focused:continue
      if token=='overlay':self.hide() if self.visible else self.show()
      else:self.toggle_key(TOGGLES[int(token)-1])
    except queue.Empty:pass
    if self.visible:
     if not focused or not self.bridge.rect():self.hide(False)
     else:self.place()
    if self.hotkey.error:self.feedback.set(self.hotkey.error)
  finally:self.window.after(50,self.poll)
