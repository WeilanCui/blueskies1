#!/bin/sh
set -eu

sh scripts/install-container-deps.sh
exec npm run dev -- --hostname 0.0.0.0
