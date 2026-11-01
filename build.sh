#!/usr/bin/env bash
set -e

# ==============================================================================
# SoundCloud Downloader for macOS - Build & Packaging Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="SoundCloud Downloader"
APP_BUNDLE="${PROJECT_DIR}/${APP_NAME}.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "🚀 Building ${APP_NAME}..."

# 1. Install / update dependencies
echo "📦 Checking Python dependencies..."
python3 -m pip install --user -q -r "${PROJECT_DIR}/requirements.txt" || true

# 2. Prepare bundle directories
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}/static"

# 3. Compile Swift native wrapper
echo "🔨 Compiling Swift native wrapper (arm64 + x86_64 compatible)..."
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
  swiftc -O -target arm64-apple-macos12.0 "${PROJECT_DIR}/main.swift" -o "${MACOS_DIR}/${APP_NAME}"
else
  swiftc -O "${PROJECT_DIR}/main.swift" -o "${MACOS_DIR}/${APP_NAME}"
fi
chmod +x "${MACOS_DIR}/${APP_NAME}"

# 4. Synchronize resources
echo "📋 Synchronizing backend & static web assets..."
cp -f "${PROJECT_DIR}/engine.py" "${RESOURCES_DIR}/engine.py"
cp -f "${PROJECT_DIR}/server.py" "${RESOURCES_DIR}/server.py"
cp -rf "${PROJECT_DIR}/static/"* "${RESOURCES_DIR}/static/"

if [ -f "${PROJECT_DIR}/AppIcon.icns" ]; then
  cp -f "${PROJECT_DIR}/AppIcon.icns" "${RESOURCES_DIR}/AppIcon.icns"
  echo "🎨 AppIcon synchronized."
elif [ -f "${RESOURCES_DIR}/AppIcon.icns" ]; then
  echo "🎨 AppIcon preserved."
fi

# 5. Optional distribution archive
if [ "$1" = "--dist" ]; then
  DIST_ZIP="${PROJECT_DIR}/SoundCloud-Downloader-macOS.zip"
  echo "📦 Creating release distribution: ${DIST_ZIP}..."
  rm -f "${DIST_ZIP}"
  cd "${PROJECT_DIR}"
  ditto -c -k --sequesterRsrc --keepParent "${APP_NAME}.app" "${DIST_ZIP}"
  echo "✅ Release ZIP ready: ${DIST_ZIP}"
fi

echo "✅ Build complete! App located at: ${APP_BUNDLE}"
