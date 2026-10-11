"""Start the complete local demo. Leaves no public deployment or cloud resources."""
from pathlib import Path
import os,sys,subprocess,signal,time
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from cloud.bootstrap import initialize
from cloud.config import Settings

if __name__=='__main__':
    subprocess.run([sys.executable,'-m','cloud.bootstrap'],check=True)
    env={**os.environ,**dotenv_values(ROOT/'.runtime/local.env')}
    api=subprocess.Popen([sys.executable,'-m','uvicorn','cloud.server:app','--host','127.0.0.1','--port','8000'],env=env)
    ui=None
    try:
        import urllib.request
        for _ in range(60):
            if api.poll() is not None: raise RuntimeError('API failed to start. Is port 8000 already in use?')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1) as response:
                    if response.status==200: break
            except OSError: time.sleep(.25)
        else: raise RuntimeError('API health check timed out')
        ui=subprocess.Popen([sys.executable,'-m','streamlit','run','dashboard/app.py','--server.address',os.getenv('NOCAP_UI_ADDRESS','0.0.0.0'),'--server.port','8501','--server.headless','true','--browser.gatherUsageStats','false'],env=env)
        print('NoCap dashboard: http://localhost:8501 | API docs: http://localhost:8000/docs',flush=True)
        while api.poll() is None and ui.poll() is None: time.sleep(.5)
    except KeyboardInterrupt: pass
    finally:
        for process in [ui,api]:
            if process and process.poll() is None: process.terminate()
        for process in [ui,api]:
            if process:
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill()
