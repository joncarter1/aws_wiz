import os
import sys
from pathlib import Path

_home_state = Path.home() / ".aws-wiz"
_cwd_state = Path(".state")

# Determine which state directory to use
if _home_state.exists():
    STATE_DIR = _home_state
elif _cwd_state.is_dir():
    print(
        "Warning: Using legacy .state/ directory. "
        f"Please move it to {_home_state}",
        file=sys.stderr,
    )
    STATE_DIR = _cwd_state.resolve()
else:
    STATE_DIR = _home_state

KEYS_DIR = STATE_DIR / "keys"
FELLOWS_FILE = STATE_DIR / "fellows.toml"


def ensure_state_dirs():
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(KEYS_DIR, 0o700)
