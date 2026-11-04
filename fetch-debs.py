#!/usr/bin/env python3
"""Download Network app debs for UOS from Ubiquiti's update API (what UOS itself uses).

Usage: ./fetch-debs.py [network-version]   e.g. 11.0.99  (default: latest release)
Writes unifi.deb and unifi-matter-controller.deb, checksum-verified.
"""
import hashlib, json, sys, urllib.request

UA = {"User-Agent": "curl/8"}  # the CDN 403s Python's default UA
API = "https://fw-update.ui.com/api/firmware?filter=eq~~channel~~release&filter=eq~~platform~~uos-deb13-amd64&filter=eq~~product~~{}&limit=500"


def releases(product):
    with urllib.request.urlopen(urllib.request.Request(API.format(product), headers=UA)) as r:
        fw = json.load(r)["_embedded"]["firmware"]
    key = lambda f: [int(x) for x in f["version"].lstrip("v").split("-")[0].split(".")]
    return sorted(fw, key=key, reverse=True)


def fetch(f, out):
    url = f["_links"]["data"]["href"]
    print(f"{f['product']} {f['version']} <- {url}")
    h = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(out, "wb") as o:
        while chunk := r.read(1 << 20):
            h.update(chunk)
            o.write(chunk)
    if h.hexdigest() != f["sha256_checksum"]:
        sys.exit(f"checksum mismatch for {out}")


want = sys.argv[1] if len(sys.argv) > 1 else None
unifi = [f for f in releases("unifi") if not want or f["version"].lstrip("v").startswith(want + "-")]
if not unifi:
    sys.exit(f"unifi {want} not found")
fetch(unifi[0], "unifi.deb")
# ponytail: always latest matter-controller; pin it if unifi.deb ever Depends on an older exact version
fetch(releases("unifi-matter-controller")[0], "unifi-matter-controller.deb")
print("check: dpkg-deb -f unifi.deb Depends")
