#!/usr/bin/env python3
"""Hoymiles HMS-800W-2T -> Victron Venus OS native D-Bus bridge.

This intentionally starts with the same proven signal as the previous NAS
bridge: RealDataNew.dtu_power, scaled by 10 as observed on the HMS-800W-2T.
Additional telemetry can be added after validating field scaling on the target
firmware.
"""
from __future__ import annotations

import asyncio
import configparser
import glob
import logging
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(BASE, "vendor")
if os.path.isdir(VENDOR):
    sys.path.insert(0, VENDOR)

VELIB = None
for candidate in [
    "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
    "/opt/victronenergy/dbus-vebus-to-pvinverter/ext/velib_python",
] + glob.glob("/opt/victronenergy/*/ext/velib_python"):
    if os.path.isfile(os.path.join(candidate, "vedbus.py")) and os.path.isfile(os.path.join(candidate, "settingsdevice.py")):
        VELIB = candidate
        sys.path.insert(0, candidate)
        break

if not VELIB:
    raise SystemExit("Victron velib_python (vedbus.py/settingsdevice.py) not found")

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from settingsdevice import SettingsDevice
from vedbus import VeDbusService
from hoymiles_wifi.dtu import DTU

LOG = logging.getLogger("hoymiles-pvinverter")


def load_config():
    cfg = configparser.ConfigParser()
    path = os.path.join(BASE, "config.ini")
    if not cfg.read(path):
        raise SystemExit(f"Config not found: {path}")
    return {
        "ip": cfg.get("hoymiles", "inverter_ip"),
        "interval": max(35, cfg.getint("hoymiles", "poll_interval", fallback=35)),
        "requested_instance": cfg.getint("victron", "requested_device_instance", fallback=40),
        "position": cfg.getint("victron", "position", fallback=1),
        "max_power": cfg.getfloat("victron", "max_power", fallback=800.0),
        "name": cfg.get("victron", "custom_name", fallback="Hoymiles HMS-800W-2T"),
        "voltage": cfg.getfloat("victron", "fallback_voltage", fallback=230.0),
    }


def fmt_w(_path, value):
    return "---" if value is None else f"{float(value):.0f} W"


def fmt_v(_path, value):
    return "---" if value is None else f"{float(value):.1f} V"


def fmt_a(_path, value):
    return "---" if value is None else f"{float(value):.2f} A"


def get_system_bus():
    return dbus.SystemBus()


class PersistentSettings:
    def __init__(self, cfg):
        requested = cfg["requested_instance"]
        supported = {
            "vrm_instance": [
                "/Settings/Devices/hoymiles_hms800w2t/ClassAndVrmInstance",
                f"pvinverter:{requested}", "", "", 0,
            ],
            "custom_name": [
                "/Settings/Devices/hoymiles_hms800w2t/CustomName",
                cfg["name"], "", "", 0,
            ],
            "position": [
                "/Settings/Devices/hoymiles_hms800w2t/Position",
                cfg["position"], 0, 2, 0,
            ],
        }
        self.settings = SettingsDevice(
            bus=get_system_bus(),
            supportedSettings=supported,
            eventCallback=self._on_change,
        )

    def _on_change(self, setting, oldvalue, newvalue):
        LOG.info("Setting changed: %s: %r -> %r; restarting service", setting, oldvalue, newvalue)
        os._exit(1)

    @property
    def instance(self):
        value = str(self.settings["vrm_instance"])
        role, instance = value.split(":", 1)
        if role != "pvinverter":
            raise RuntimeError(f"Invalid ClassAndVrmInstance: {value}")
        return int(instance)

    @property
    def custom_name(self):
        return str(self.settings["custom_name"])

    @property
    def position(self):
        return int(self.settings["position"])


class PvService:
    def __init__(self, cfg, settings):
        self.cfg = cfg
        self.update_index = 0
        self.service = VeDbusService("com.victronenergy.pvinverter.hoymiles_hms800w2t", register=False)
        s = self.service
        s.add_path("/Mgmt/ProcessName", __file__)
        s.add_path("/Mgmt/ProcessVersion", "1.0.0")
        s.add_path("/Mgmt/Connection", f"Hoymiles WiFi {cfg['ip']}")
        s.add_path("/DeviceInstance", settings.instance)
        s.add_path("/ProductId", 0xFFFF)
        s.add_path("/ProductName", "Hoymiles HMS-800W-2T")
        s.add_path("/CustomName", settings.custom_name)
        s.add_path("/Connected", 0)
        s.add_path("/FirmwareVersion", "hoymiles-wifi 0.5.6")
        s.add_path("/HardwareVersion", "HMS-800W-2T")
        s.add_path("/Position", settings.position)
        s.add_path("/Serial", "")
        s.add_path("/UpdateIndex", 0)
        s.add_path("/StatusCode", 8)
        s.add_path("/ErrorCode", 0)
        s.add_path("/Ac/MaxPower", cfg["max_power"], gettextcallback=fmt_w)
        s.add_path("/Ac/Power", 0.0, gettextcallback=fmt_w)
        s.add_path("/Ac/L1/Power", 0.0, gettextcallback=fmt_w)
        s.add_path("/Ac/L1/Voltage", cfg["voltage"], gettextcallback=fmt_v)
        s.add_path("/Ac/L1/Current", 0.0, gettextcallback=fmt_a)
        s.register()

    def _tick(self):
        self.update_index = (self.update_index + 1) % 256
        self.service["/UpdateIndex"] = self.update_index

    def update(self, response):
        try:
            raw = getattr(response, "dtu_power", 0)
            power = max(0.0, float(raw) / 10.0)
        except (TypeError, ValueError):
            power = 0.0
        voltage = self.cfg["voltage"]
        current = power / voltage if voltage > 0 else 0.0

        serial = str(getattr(response, "device_serial_number", "") or "")
        self.service["/Connected"] = 1
        self.service["/StatusCode"] = 7 if power > 0 else 8
        self.service["/ErrorCode"] = 0
        self.service["/Ac/Power"] = power
        self.service["/Ac/L1/Power"] = power
        self.service["/Ac/L1/Voltage"] = voltage
        self.service["/Ac/L1/Current"] = current
        if serial:
            self.service["/Serial"] = serial
        self._tick()
        LOG.info("HMS: raw dtu_power=%r -> %.1f W", raw, power)
        return False

    def disconnected(self, error):
        self.service["/Connected"] = 0
        self.service["/StatusCode"] = 10
        self.service["/Ac/Power"] = 0.0
        self.service["/Ac/L1/Power"] = 0.0
        self.service["/Ac/L1/Current"] = 0.0
        self._tick()
        LOG.warning("Hoymiles not reachable: %s", error)
        return False


async def poll(cfg, service):
    dtu = DTU(cfg["ip"])
    while True:
        started = time.monotonic()
        try:
            response = await dtu.async_get_real_data_new()
            if response:
                GLib.idle_add(service.update, response)
            else:
                GLib.idle_add(service.disconnected, "empty response")
        except Exception as exc:
            GLib.idle_add(service.disconnected, str(exc))
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(1.0, cfg["interval"] - elapsed))


def poll_thread(cfg, service):
    asyncio.run(poll(cfg, service))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    DBusGMainLoop(set_as_default=True)
    settings = PersistentSettings(cfg)
    service = PvService(cfg, settings)
    LOG.info(
        "Starting HMS -> Venus: IP=%s instance=%s position=%s interval=%ss velib=%s",
        cfg["ip"], settings.instance, settings.position, cfg["interval"], VELIB,
    )
    threading.Thread(target=poll_thread, args=(cfg, service), daemon=True).start()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
