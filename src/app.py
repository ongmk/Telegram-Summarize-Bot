import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from logzero import logger
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from helpers.utils import load_json

load_dotenv()


async def summarize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_message = await update.message.reply_text("Summarizing headlines...")
    raw = load_json("tmp/summaries.json")
    timestamp = datetime.strptime(raw["timestamp"], "%Y%m%d_%H%M%S")
    summaries = raw["summaries"]

    one_day_ago = datetime.now() - timedelta(days=1)
    if not summaries or timestamp < one_day_ago:
        await response_message.edit_text("Cannot find headlines to summarize.")
        return None

    for chunks in summaries:
        text = chunks[0]
        topic_message = await update.message.reply_text(
            text, parse_mode="MarkdownV2", disable_web_page_preview=True
        )
        for chunk in chunks[1:]:
            text += chunk
            await topic_message.edit_text(text, parse_mode="MarkdownV2")
    return None


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "歡迎使用香港日報 Bot！我每天會為您提供新聞摘要和相關連結。\n"
        "Welcome to the daily_hk_news_bot! I'll provide you with daily news summaries and relevant links."
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=welcome_message
    )
    return None


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Log the error.

    This function is called when an error occurs.
    It logs the error to the console.
    """

    logger.error(update)
    logger.error(f"{type(context.error).__name__}: {context.error}")


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    logger.info(user_input)
    await update.message.reply_text(user_input, parse_mode="MarkdownV2")
    return None


def main():
    load_dotenv()
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("summarize", summarize_handler))
    application.add_handler(MessageHandler(filters.TEXT, echo_handler))
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot started successfully.")


if __name__ == "__main__":
    main()
