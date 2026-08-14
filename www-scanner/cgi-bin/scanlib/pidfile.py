"""Tiny helpers for tracking the PID of the currently-running scanimage
process, so a separate CGI request (cancel.py) can find and signal it.
"""

import os


def write_pid(path, pid):
    with open(path, "w") as f:
        f.write(str(pid))


def read_pid(path):
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def remove_pid(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
