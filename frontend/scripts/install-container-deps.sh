#!/bin/sh
set -eu

if [ "${FRONTEND_INSTALL_MODE:-install}" = "ci" ]; then
  npm ci --include=optional --no-audit --no-fund
else
  npm install --include=optional --no-audit --no-fund
fi

case "$(uname -m)" in
  aarch64)
    npm install --no-save --no-audit --no-fund \
      @tailwindcss/oxide-linux-arm64-gnu \
      lightningcss-linux-arm64-gnu
    ;;
  x86_64)
    npm install --no-save --no-audit --no-fund \
      @tailwindcss/oxide-linux-x64-gnu \
      lightningcss-linux-x64-gnu
    ;;
esac
