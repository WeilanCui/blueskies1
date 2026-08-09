#!/bin/sh
set -eu

sh scripts/install-container-deps.sh
echo "Starting Next.js dev server with hot reload..."
exec npm run dev
