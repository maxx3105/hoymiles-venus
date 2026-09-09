# Hoymiles HMS-800W-2T → Victron Venus OS

Native D-Bus integration for a **Hoymiles HMS-800W-2T** on a Victron GX device (tested target: Cerbo GX / Venus OS with Python 3.12, ARMv7).

The inverter is polled directly over the integrated Hoymiles WiFi DTU. No NAS and no MQTT bridge are required.

## Current scope

The first version deliberately mirrors the proven NAS bridge and uses only `RealDataNew.dtu_power` for PV power. On the target HMS-800W-2T this value is divided by 10, matching the existing working bridge. AC voltage is currently a configurable fallback (230 V) and current is calculated from P/V.

## Defaults

- HMS IP: `192.168.178.176`
- Poll interval: `35 s`
- Position: `1` = AC Output
- Max power: `800 W`
- Requested DeviceInstance: `40`

### DeviceInstance collision handling

`40` is only the requested starting value. The driver persists
`/Settings/Devices/hoymiles_hms800w2t/ClassAndVrmInstance` through Victron `SettingsDevice`.
Venus OS `localsettings` rejects duplicate class+instance combinations and assigns the next free instance automatically.

## Install on Cerbo GX

### Variante A: mit `git` (falls vorhanden)

```sh
cd /data
git clone https://github.com/maxx3105/hoymiles-venus.git hoymiles-pvinverter
cd /data/hoymiles-pvinverter
chmod +x install.sh
./install.sh
```

### Variante B: ohne `git`

```sh
cd /data
rm -rf hoymiles-pvinverter hoymiles-venus-main
wget -qO- https://github.com/maxx3105/hoymiles-venus/archive/refs/heads/main.tar.gz | tar xz
mv hoymiles-venus-main hoymiles-pvinverter
cd /data/hoymiles-pvinverter
chmod +x install.sh
./install.sh
```

The installation directory is intentionally `/data/hoymiles-pvinverter`, because `/data` survives normal Venus OS firmware updates.

`install.sh` does **not** install pip. It downloads pinned, hash-verified pure-Python packages into `/data/hoymiles-pvinverter/vendor`:

- hoymiles-wifi 0.5.6
- protobuf 5.29.6
- crcmod 1.7 (pure Python)

The Cerbo's existing `cryptography` package is used.

## Test before enabling the old bridge

Stop the NAS bridge first to avoid double PV reporting and parallel local polling. Then:

```sh
cd /data/hoymiles-pvinverter
PYTHONPATH=/data/hoymiles-pvinverter/vendor python3 test_hms.py
```

Service status:

```sh
svstat /service/hoymiles-pvinverter
```

Log:

```sh
tail -f /var/log/hoymiles-pvinverter/current
```

D-Bus:

```sh
dbus-spy
```

Expected service:

```text
com.victronenergy.pvinverter.hoymiles_hms800w2t
```

## Configuration

Edit `config.ini` before installation if the HMS IP differs.

`position = 1` means AC Output, matching an HMS connected to MultiPlus-II AC Out.

## Notes

- `/data` survives normal Venus OS updates.
- Polling is intentionally kept at 35 seconds.
- Power limiting/control is **not** implemented. This driver is telemetry-only.
- Additional HMS telemetry should only be added after field scaling has been validated against the target firmware.
