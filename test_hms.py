#!/usr/bin/env python3
import asyncio
import configparser
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "vendor"))

from hoymiles_wifi.dtu import DTU


def inverter_ip():
    if len(sys.argv) > 1:
        return sys.argv[1]
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(BASE, "config.ini"))
    return cfg.get("hoymiles", "inverter_ip", fallback="192.168.178.176")


async def main():
    ip = inverter_ip()
    print(f"Teste HMS unter {ip} ...")
    data = await DTU(ip).async_get_real_data_new()
    print(data)
    if data:
        raw = getattr(data, "dtu_power", None)
        print("dtu_power raw:", raw)
        if raw is not None:
            print("power / 10:", float(raw) / 10.0, "W")


asyncio.run(main())
