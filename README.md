# Hoymiles HMS-800W-2T → Victron Venus OS

Native D-Bus integration for a **Hoymiles HMS-800W-2T** on a Victron GX device.

Validated on 2026-09-09 with:

- Cerbo GX / Venus OS
- Python 3.12 / ARMv7
- Hoymiles HMS-800W-2T
- Victron D-Bus service `com.victronenergy.pvinverter.hoymiles_hms800w2t`
- DeviceInstance `40`
- Position `1` = AC Output
- driver version `1.1.1`

The inverter is polled directly over the integrated Hoymiles WiFi DTU. No NAS and no MQTT bridge are required.

## Validated telemetry

The local HMS response was validated against real device data. The driver uses:

- `dtu_power / 10` → AC power in W
- `sgs_data.voltage / 10` → AC voltage in V
- `sgs_data.frequency / 100` → Hz
- `sgs_data.current / 100` → A
- `sgs_data.power_factor / 1000` → power factor
- `sgs_data.temperature / 10` → °C
- energy counters are Wh and are divided by 1000 for kWh

A real sample was internally consistent: 234.0 V, 49.99 Hz, 0.53 A, PF 0.999 and 116.4 W AC. PV daily energy from both inputs summed exactly to the DTU daily energy counter.

Runtime validation also showed stable polling every 35 seconds with live values such as 175.6 W / 238.1 V / 0.76 A and 330.1 W / 239.1 V / 1.39 A.

Hoymiles `warning_number` is exposed only as a diagnostic value. It is not mapped to Victron `/ErrorCode` until the warning-code semantics are verified.

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

`install.sh` does **not** install pip. It downloads pinned, hash-verified packages into `/data/hoymiles-pvinverter/vendor`:

- hoymiles-wifi 0.5.6
- protobuf 6.31.1
- crcmod 1.7, Python-3 implementation

The Cerbo's existing `cryptography` package is used.

`hoymiles-wifi 0.5.6` contains protobuf-generated modules built with protobuf 6.31.1, therefore the bundled runtime is pinned to 6.31.1 as well.

## Service management on Venus OS

Venus OS uses daemontools-style supervision. Useful commands:

```sh
svstat /service/hoymiles-pvinverter
svc -t /service/hoymiles-pvinverter
```

`svc -t` terminates the current process and `supervise` starts it again automatically.

Logging uses `multilog` and writes to:

```text
/var/log/hoymiles-pvinverter/current
```

## Test

Stop any old NAS bridge first to avoid double PV reporting and parallel local polling. Then:

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

Process version check:

```sh
dbus -y com.victronenergy.pvinverter.hoymiles_hms800w2t /Mgmt/ProcessVersion GetValue
```

Published telemetry includes AC power, voltage, current, frequency, power factor, forward energy, daily energy, temperature, warning number and link status.

## Configuration

Edit `config.ini` before installation if the HMS IP differs.

`position = 1` means AC Output, matching an HMS connected to MultiPlus-II AC Out.

## Notes

- `/data` survives normal Venus OS updates.
- Polling is intentionally kept at 35 seconds.
- Power limiting/control is **not** implemented. This driver is telemetry-only.
- If another service (for example an older MQTT-PV bridge) reports the same inverter, disable that duplicate source to avoid double-counting PV power.
