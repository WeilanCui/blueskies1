#!/bin/sh
set -eu

standalone_dir=".next/standalone"

if [ ! -d "$standalone_dir" ]; then
  echo "Standalone build output not found; skipping asset sync."
  exit 0
fi

mkdir -p "$standalone_dir/.next"
rm -rf "$standalone_dir/.next/static" "$standalone_dir/public"
cp -R .next/static "$standalone_dir/.next/static"

if [ -d public ]; then
  cp -R public "$standalone_dir/public"
fi
