# syntax=docker/dockerfile:1
# Based on https://github.com/unihosted/unifi-os-server-docker (UniHosted), adapted for UOS 6.0
# Build context needs (see README.md for where to get them):
#   installer.bin                UOS 6.0.19 linux-x64 installer
#   unifi.deb                    Network app 11.0.99 (uos-deb13)
#   unifi-matter-controller.deb  dependency of unifi.deb, not in the base image

FROM ubuntu:22.04 AS extractor

RUN apt-get update && apt-get install -y --no-install-recommends unzip jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
# The installer is an ELF with a zip appended; unzip exits 1 on the leading bytes.
RUN --mount=type=bind,source=installer.bin,target=/installer.bin \
    unzip -o /installer.bin image.tar || [ $? -eq 1 ]

RUN /bin/bash <<'EXTRACT'
set -eo pipefail
mkdir oci
tar xf image.tar -C oci/
rm image.tar
MANIFEST=$(jq -r '.manifests[0].digest' oci/index.json | cut -d: -f2)
mkdir /rootfs
jq -r '.layers[].digest' "oci/blobs/sha256/$MANIFEST" | cut -d: -f2 | \
while read -r layer; do
    echo "Extracting layer $layer"
    tar xf "oci/blobs/sha256/$layer" -C /rootfs
    find /rootfs -name '.wh.*' 2>/dev/null | while read -r wh; do
        base=$(basename "$wh"); dir=$(dirname "$wh")
        if [ "$base" = ".wh..wh..opq" ]; then
            find "$dir" -mindepth 1 -maxdepth 1 ! -name '.wh..wh..opq' -exec rm -rf {} +
        else
            rm -rf "$dir/${base#.wh.}"
        fi
        rm -f "$wh"
    done
done
EXTRACT

COPY uos-entrypoint.sh /rootfs/root/uos-entrypoint.sh
RUN chmod +x /rootfs/root/uos-entrypoint.sh

FROM scratch

COPY --from=extractor /rootfs /

# Upgrade the bundled Network app (10.6.106) to 11.0.99.
# Ubiquiti's dpkg hooks log via systemd-cat, which needs journald; park them during the build.
RUN --mount=type=bind,target=/debs <<'INSTALL'
set -e
hooks="/etc/dpkg/dpkg.cfg.d/015-ubnt-dpkg-status /etc/dpkg/dpkg.cfg.d/020-ubnt-dpkg-cache"
mkdir /tmp/hooks && mv $hooks /tmp/hooks/
dpkg -i /debs/unifi-matter-controller.deb /debs/unifi.deb
mv /tmp/hooks/* /etc/dpkg/dpkg.cfg.d/ && rmdir /tmp/hooks
dpkg-query -W unifi | grep -q '11.0.99'
INSTALL

# The setup wizard asks the host-side "UOS Server Manager" (uosserver-service, connects in over UCP4)
# whether a legacy Network install exists. There is no manager in Docker, so the call 500s and the
# wizard never renders. Answer "no" locally. Fails the build if the call is gone/renamed.
RUN f=/usr/share/unifi-core/app/service.js \
    && grep -q 'await xa("hasLegacyNet",{})' $f \
    && sed -i 's/await xa("hasLegacyNet",{})/({body:{hasLegacyNet:false}})/' $f

ARG UOS_SERVER_VERSION="6.0.19"
ENV UOS_SERVER_VERSION="${UOS_SERVER_VERSION}" \
    APP_VERSION="${UOS_SERVER_VERSION}" \
    APP_MODEL="UOSSERVER" \
    PRODUCT_NAME="UniFi OS Server"

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/root/uos-entrypoint.sh"]
