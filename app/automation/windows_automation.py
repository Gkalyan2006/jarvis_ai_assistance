import os
import subprocess
import shlex
import webbrowser

def open_app(path_or_name: str):
    # Try to open with os.startfile or webbrowser
    try:
        if os.path.exists(path_or_name):
            os.startfile(path_or_name)
            return True
        # common app shortcuts
        webbrowser.open(path_or_name)
        return True
    except Exception:
        # fallback: try start via cmd
        try:
            subprocess.Popen(['start', '', path_or_name], shell=True)
            return True
        except Exception:
            return False

def run_command(cmd: str):
    try:
        # careful: run with shell to allow Windows commands
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}
    except Exception as e:
        return {"error": str(e)}
