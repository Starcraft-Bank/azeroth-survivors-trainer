"""Focus-scoped native keyboard and owned game-window integration."""
import ctypes,queue,threading
from ctypes import wintypes as w

class InsertHotkey:
    """Event-driven Insert only; other applications and other keys pass through."""
    def __init__(self,bridge,panel):
        self.events=queue.Queue();self.bridge=bridge;self.panel=panel;self.thread_id=0
        self.error='';self.stopping=False;self.down=set()
        self.thread=threading.Thread(target=self.listen,daemon=True);self.thread.start()
    def listen(self):
        user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,w.WPARAM,w.LPARAM)
        user.SetWindowsHookExW.argtypes=[ctypes.c_int,callback_type,w.HINSTANCE,w.DWORD];user.SetWindowsHookExW.restype=w.HANDLE
        user.CallNextHookEx.argtypes=[w.HANDLE,ctypes.c_int,w.WPARAM,w.LPARAM];user.CallNextHookEx.restype=ctypes.c_ssize_t
        user.UnhookWindowsHookEx.argtypes=[w.HANDLE];user.GetMessageW.argtypes=[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]
        kernel.GetModuleHandleW.argtypes=[w.LPCWSTR];kernel.GetModuleHandleW.restype=w.HMODULE
        kernel.GetCurrentThreadId.restype=w.DWORD
        @callback_type
        def callback(code,event,data):
            if code>=0:
                key=ctypes.cast(data,ctypes.POINTER(w.DWORD))[0]
                owns=self.bridge.hwnd and self.bridge.focused(self.panel)
                game_only=self.bridge.api.GetForegroundWindow()==self.bridge.hwnd
                token='overlay' if key==0x2d else str(key-0x30) if 0x31<=key<=0x37 else str(key-0x60) if 0x61<=key<=0x67 else None
                eligible=owns and token and (token=='overlay' or game_only)
                if event in (0x101,0x105):
                    self.down.discard(key)
                    if eligible:return 1
                elif event in (0x100,0x104):
                    first=key not in self.down;self.down.add(key)
                    if eligible:
                        if first:self.events.put(token)
                        return 1
            return user.CallNextHookEx(None,code,event,data)
        self.thread_id=kernel.GetCurrentThreadId()
        hook=user.SetWindowsHookExW(13,callback,kernel.GetModuleHandleW(None),0)
        if not hook:self.error='Insert shortcut unavailable. Use Open overlay on the launcher.';return
        try:
            msg=w.MSG()
            while not self.stopping and user.GetMessageW(ctypes.byref(msg),None,0,0)>0:pass
        finally:user.UnhookWindowsHookEx(hook)
    def stop(self):
        self.stopping=True
        if self.thread_id:
            api=ctypes.WinDLL('user32');api.PostThreadMessageW.argtypes=[w.DWORD,w.UINT,w.WPARAM,w.LPARAM]
            api.PostThreadMessageW(self.thread_id,0x12,0,0)

class GameWindow:
    def __init__(self):
        self.api=ctypes.WinDLL('user32',use_last_error=True)
        specs={
            'GetForegroundWindow':([],w.HWND), 'GetAncestor':([w.HWND,w.UINT],w.HWND),
            'GetWindowThreadProcessId':([w.HWND,ctypes.POINTER(w.DWORD)],w.DWORD),
            'IsWindowVisible':([w.HWND],w.BOOL), 'IsIconic':([w.HWND],w.BOOL),
            'GetAsyncKeyState':([ctypes.c_int],ctypes.c_short),
            'GetClientRect':([w.HWND,ctypes.POINTER(w.RECT)],w.BOOL),
            'ClientToScreen':([w.HWND,ctypes.POINTER(w.POINT)],w.BOOL),
            'SetForegroundWindow':([w.HWND],w.BOOL),
        }
        for name,(args,result) in specs.items():
            fn=getattr(self.api,name);fn.argtypes=args;fn.restype=result
        self.callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        self.api.EnumWindows.argtypes=[self.callback,w.LPARAM];self.api.EnumWindows.restype=w.BOOL
        self.hwnd=None

    def owner(self,hwnd):
        pid=w.DWORD();self.api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));return pid.value

    def find(self,pid):
        matches=[]
        @self.callback
        def visit(hwnd,_):
            if self.owner(hwnd)==pid and self.api.IsWindowVisible(hwnd):
                r=w.RECT();self.api.GetClientRect(hwnd,ctypes.byref(r))
                if r.right>400 and r.bottom>250:matches.append((r.right*r.bottom,hwnd))
            return True
        self.api.EnumWindows(visit,0);self.hwnd=max(matches)[1] if matches else None
        return self.hwnd

    def rect(self):
        if not self.hwnd or self.api.IsIconic(self.hwnd):return None
        r=w.RECT();p=w.POINT()
        if not self.api.GetClientRect(self.hwnd,ctypes.byref(r)):return None
        self.api.ClientToScreen(self.hwnd,ctypes.byref(p))
        return p.x,p.y,r.right,r.bottom

    def focused(self,panel):
        hwnd=self.api.GetForegroundWindow()
        return bool(hwnd and (hwnd==self.hwnd or self.api.GetAncestor(hwnd,3)==self.api.GetAncestor(panel,3)))

    def insert_down(self):return bool(self.api.GetAsyncKeyState(0x2d)&0x8000)
    def focus_game(self):
        if self.hwnd:self.api.SetForegroundWindow(self.hwnd)


