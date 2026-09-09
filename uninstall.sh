#!/bin/sh
set -eu

SERVICE=/service/hoymiles-pvinverter
sv down "$SERVICE" 2>/dev/null || true
rm -f "$SERVICE"

/usr/bin/python3 - <<'PY'
from pathlib import Path
rc = Path('/data/rc.local')
line = 'ln -snf /data/hoymiles-pvinverter/service /service/hoymiles-pvinverter'
if rc.exists():
    lines = [x for x in rc.read_text().splitlines() if x.strip() != line]
    rc.write_text('\n'.join(lines) + '\n')
PY

echo "Service entfernt. Daten unter /data/hoymiles-pvinverter bleiben erhalten."
