#!/bin/bash

cd "$(dirname "$0")/desktop-electron-frontend"

npx vite --config vite.renderer.config.mjs --host 0.0.0.0 --port 5173
