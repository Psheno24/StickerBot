#!/bin/bash
set -e

APP_DIR="/opt/stickerbot"
SERVICE_NAME="stickerbot"

echo "=== Установка StickerBot ==="

# Зависимости системы
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

# Пользователь
id -u stickerbot &>/dev/null || useradd -r -s /bin/false stickerbot

# Директория
mkdir -p "$APP_DIR"

# Копируем файлы
cp bot.py image_processor.py requirements.txt "$APP_DIR/"

# Виртуальное окружение
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

# .env
if [ ! -f "$APP_DIR/.env" ]; then
    cp .env.example "$APP_DIR/.env"
    echo ""
    echo "⚠️  Укажи токен в $APP_DIR/.env"
    echo ""
fi

chown -R stickerbot:stickerbot "$APP_DIR"

# Systemd
cp deploy/stickerbot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "✅ Бот установлен и запущен!"
echo "   Статус: systemctl status $SERVICE_NAME"
echo "   Логи:   journalctl -u $SERVICE_NAME -f"
