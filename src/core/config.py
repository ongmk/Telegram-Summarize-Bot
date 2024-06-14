from datetime import time, timedelta


class Config:
    ADMIN_CHAT_ID = "1463445239"
    SUBSCRIBER_FILE = "../data/subscribers.json"
    SUMMARIES_FILE = "../data/summaries.json"
    HEADLINES_FILE = "../data/headlines.json"
    SEND_SCHEDULE = [time(7, 0), time(17, 45)]
    SUMMARIZE_SCHEDULE = [time(6, 45), time(17, 30)]
