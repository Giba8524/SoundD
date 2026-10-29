#!/bin/bash
# Launcher for SoundCloud Downloader on macOS
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Launch native macOS app bundle
open "$DIR/SoundCloud Downloader.app"
