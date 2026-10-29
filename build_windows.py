"""Build the native-only runtime from an explicit public-source allowlist."""
from pathlib import Path
import hashlib,importlib.metadata,os,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parent
VERSION='2.1.1';NAME='AzerothSurvivorsTrainerNative-'+VERSION
SOURCE=['app.py', 'overlay.py', 'window_bridge.py', 'settings.py', 'runtime.py', 'collection.py', 'collection-catalog.json', 'compatibility.py', 'compatibility-manifest.json', 'native-profile.json', 'combat.js', 'economy.js', 'actions.js', 'trainer.js', 'map_travel.js', 'README.txt', 'README.md', 'PRIVACY.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'requirements-build.txt', 'build_windows.py', 'audit_release.py', '.gitignore']

def main():
    os.chdir(ROOT);licenses=ROOT/'third_party_licenses';licenses.mkdir(exist_ok=True)
    for package in ['frida','pyinstaller','pefile']:
        dist=importlib.metadata.distribution(package)
        for item in dist.files or []:
            if Path(item).name.upper().startswith(('LICENSE','COPYING','NOTICE')):
                source=dist.locate_file(item)
                if source.is_file():shutil.copyfile(source,licenses/(package+'-'+Path(item).name))
    for source,name in [(Path(sys.base_prefix)/'LICENSE.txt','Python-LICENSE.txt'),(Path(sys.base_prefix)/'tcl/tcl8.6/license.terms','Tcl-license.terms'),(Path(sys.base_prefix)/'tcl/tk8.6/license.terms','Tk-license.terms')]:
        if source.is_file():shutil.copyfile(source,licenses/name)
    build=ROOT/'build';build.mkdir(exist_ok=True)
    info=build/'version-info.txt';info.write_text("VSVersionInfo(ffi=FixedFileInfo(filevers=(2,1,1,0),prodvers=(2,1,1,0),mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Community project'),StringStruct('FileDescription','Azeroth Survivors Trainer native launcher'),StringStruct('FileVersion','2.1.1'),StringStruct('ProductName','Azeroth Survivors Trainer Native'),StringStruct('OriginalFilename','AzerothSurvivorsTrainerNative-2.1.1.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",encoding='utf-8')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name',NAME,'--icon',str(ROOT/'assets/wow.ico'),'--version-file',str(info),'--distpath','dist','--workpath','build/pyinstaller','--specpath','build','--collect-all','frida','--add-data',str(ROOT/'combat.js')+';'+'.','--add-data',str(ROOT/'economy.js')+';'+'.','--add-data',str(ROOT/'actions.js')+';'+'.','--add-data',str(ROOT/'map_travel.js')+';'+'.','--add-data',str(ROOT/'trainer.js')+';'+'.','--add-data',str(ROOT/'collection-catalog.json')+';'+'.','--add-data',str(ROOT/'native-profile.json')+';'+'.','--add-data',str(ROOT/'compatibility-manifest.json')+';'+'.','--add-data',str(ROOT/'README.txt')+';'+'.','--add-data',str(ROOT/'assets')+';'+'assets','--add-data',str(ROOT/'third_party_licenses')+';'+'third_party_licenses',str(ROOT/'app.py')]
    subprocess.run(command,check=True)
    dist=ROOT/'dist';exe=dist/(NAME+'.exe');archive=dist/(NAME+'-Windows-x64.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        z.write(exe,exe.name)
        for name in ['README.txt','PRIVACY.md','LICENSE','THIRD_PARTY_NOTICES.md']:z.write(ROOT/name,name)
        for p in licenses.iterdir():
            if p.is_file():z.write(p,'third_party_licenses/'+p.name)
        z.write(ROOT/'assets/ATTRIBUTION.txt','third_party_licenses/WoW-icon-attribution.txt')
    (dist/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'for p in [exe,archive]),encoding='ascii')
    print('Built native launcher and ZIP. Audit and packaged smoke test required.')

if __name__=='__main__':main()
