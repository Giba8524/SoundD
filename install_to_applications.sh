#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="SoundCloud Downloader.app"

echo "Установка $APP_NAME в папку /Applications..."

# Remove any duplicate from ~/Applications
rm -rf "$HOME/Applications/$APP_NAME" 2>/dev/null || true

if cp -R "$DIR/$APP_NAME" "/Applications/"; then
    echo "Приложение успешно установлено в /Applications!"
    echo "Теперь вы можете открывать его через Spotlight (Cmd + Пробел) или Launchpad."
else
    echo "Установка в /Applications требует прав администратора. Устанавливаем в ~/Applications..."
    mkdir -p "$HOME/Applications"
    cp -R "$DIR/$APP_NAME" "$HOME/Applications/"
    echo "Приложение установлено в $HOME/Applications!"
fi
