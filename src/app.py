# -*- coding: utf-8 -*-

import datetime
import os

from dotenv import load_dotenv
from logzero import logger
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from core.config import Config
from core.summarize import summarize
from helpers.utils import (
    datetime,
    datetime_to_str,
    load_json,
    save_as_json,
    str_to_datetime,
)

load_dotenv()


async def warn(text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot.send_message(Config.ADMIN_CHAT_ID, f"[Warning] {text}")
    logger.warning(text)
    return None


async def send_news_to_chat(
    chat_id: str,
    context: ContextTypes.DEFAULT_TYPE,
    last_sent="1900-01-01 00:00:00",
    by_chunks=False,
) -> None:
    summaries = load_json(Config.SUMMARIES_FILE)
    last_sent = str_to_datetime(last_sent)
    last_updated = str_to_datetime(summaries["last_updated"])
    summaries = summaries["summaries"]

    if not summaries:
        warn("Cannot find headlines to summarize.")
        return None
    if last_sent > last_updated:
        warn(f"No new news for {chat_id}. {last_sent=}, {last_updated=}")
        return None
    for chunks in summaries:
        if by_chunks:
            text = chunks[0]
            topic_message = await context.bot.send_message(
                chat_id, text, parse_mode="MarkdownV2"
            )
            for chunk in chunks[1:]:
                text += chunk
                await topic_message.edit_text(text, parse_mode="MarkdownV2")
        else:
            text = "".join(chunks)
            await context.bot.send_message(chat_id, text, parse_mode="MarkdownV2")

    subscribers = load_json(Config.SUBSCRIBER_FILE)
    subscribers[chat_id] = datetime_to_str(datetime.datetime.now())
    save_as_json(subscribers, Config.SUBSCRIBER_FILE)
    return None


def is_subscriber(chat_id: str) -> bool:
    if chat_id in load_json(Config.SUBSCRIBER_FILE):
        return True
    return False


def subscribe(chat_id: str) -> bool:
    subscribers = load_json(Config.SUBSCRIBER_FILE)
    subscribers[chat_id] = "1900-01-01 00:00:00"
    save_as_json(subscribers, Config.SUBSCRIBER_FILE)
    return None


def unsubscribe(chat_id: str) -> bool:
    subscribers = load_json(Config.SUBSCRIBER_FILE)
    subscribers.pop(chat_id)
    save_as_json(subscribers, Config.SUBSCRIBER_FILE)
    return None


async def send_news_to_all_subscribers(context: ContextTypes.DEFAULT_TYPE) -> None:
    for chat_id, last_sent in load_json(Config.SUBSCRIBER_FILE).items():
        await send_news_to_chat(chat_id, context, last_sent)
    return None


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    if is_subscriber(chat_id):
        return
    subscribe(chat_id)
    await update.effective_message.reply_text("Subscribed.")
    await send_news_to_chat(chat_id, context, by_chunks=True)
    return


async def unsubscribe_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = str(update.effective_message.chat_id)
    if is_subscriber(chat_id):
        unsubscribe(chat_id)
        await update.effective_message.reply_text("Unsubscribed.")
    return


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = "歡迎使用香港日報 Bot！我每天會為您提供新聞摘要和相關連結。"
    await update.message.reply_text(
        welcome_message,
    )
    await help_handler(update, context)
    return None


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_message.chat_id)
    if is_subscriber(chat_id):
        message = "您已訂閱"
        buttons = [["/unsubscribe 取消訂閱"]]
    else:
        message = "您還未訂閱"
        buttons = [["/subscribe 訂閱"]]
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return None


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(update)
    logger.error(f"{type(context.error).__name__}: {context.error}")


async def summarize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summarize()
    return None


def schedule_jobs(application: Application) -> None:
    for time in Config.SEND_SCHEDULE:
        application.job_queue.run_daily(
            send_news_to_all_subscribers,
            time,
        )
        logger.info(f"News sending scheduled at {time}.")
    for time in Config.SUMMARIZE_SCHEDULE:
        application.job_queue.run_daily(
            summarize_handler,
            time,
        )
        logger.info(f"Summarization scheduled at {time}.")


def main():
    load_dotenv()
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("subscribe", subscribe_handler))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_handler))
    application.add_error_handler(error_handler)

    schedule_jobs(application)

    logger.info("Bot started successfully.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
