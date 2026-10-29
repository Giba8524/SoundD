#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================="
echo "    SoundCloud Downloader для macOS       "
echo "=========================================="
echo ""
echo "Запуск приложения..."

if [ "$1" == "--web" ] || [ "$1" == "-w" ]; then
    echo "Запуск веб-версии в браузере..."
    python3 "$DIR/server.py" &
    SERVER_PID=$!
    sleep 1
    open "http://127.0.0.1:5678"
    wait $SERVER_PID
else
    # Launch native macOS app
    open "$DIR/SoundCloud Downloader.app"
fi
