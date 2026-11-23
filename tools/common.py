"""Paths and helpers shared by the name recovery tools.

Nothing here reads or writes inside the repository except data/ (the published results).
Everything derived from game files lives in the work folder, which is outside the repo by default.

Environment:
  GTA6_GAME_DIR        folder holding the game archives (only the scan and extract tools need it)
  NAME_RECOVERY_WORK   work folder (default: a sibling of the repo named <repo>-work)
  PERCYSTAR_NAMES_DIR  folder of name lists (default: %LOCALAPPDATA%/PercyStar/names)
  NAME_RECOVERY_CRACK_EXE  the built cracker (default: <work>/bin/crack)
  NAME_RECOVERY_HIDE   file of names to treat as unknown (holdout tests)
"""
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
WORK = os.environ.get('NAME_RECOVERY_WORK') or os.path.join(os.path.dirname(REPO), os.path.basename(REPO) + '-work')
CRACK = os.path.join(WORK, 'crack')
PSIN_FILES = os.path.join(WORK, 'psin_files')
SITE_DATA = os.path.join(REPO, 'data')
NAMES_DIR = os.environ.get('PERCYSTAR_NAMES_DIR') or os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'PercyStar', 'names')
CRACK_EXE = os.environ.get('NAME_RECOVERY_CRACK_EXE') or os.path.join(WORK, 'bin', 'crack.exe' if os.name == 'nt' else 'crack')
THREADS = str(max(1, (os.cpu_count() or 4) - 2))


def game_dir():
    d = os.environ.get('GTA6_GAME_DIR')
    if not d or not os.path.isdir(d):
        raise SystemExit('set GTA6_GAME_DIR to the folder that holds the game archives')
    return d


def joaat_cs(s):
    """joaat of the text as written, the form struct, field and enum value names use"""
    h = 0
    for c in (s.encode('latin-1', 'replace') if isinstance(s, str) else s):
        h = (h + c) & 0xffffffff
        h = (h + (h << 10)) & 0xffffffff
        h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff
    h ^= h >> 11
    return (h + (h << 15)) & 0xffffffff


def joaat(s):
    """joaat of the lower-cased text, the form values stored in the data use"""
    return joaat_cs(s.lower())
