#!/usr/bin/env bash
# Install gVisor on gmt and register it with Docker as the runtime "runsc", which the launcher
# starts every conversion's sandbox in (ADR 0004, docs/DEPLOY.md).
#
#   scp scripts/install-gvisor.sh gmt:/tmp/ && ssh -t gmt sudo bash /tmp/install-gvisor.sh
#
# Docker is reloaded, not restarted, so the containers already running (Chatbot's) carry on, and
# keep their own runtime: runsc is added beside runc and nvidia, never made the default.
# Running it again changes nothing that is already in place.
set -euo pipefail

# The release is pinned, and its checksum with it: gvisor.dev's tarball for 2026-10-05, released
# on 2026-10-08. The checksum is checked against this copy, not one downloaded beside the file.
RELEASE=20261005.0
SHA512=27fed731b432d6a39d908956623fd273979fda66b3ccf4b9c12413ea417c516e18a9dc3cced403fb28efe495d64dce4251f51cf8c4d9f4a72f9833bd96b6bb35
URL="https://storage.googleapis.com/gvisor/releases/release/$RELEASE/x86_64/gvisor.tar.zstd"
DAEMON=/etc/docker/daemon.json
# A small image to try the runtime with, pinned by digest.
PROBE=alpine@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b

[ "$(id -u)" = 0 ] || { echo "run it as root: sudo bash $0"; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo "this script installs the x86_64 build only"; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
echo "downloading gVisor $RELEASE..."
curl -fsSL -o "$work/gvisor.tar.zstd" "$URL"
echo "$SHA512  $work/gvisor.tar.zstd" | sha512sum -c --quiet -
# As gvisor.dev installs it: runsc, its containerd shim, and the gvisor-bin folder runsc needs
# beside it.
tar --zstd -xf "$work/gvisor.tar.zstd" -C /usr/local/bin
/usr/local/bin/runsc --version | head -1

# runsc install adds runsc to Docker's runtimes. The file is kept as it was, to put back if the
# runtimes already there do not survive.
[ -f "$DAEMON" ] && cp -a "$DAEMON" "$DAEMON.before-gvisor"
/usr/local/bin/runsc install
if ! python3 - "$DAEMON" "$DAEMON.before-gvisor" <<'PY'
import json, sys
now = json.load(open(sys.argv[1]))
try:
    before = json.load(open(sys.argv[2]))
except FileNotFoundError:
    before = {}
runtimes = now.get("runtimes", {})
lost = set(before.get("runtimes", {})) - set(runtimes)
sys.exit(1 if lost or "runsc" not in runtimes or now.get("default-runtime") != before.get("default-runtime") else 0)
PY
then
  [ -f "$DAEMON.before-gvisor" ] && cp -a "$DAEMON.before-gvisor" "$DAEMON"
  echo "runsc install changed Docker's settings in a way it should not have; $DAEMON is put back as it was"
  exit 1
fi

# A reload (SIGHUP) takes the new runtime without restarting Docker or any container.
systemctl reload docker
for _ in $(seq 30); do
  docker info --format '{{range $name, $_ := .Runtimes}}{{$name}} {{end}}' | grep -qw runsc && break
  sleep 1
done
docker info --format 'runtimes: {{range $name, $_ := .Runtimes}}{{$name}} {{end}}default: {{.DefaultRuntime}}'
echo "trying a container in gVisor:"
docker run --rm --runtime=runsc --network none "$PROBE" dmesg | head -3
echo "gVisor $RELEASE is installed and registered as the runtime runsc"
