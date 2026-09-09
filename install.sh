#!/bin/sh
set -eu

BASE=/data/hoymiles-pvinverter
SERVICE=/service/hoymiles-pvinverter

if [ "$(pwd)" != "$BASE" ]; then
    echo "Bitte Repository nach $BASE kopieren und install.sh dort starten."
    echo "Aktuell: $(pwd)"
    exit 2
fi

chmod +x \
    "$BASE/install.sh" \
    "$BASE/bootstrap_vendor.py" \
    "$BASE/hoymiles_pvinverter.py" \
    "$BASE/test_hms.py" \
    "$BASE/uninstall.sh" \
    "$BASE/service/run" \
    "$BASE/service/log/run"

/usr/bin/python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python >= 3.9 required")
for module in ("dbus", "gi", "cryptography"):
    __import__(module)
print("System dependencies OK")
PY

if [ ! -f /opt/victronenergy/dbus-systemcalc-py/ext/velib_python/vedbus.py ]; then
    echo "WARNUNG: Standard-velib-Pfad fehlt; Treiber sucht beim Start weitere Victron-Pfade."
fi

echo "Installiere gepinnte Python-Abhängigkeiten ohne pip ..."
/usr/bin/python3 "$BASE/bootstrap_vendor.py"

PYTHONPATH="$BASE/vendor" /usr/bin/python3 - <<'PY'
import google.protobuf
import crcmod
import cryptography
import hoymiles_wifi
from hoymiles_wifi.dtu import DTU
print("protobuf:", google.protobuf.__version__)
print("crcmod: OK")
print("cryptography:", cryptography.__version__)
print("hoymiles_wifi: OK")
print("DTU import: OK")
PY

if [ -L "$SERVICE" ] || [ -f "$SERVICE" ]; then
    rm -f "$SERVICE"
elif [ -d "$SERVICE" ]; then
    echo "FEHLER: $SERVICE existiert bereits als echtes Verzeichnis."
    echo "Bitte zuerst prüfen, bevor es ersetzt wird."
    exit 3
fi
ln -s "$BASE/service" "$SERVICE"

/usr/bin/python3 - <<'PY'
from pathlib import Path
rc = Path('/data/rc.local')
line = 'ln -snf /data/hoymiles-pvinverter/service /service/hoymiles-pvinverter'
text = rc.read_text() if rc.exists() else '#!/bin/sh\n'
if line not in text:
    lines = text.splitlines()
    insert_at = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == 'exit 0':
            insert_at = i
            break
    lines.insert(insert_at, line)
    rc.write_text('\n'.join(lines) + '\n')
PY
chmod +x /data/rc.local

sv up "$SERVICE" 2>/dev/null || true
sleep 2
svstat "$SERVICE" 2>/dev/null || true

echo
echo "Installation abgeschlossen."
echo "Log:      tail -f /var/log/hoymiles-pvinverter/current"
echo "Status:   svstat $SERVICE"
echo "D-Bus:    dbus-spy"
echo "HMS-Test: cd $BASE && PYTHONPATH=$BASE/vendor python3 test_hms.py"
