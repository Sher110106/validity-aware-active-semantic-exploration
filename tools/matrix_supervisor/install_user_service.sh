#!/usr/bin/env bash
set -euo pipefail

WORKSPACE=/home/sher/active-semantic-perception-workspace
SOURCE="$WORKSPACE/tools/matrix_supervisor/asp-matrix-supervisor.service"
TARGET="$HOME/.config/systemd/user/asp-matrix-supervisor.service"

mkdir -p "$(dirname "$TARGET")"
install -m 0644 "$SOURCE" "$TARGET"

# A user service otherwise disappears when the last SSH session closes and
# will not start after a reboot. Enabling linger for the current user is the
# persistence mechanism; this does not grant new privileges.
loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now asp-matrix-supervisor.service

systemctl --user --no-pager status asp-matrix-supervisor.service
loginctl show-user "$USER" -p Linger
