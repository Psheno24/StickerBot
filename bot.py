import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from image_processor import process_sticker_image

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WELCOME = (
    "Привет! Отправь мне фото (как фото или файл), и я подготовлю стикер:\n"
    "• Удалю фон\n"
    "• Размер 512×512\n"
    "• Формат WEBP, до 512 КБ\n\n"
    "Готовый файл можно загрузить в @Stickers или использовать в своём стикерпаке."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    last = context.user_data.get("last_sticker")
    if not last:
        await update.message.reply_text("Нет сохранённого стикера. Сначала отправь фото.")
        return
    await update.message.reply_document(
        document=last,
        filename="sticker.webp",
        caption="Последний стикер",
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    status = await message.reply_text("Обрабатываю изображение…")

    try:
        if message.photo:
            file = await message.photo[-1].get_file()
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
            file = await message.document.get_file()
        else:
            await status.edit_text("Отправь изображение как фото или файл (PNG/JPG/WEBP).")
            return

        image_bytes = await file.download_as_bytearray()
        result = process_sticker_image(bytes(image_bytes))
        size_kb = len(result) / 1024

        await status.delete()
        context.user_data["last_sticker"] = result
        await message.reply_document(
            document=result,
            filename="sticker.webp",
            caption=f"Готово! {size_kb:.0f} КБ · 512×512 · прозрачный фон\n/save — скачать ещё раз",
        )
    except ValueError as exc:
        await status.edit_text(str(exc))
    except Exception:
        logger.exception("Failed to process image")
        await status.edit_text("Не удалось обработать изображение. Попробуй другое фото.")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Укажи TELEGRAM_BOT_TOKEN в .env или переменных окружения.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("save", save_command))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
