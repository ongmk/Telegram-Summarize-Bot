from datetime import time

import pytz


class Config:
    ADMIN_CHAT_ID = "1463445239"
    SUBSCRIBER_FILE = "../data/subscribers.json"
    SUMMARIES_FILE = "../data/summaries.json"
    HEADLINES_FILE = "../data/headlines.json"
    TIMEZONE = pytz.timezone("Asia/Hong_Kong")
    SEND_SCHEDULE = [
        time(7, 0, tzinfo=TIMEZONE),
        time(17, 45, tzinfo=TIMEZONE),
    ]
    SUMMARIZE_SCHEDULE = [
        time(6, 55, tzinfo=TIMEZONE),
        time(17, 40, tzinfo=TIMEZONE),
    ]
