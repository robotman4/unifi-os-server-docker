# UniFi OS Server in Docker

UniFi OS Server **6.0.19** + UniFi Network **11.0.99** as a Docker image, behind Traefik.

No Ubiquiti files are included. You download them, and the build turns them into an image.

## Setup

Needs: x86_64 Linux, Docker, and Traefik on an external network (`proxy_internal`, entrypoint `https`,
`insecureSkipVerify=true`).

```sh
# 1. UOS installer (linux-x64 6.0.19) from https://ui.com/download/releases/unifi-os-server
cp ~/Downloads/*-linux-x64-6.0.19-*-x64 installer.bin

# 2. Network debs, checksum-verified (version optional, default latest)
./fetch-debs.py 11.0.99

# 3. Set DOMAIN and UOS_SYSTEM_IP (IP devices use to reach the controller)
cp .env.example .env

# 4. Build + start (first boot takes a few minutes)
docker compose up -d --build
```

Open `https://$DOMAIN` and run the setup wizard.

## Update

Get a new `installer.bin` and/or run `./fetch-debs.py`, bump the image tag in `compose.yml`,
then `docker compose up -d --build`. Don't update from the UI (it won't work in Docker).

Betas: `./fetch-debs.py --beta` (needs your instance's update token, see `./fetch-debs.py --help`).

## How it works

- The installer is an ELF with a zip appended. The Dockerfile unzips `image.tar` and flattens it into a rootfs.
- Network 11.0.99 is installed on top of the bundled 10.6.106. There's no standalone 11.x deb.
  `fetch-debs.py` gets it from Ubiquiti's update API, the same place UOS gets it.
- Two fixes for the missing host-side "UOS Server Manager":
  - the setup wizard's legacy-Network check is patched to answer "no" (otherwise: blank page)
  - apps installed from the UI are restored from `/persistent/dpkg` when the container is recreated
- Data lives in named volumes (`data`, `persistent`, `srv`, ...). Network 11 stores its data in PostgreSQL inside the container.

## Credits

Built on [unihosted/unifi-os-server-docker](https://github.com/unihosted/unifi-os-server-docker) by UniHosted.
`uos-entrypoint.sh`, the layer-extraction logic in the `Dockerfile` and the compose layout come from there. Thank you!

Not affiliated with Ubiquiti Inc.
