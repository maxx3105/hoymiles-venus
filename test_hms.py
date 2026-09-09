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
    if not data:
        return

    power = float(getattr(data, "dtu_power", 0)) / 10.0
    daily = float(getattr(data, "dtu_daily_energy", 0)) / 1000.0
    total = sum(float(getattr(pv, "energy_total", 0)) for pv in getattr(data, "pv_data", []) or []) / 1000.0

    print("\nInterpretierte Werte:")
    print(f"AC power:       {power:.1f} W")
    print(f"Daily energy:   {daily:.3f} kWh")
    print(f"Lifetime energy:{total:9.3f} kWh")

    sgs = getattr(data, "sgs_data", None)
    if sgs:
        ac = sgs[0]
        print(f"AC voltage:     {float(ac.voltage) / 10.0:.1f} V")
        print(f"AC frequency:   {float(ac.frequency) / 100.0:.2f} Hz")
        print(f"AC current:     {float(ac.current) / 100.0:.2f} A")
        print(f"Power factor:   {float(ac.power_factor) / 1000.0:.3f}")
        print(f"Temperature:    {float(ac.temperature) / 10.0:.1f} °C")
        print(f"Warning number: {int(ac.warning_number)}")
        print(f"Link status:    {int(ac.link_status)}")


asyncio.run(main())
