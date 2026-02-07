import os
import sys

def is_docker() -> bool:
    path = '/.dockerenv'
    return os.path.exists(path)

def is_linux() -> bool:
    return sys.platform.startswith('linux')

def is_root() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # Windows usually doesn't have geteuid
