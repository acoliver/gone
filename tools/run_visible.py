"""Keep only this command's native Godot window frontmost during verification."""
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

command = sys.argv[1:]
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
lines = queue.Queue()
def stream():
    for line in process.stdout:
        lines.put(line)
    lines.put(None)
threading.Thread(target=stream, daemon=True).start()
owned_app = None if '--headless' in command else process.pid
last_focus = 0
while True:
    try:
        line = lines.get(timeout=1)
    except queue.Empty:
        line = ''
    if line is None:
        break
    if line:
        print(line, end='', flush=True)
        match = re.search(r'spawned app pid (\d+)', line)
        if match:
            owned_app = int(match.group(1))
    if owned_app is not None and time.monotonic() - last_focus >= 10:
        script = f'tell application "System Events" to set frontmost of (first process whose unix id is {owned_app}) to true'
        focus = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        print(f'OWNED_WINDOW_FOCUS pid={owned_app} code={focus.returncode}', flush=True)
        last_focus = time.monotonic()
raise SystemExit(process.wait())
