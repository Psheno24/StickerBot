# StickerBot

Telegram-бот для подготовки стикеров из фотографий (например, сгенерированных в ChatGPT).

Отправь боту фото — он:
- удалит фон
- приведёт к размеру **512×512**
- сохранит в **WEBP** с прозрачностью, не больше **512 КБ**

Готовый файл можно загрузить в [@Stickers](https://t.me/Stickers) или добавить в свой стикерпак через Bot API.

## Быстрый старт

### 1. Создай бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot` и следуй инструкциям
3. Скопируй токен

### 2. Установка

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройка

```bash
cp .env.example .env
# Вставь токен в .env
```

### 4. Запуск

```bash
python bot.py
```

## Использование

1. Напиши боту `/start`
2. Отправь изображение как **фото** или **файл** (PNG/JPG/WEBP)
3. Получи готовый `sticker.webp`

## Требования Telegram к стикерам

| Параметр | Значение |
|----------|----------|
| Размер | 512×512 px |
| Формат | WEBP (статичный) |
| Макс. размер файла | 512 КБ |
| Фон | прозрачный |

## Стек

- [python-telegram-bot](https://python-telegram-bot.org/) — Telegram Bot API
- [rembg](https://github.com/danielgatis/rembg) — удаление фона
- [Pillow](https://python-pillow.org/) — обработка изображений

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather |
