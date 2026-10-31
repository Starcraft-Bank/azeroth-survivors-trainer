"""Launch and own one supported native game process; never patch files."""
from pathlib import Path
import ctypes,hashlib,json,os,queue,sys,threading,time
from ctypes import wintypes

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
VERSION='2.1.5'
from settings import DEFAULTS, SCHEMA, validate_settings


class OwnedProcess:
    """Keep an OS handle so PID reuse can never redirect a later close."""
    def __init__(self,pid):
        self.lock=threading.Lock()
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.OpenProcess.restype=wintypes.HANDLE
        self.api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        self.api.WaitForSingleObject.restype=wintypes.DWORD
        self.api.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
        self.api.TerminateProcess.restype=wintypes.BOOL
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.api.OpenProcess(0x100001,False,pid) # SYNCHRONIZE | TERMINATE
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())

    def close(self,terminate=False):
        with self.lock:handle=self.handle;self.handle=None
        if not handle:return
        try:
            if terminate:
                state=self.api.WaitForSingleObject(handle,0)
                if state==0xffffffff:raise ctypes.WinError(ctypes.get_last_error())
                if state==0x102 and not self.api.TerminateProcess(handle,0):
                    error=ctypes.get_last_error()
                    if self.api.WaitForSingleObject(handle,0)!=0:raise ctypes.WinError(error)
        finally:self.api.CloseHandle(handle)


def compatibility_check(path, report_path=None):
    from compatibility import analyze_game,select_launch_profile,write_report
    exe=Path(path).resolve(strict=True)
    if not exe.is_file():raise ValueError('Select AzerothSurvivors.exe.')
    profile,report=analyze_game(exe,ROOT/'compatibility-manifest.json')
    launch_profile,_=select_launch_profile(exe,ROOT/'compatibility-manifest.json')
    report['diagnosticHooksMatch']=bool(profile);report['diagnosticOnly']=True;report['launchAllowed']=True
    if not profile:
        report['message']='Diagnostic: some hook locations differ. Launch remains allowed; individual features may be unavailable.'
    profile=launch_profile
    if report_path:write_report(report_path,report)
    return exe,profile,report

def check_game(path):
    report_path=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AzerothSurvivorsTrainerNative'/'compatibility-report.json'
    from compatibility import select_launch_profile,write_report
    exe=Path(path).resolve(strict=True)
    profile,report=select_launch_profile(exe,ROOT/'compatibility-manifest.json')
    write_report(report_path,report)
    if not (exe.parent/'Data').is_dir():raise ValueError('The game needs its Data folder beside AzerothSurvivors.exe.')
    return exe,profile

class NativeGame:
    def __init__(self):
        self.events=queue.Queue();self.device=None;self.session=None;self.agent=None;self.pid=None;self.owned_process=None
        self.unverified=False;self.ready=False;self.running=False;self.feature_errors=[];self.closed=threading.Event();self.lock=threading.RLock();self.latest=None

    def start(self,path,settings,environment=None):
        if not validate_settings(settings):raise ValueError('Invalid pre-match settings.')
        exe,profile=check_game(path)
        self.unverified=bool(profile.get("compatibilityUnverified"))
        import frida
        with self.lock:
            if self.closed.is_set():raise RuntimeError('The launcher closed before the game started.')
            if self.pid:raise RuntimeError('The game is already running.')
            self.device=frida.get_local_device()
            # Prevent the game's updater from changing the checked build during
            # this session. Everything else uses the player's ordinary game/save.
            env=dict(os.environ,WOW_ROGUE_UPDATE_AUTO='0',WOW_ROGUE_UPDATE='0')
            if environment:env.update(environment)
            self.pid=self.device.spawn(str(exe),argv=[str(exe)],env=env,cwd=str(exe.parent))
            try:
                self.owned_process=OwnedProcess(self.pid)
                self.session=self.device.attach(self.pid)
                self.session.on('detached',self._detached)
                self.events.put({'kind':'compatible','version':profile['version'],'stamp':profile['stamp'],'verified':not self.unverified})
                source='globalThis.AZS_SCHEMA='+json.dumps(SCHEMA)+';\n'+'globalThis.AZS_PROFILE='+json.dumps(profile)+';\nglobalThis.AZS_SETTINGS='+json.dumps(settings)+';\n'+'\n'.join((ROOT/name).read_text(encoding='utf-8') for name in ['combat.js','economy.js','actions.js','map_travel.js','resilience.js','trainer.js'])
                try:
                    self.agent=self.session.create_script(source,name='AzerothSurvivorsTrainerNative')
                    self.agent.on('message',self._message);self.agent.load()
                    if not self.ready:raise RuntimeError('Feature initialization did not complete.')
                except Exception as error:
                    # The child is still suspended: remove partial hooks before any
                    # gameplay can borrow agent-owned data, then start the normal game.
                    if self.agent:self.agent.unload()
                    self.agent=None;self.ready=False
                    self.events.put({'kind':'degraded','error':str(error),'text':'Game running without extensions; feature initialization failed.'})
                self.device.resume(self.pid);self.running=True
            except BaseException:
                self.close();raise

    def _message(self,message,data):
        if message.get('type')=='send':
            value=message['payload']
            if value.get('kind')=='ready':self.ready=True
            if value.get('kind')=='feature-unavailable':self.feature_errors.append(value)
            if value.get('kind')=='status':
                value['unavailableFeatures']=list(self.feature_errors);self.latest=value
            self.events.put(value)
        elif message.get('type')=='error':
            self.events.put(dict(kind='fault',error=message.get('description','Native runtime error')))

    def _detached(self,reason,crash=None):
        self.closed.set();self.ready=False;self.running=False
        # An unexpected agent detachment must not leave a game running with
        # callbacks and borrowed definitions whose owner has disappeared.
        if self.owned_process:self.owned_process.close(terminate=reason!='process-terminated')
        self.pid=None
        self.events.put(dict(kind='closed',reason=reason,crashed=crash is not None))

    def configure(self,settings):
        if not validate_settings(settings):return False
        return self.agent.exports_sync.configure(settings)

    def action(self,name,args=None):return self.agent.exports_sync.action(name,args or {})
    def travel(self,zone):return self.agent.exports_sync.travel(zone)
    def catalog(self):return self.agent.exports_sync.catalog()

    def close(self):
        # Trainer callbacks and cloned definitions borrow agent-owned memory. Terminate
        # our own child before unloading the session; never detach a live game.
        with self.lock:
            if self.owned_process:
                self.owned_process.close(terminate=True)
            elif self.pid and self.device:
                # Only reachable if retaining the freshly spawned, still
                # suspended child's handle failed before session attachment.
                try:self.device.kill(self.pid)
                except Exception as error:
                    if type(error).__name__!='ProcessNotFoundError':raise
            self.pid=None;self.ready=False;self.running=False;self.closed.set()

def self_test(game,report,seconds=15):
    """Packaged launch check: isolated save, no combat/test memory writes."""
    target=Path(report).resolve();target.parent.mkdir(parents=True,exist_ok=True)
    session=NativeGame();result={'version':VERSION,'success':False}
    private=target.parent/'smoke-profile';private.mkdir(exist_ok=True)
    try:
        session.start(game,dict(DEFAULTS),dict(WOW_ROGUE_SAVE=str(private/'save.txt'),APPDATA=str(private/'Roaming'),LOCALAPPDATA=str(private/'Local')))
        end=time.monotonic()+seconds
        while time.monotonic()<end and not session.closed.is_set():time.sleep(.25)
        result.update(success=session.ready and bool(session.latest) and not session.latest.get('fault'),status=session.latest)
    except Exception as error:result['error']=str(error)
    finally:
        records=[]
        while not session.events.empty():records.append(session.events.get_nowait())
        result['events']=records[-20:]
        session.close();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return 0 if result['success'] else 1
