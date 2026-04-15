import sys
import traceback
import signal

def handler(signum, frame):
    print("Function timed out!")
    raise Exception("Timeout!")

# Add signal to catch hangs
# Windows does not support signal.SIGALRM!
# I will use threading timer to kill it and print stack trace.

import threading

def kill():
    print("Timeout reached, exiting.")
    import os
    os._exit(1)

timer = threading.Timer(10.0, kill)
timer.start()

try:
    print("Testing main...")
    import runpy
    runpy.run_path("main.py", run_name="__main__")
except Exception as e:
    print(e)
finally:
    timer.cancel()
    print("Finished.")
