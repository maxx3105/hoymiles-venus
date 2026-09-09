#!/usr/bin/env python3
"""Install pinned pure-Python dependencies into ./vendor without pip."""
from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
VENDOR = BASE / "vendor"

PACKAGES = {
    "hoymiles_wifi": {
        "url": "https://files.pythonhosted.org/packages/21/af/668a54204944ec31c33319a6c6a88e2ecccb733c839df7b4c00cd58681b8/hoymiles_wifi-0.5.6-py3-none-any.whl",
        "sha256": "ded707ff02587db2c7c3c2a8988424b711a27ec3683e1bc78c6efe2dbb12d375",
        "kind": "wheel",
    },
    "protobuf": {
        "url": "https://files.pythonhosted.org/packages/5a/cb/e3065b447186cb70aa65acc70c86baf482d82bf75625bf5a2c4f6919c6a3/protobuf-5.29.6-py3-none-any.whl",
        "sha256": "6b9edb641441b2da9fa8f428760fc136a49cf97a52076010cf22a2ff73438a86",
        "kind": "wheel",
    },
    "crcmod": {
        "url": "https://files.pythonhosted.org/packages/6b/b0/e595ce2a2527e169c3bcd6c33d2473c1918e0b7f6826a043ca1245dd4e5b/crcmod-1.7.tar.gz",
        "sha256": "dc7051a0db5f2bd48665a990d3ec1cc305a466a77358ca4492826f41f283601e",
        "kind": "crcmod-sdist",
    },
}


def fetch(url: str, dest: Path, expected_sha256: str) -> None:
    print(f"Download: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "hoymiles-venus-installer/1.0"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=60) as src, dest.open("wb") as out:
        while True:
            chunk = src.read(1024 * 128)
            if not chunk:
                break
            out.write(chunk)
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected_sha256:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"SHA256 mismatch for {url}: {actual}")


def extract_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as zf:
        zf.extractall(VENDOR)


def extract_crcmod(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="crcmod-") as td:
        td_path = Path(td)
        with tarfile.open(path, "r:gz") as tf:
            tf.extractall(td_path, filter="data")
        candidates = list(td_path.glob("crcmod-*/crcmod"))
        if len(candidates) != 1:
            raise RuntimeError("crcmod package directory not found in source archive")
        target = VENDOR / "crcmod"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(candidates[0], target)


def main() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name in ["hoymiles_wifi", "google", "crcmod"]:
        p = VENDOR / name
        if p.is_dir():
            shutil.rmtree(p)
    for p in VENDOR.glob("hoymiles_wifi-*.dist-info"):
        shutil.rmtree(p)
    for p in VENDOR.glob("protobuf-*.dist-info"):
        shutil.rmtree(p)

    with tempfile.TemporaryDirectory(prefix="hoymiles-venus-") as td:
        td_path = Path(td)
        for name, meta in PACKAGES.items():
            suffix = ".whl" if meta["kind"] == "wheel" else ".tar.gz"
            archive = td_path / f"{name}{suffix}"
            fetch(meta["url"], archive, meta["sha256"])
            if meta["kind"] == "wheel":
                extract_wheel(archive)
            else:
                extract_crcmod(archive)

    print(f"Dependencies installed to {VENDOR}")


if __name__ == "__main__":
    main()
