"""Public native trainer launcher and verified collection workflow."""
from pathlib import Path
import argparse,json,os,queue,sys,threading,time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from runtime import NativeGame,ROOT,VERSION,compatibility_check,self_test
from settings import DEFAULTS,validate_settings
from overlay import Overlay,theme,BG,CARD,TEXT,MUTED,GOLD
from collection import unlock_save,game_processes
HOME=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AzerothSurvivorsTrainerNative'

class App:
 def __init__(self,window):
  self.window=window;self.game=None;self.settings=dict(DEFAULTS);self.launching=False;self.unlocking=False;self.events=queue.Queue();self.saved={}
  try:self.saved=json.loads((HOME/'settings.json').read_text(encoding='utf-8'))
  except (OSError,ValueError):pass
  window.title('Azeroth Survivors Trainer · Native '+VERSION);window.geometry('650x430');window.minsize(590,420);window.configure(bg=BG);theme(window)
  try:window.iconbitmap(str(ROOT/'assets/wow.ico'))
  except tk.TclError:pass
  p=tk.Frame(window,bg=BG);p.pack(fill='both',expand=True,padx=28,pady=24)
  tk.Label(p,text='AZEROTH SURVIVORS',bg=BG,fg=TEXT,font=('Segoe UI',21,'bold')).pack(anchor='w')
  tk.Label(p,text='NATIVE TRAINER  /  '+VERSION,bg=BG,fg=GOLD,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(3,20))
  tk.Label(p,text='Select your installed game',bg=BG,fg=MUTED,font=('Segoe UI',10)).pack(anchor='w')
  beside=Path(sys.executable).parent/'AzerothSurvivors.exe';self.path=tk.StringVar(value=self.saved.get('game','') or (str(beside) if beside.exists() else ''))
  row=ttk.Frame(p);row.pack(fill='x',pady=(7,16));self.entry=ttk.Entry(row,textvariable=self.path);self.entry.pack(side='left',fill='x',expand=True,ipady=6)
  self.browse=ttk.Button(row,text='Browse…',command=self.choose);self.browse.pack(side='right',padx=(8,0))
  row=ttk.Frame(p);row.pack(fill='x');self.launch=ttk.Button(row,text='Launch with trainer',command=self.open_game,style='Gold.TButton');self.launch.pack(side='left')
  self.open_panel=ttk.Button(row,text='Open panel  [ INS ]',command=lambda:self.overlay.show(),state='disabled');self.open_panel.pack(side='left',padx=8)
  self.stop=ttk.Button(row,text='Close game',command=self.close_game,state='disabled');self.stop.pack(side='right')
  self.status=tk.StringVar(value='Ready. Supports the reviewed native game 0.130.0.')
  tk.Label(p,textvariable=self.status,bg=CARD,fg=TEXT,font=('Segoe UI',10),justify='left',anchor='w',wraplength=550,padx=14,pady=14).pack(fill='x',pady=17)
  tk.Label(p,text='Press Insert for all controls. Use windowed or borderless mode.\nAll cheats start off. Keep the trainer open while playing.',bg=BG,fg=MUTED,font=('Segoe UI',10),justify='left').pack(anchor='w')
  row=ttk.Frame(p);row.pack(fill='x',pady=(15,0));ttk.Button(row,text='Usage guide',command=lambda:os.startfile(str(ROOT/'README.txt'))).pack(side='left')
  self.check=ttk.Button(row,text='Check compatibility',command=self.check_compatibility);self.check.pack(side='right')
  self.overlay=Overlay(self);window.protocol('WM_DELETE_WINDOW',self.quit);window.after(150,self.poll)
 def choose(self):
  value=filedialog.askopenfilename(title='Select AzerothSurvivors.exe',filetypes=[('Windows executable','*.exe')])
  if value:self.path.set(value);self.save()
 def save(self):
  HOME.mkdir(parents=True,exist_ok=True);p=HOME/'settings.tmp';p.write_text(json.dumps({'game':self.path.get()},indent=2),encoding='utf-8');p.replace(HOME/'settings.json')
 def check_compatibility(self):
  self.check.configure(state='disabled');path=self.path.get();self.status.set('Checking the selected file without opening a game…')
  def work():
   try:
    _,profile,report=compatibility_check(path,HOME/'compatibility-report.json');text=(f"Compatible: game {profile['version']} / {profile['stamp']}" if profile else report['message'])
   except Exception as e:text=str(e)
   self.events.put(('compatibility',text))
  threading.Thread(target=work,daemon=True).start()
 def open_game(self):
  if self.game or self.launching or self.unlocking:return
  if game_processes():messagebox.showinfo('Close the game first','Close your other Azeroth Survivors game before launching the trainer.',parent=self.window);return
  self.settings=dict(DEFAULTS);self.overlay.sync();self.launching=True;self.launch.configure(state='disabled');self.browse.configure(state='disabled');self.entry.configure(state='disabled');self.save()
  self.status.set('Checking compatibility and launching the game…');game=NativeGame();self.game=game;path=self.path.get()
  def work():
   try:game.start(path,self.settings)
   except Exception as e:game.events.put({'kind':'launch-error','error':str(e)})
  threading.Thread(target=work,daemon=True).start()
 def apply_settings(self,settings):
  if not validate_settings(settings):raise ValueError('Invalid trainer setting.')
  if self.game and self.game.ready and not self.game.configure(settings):raise ValueError('The game rejected these settings.')
  self.settings=dict(settings)
 def action(self,name,args):
  if not self.game or not self.game.ready or not self.game.action(name,args):raise ValueError('Start a solo match or host a match before using this action.')
 def travel(self,zone):
  if not self.game or not self.game.ready:raise ValueError('Start a solo match or host a match first.')
  result=self.game.travel(zone)
  if not result or isinstance(result,dict) and result.get('ok') is False:
   raise ValueError((result.get('error') or result.get('reason') or 'Map transfer is unavailable.') if isinstance(result,dict) else 'Map transfer is unavailable.')
 def open_backups(self):
  p=HOME/'Collection Backups';p.mkdir(parents=True,exist_ok=True);os.startfile(str(p))
 def unlock_collection(self):
  if self.unlocking or not self.game or not self.game.ready:return
  game=self.game;status=game.agent.exports_sync.status();m=status.get('match')
  if status.get('fault') or m and m['phase']!=0:messagebox.showinfo('Leave the match first','Return to the character menu before unlocking your collection.',parent=self.overlay.window);return
  if not messagebox.askyesno('Unlock your collection permanently?',
   'This unlocks your own collection and class progression. The trainer will close its game, create and verify a save backup, apply the unlocks and restart the game. Existing equipped choices and statistics are kept.\n\nContinue?',parent=self.overlay.window):return
  status=game.agent.exports_sync.status();m=status.get('match')
  if status.get('fault') or m and m['phase']!=0:return
  self.unlocking=True;self.game=None;self.launching=True;self.overlay.hide(False);self.open_panel.configure(state='disabled');self.stop.configure(state='disabled');self.status.set('Closing the game and verifying your collection backup…');path=self.path.get()
  def work():
   try:
    game.close();end=time.monotonic()+5
    while game_processes() and time.monotonic()<end:time.sleep(.1)
    result=unlock_save(path,backup_dir=HOME/'Collection Backups');self.events.put(('unlocked',result))
   except Exception as e:self.events.put(('unlock-error',str(e)))
  threading.Thread(target=work,daemon=True).start()
 def reset_launch_ui(self):
  self.launching=False;self.launch.configure(state='normal');self.browse.configure(state='normal');self.entry.configure(state='normal');self.stop.configure(state='disabled');self.open_panel.configure(state='disabled')
 def poll(self):
  try:
   while True:
    kind,value=self.events.get_nowait()
    if kind=='compatibility':self.check.configure(state='normal');self.status.set(value)
    elif kind in ('unlocked','unlock-error'):
     self.unlocking=False;self.reset_launch_ui()
     if kind=='unlocked':self.status.set('Collection unlocked. Restarting the game…');self.open_game();messagebox.showinfo('Collection unlocked','Verified backup:\n'+value['backup'],parent=self.window)
     else:self.status.set('Collection unlock stopped: '+value);messagebox.showerror('Unlock stopped',value,parent=self.window)
  except queue.Empty:pass
  if self.game:
   try:
    while True:
     item=self.game.events.get_nowait();kind=item.get('kind')
     if kind=='ready':
      self.launching=False;self.open_panel.configure(state='normal');self.stop.configure(state='normal');self.status.set('Trainer ready. Press Insert in the game. All cheats are off.');self.overlay.set_catalog(self.game.catalog())
     elif kind=='status':self.overlay.update_status(item)
     elif kind=='notice':self.overlay.feedback.set(item['text'])
     elif kind=='fault':self.status.set('Trainer error: '+item['error'].splitlines()[0])
     elif kind in ('closed','launch-error'):
      self.status.set(item.get('error') or 'Game closed. Ready to launch again.');self.game=None;self.reset_launch_ui();self.overlay.update_travel({});self.overlay.hide(False);self.overlay.bridge.hwnd=None;break
   except queue.Empty:pass
  self.window.after(150,self.poll)
 def close_game(self):
  if self.game and messagebox.askyesno('Close the game?','This closes the game launched by this trainer. Finish or leave the match first.',parent=self.window):self.game.close()
 def quit(self):
  if self.unlocking:messagebox.showinfo('Collection update in progress','Wait for the verified save operation to finish.',parent=self.window);return
  if self.game and not messagebox.askyesno('Close trainer and game?','Closing the trainer also closes its game. Continue?',parent=self.window):return
  if self.game:self.game.close()
  self.overlay.hotkey.stop();self.window.destroy()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--diagnose',action='store_true');parser.add_argument('--self-test',action='store_true');parser.add_argument('--game');parser.add_argument('--report');parser.add_argument('--seconds',type=int,default=15);a=parser.parse_args()
 if a.diagnose or a.self_test:
  if not a.game or not a.report:parser.error('--game and --report are required')
  if a.self_test:raise SystemExit(self_test(a.game,a.report,a.seconds))
  _,profile,_=compatibility_check(a.game,a.report);raise SystemExit(0 if profile else 2)
 window=tk.Tk();App(window);window.mainloop()
if __name__=='__main__':main()
