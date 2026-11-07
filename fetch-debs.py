#!/usr/bin/env python3
r"""Download Network app debs for UOS from Ubiquiti's update API (what UOS itself uses).

Usage: ./fetch-debs.py [network-version] [--beta]   e.g. 11.0.99  (default: latest release)
Writes unifi.deb and unifi-matter-controller.deb, checksum-verified.

--beta needs your UOS instance's update token (the API only shows betas to signed-in consoles):
  UOS_FW_TOKEN=$(docker compose exec uos grep -oP '^token: \K\S+' /data/unifi-core/config/firmware.yaml) ./fetch-debs.py --beta
"""
import hashlib, json, os, sys, urllib.request

UA = {"User-Agent": "curl/8"}  # the CDN 403s Python's default UA
args = [a for a in sys.argv[1:] if a != "--beta"]
CHANNEL = "beta" if "--beta" in sys.argv else "release"  # beta also lists release builds
HEADERS = dict(UA)
if CHANNEL == "beta":
    if not os.environ.get("UOS_FW_TOKEN"):
        sys.exit("--beta needs UOS_FW_TOKEN (see --help)")
    HEADERS["Authorization"] = "Bearer token:" + os.environ["UOS_FW_TOKEN"]
API = "https://fw-update.ui.com/api/firmware?filter=eq~~channel~~" + CHANNEL + "&filter=eq~~platform~~uos-deb13-amd64&filter=eq~~product~~{}&limit=500"


def releases(product):
    with urllib.request.urlopen(urllib.request.Request(API.format(product), headers=HEADERS)) as r:
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


if "-h" in args or "--help" in args:
    sys.exit(__doc__)
want = args[0] if args else None
unifi = [f for f in releases("unifi") if not want or f["version"].lstrip("v").startswith(want + "-")]
if not unifi:
    sys.exit(f"unifi {want} not found")
fetch(unifi[0], "unifi.deb")
# ponytail: always latest matter-controller; pin it if unifi.deb ever Depends on an older exact version
fetch(releases("unifi-matter-controller")[0], "unifi-matter-controller.deb")
print("check: dpkg-deb -f unifi.deb Depends")
