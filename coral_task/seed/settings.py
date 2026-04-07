"""Settings module"""

import shutil

FORFEIT = False
FORFEIT_TIME = 600  # Time in seconds

LEAGUE_CLIENT_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'

# Auto-detect tesseract: homebrew Apple Silicon, homebrew Intel, or fallback
TESSERACT_PATH = shutil.which('tesseract') or '/opt/homebrew/bin/tesseract'
