import json
import logging
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv
from logzero import logger
from openai import AzureOpenAI, RateLimitError
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from core.config import Config
from core.schema import Headline
from core.scraper import scrape_headlines
from helpers.llm_gateway_util import (
    KeycloakTokenManager,
    append_cert_to_cacert,
    get_ssl_certificate,
)
from helpers.utils import capture_code, datetime_to_str, save_as_json

load_dotenv()

DEPLOYMENT_NAME = "gpt-4o-deploy-gs"
API_VERSION = "2024-05-13"
SYSTEM_PROMPT = "You are a helpful Trditional Chinese AI assistant that summarizes news headlines and response only in JSON format."
USE_LLM_GATEWAY = True

if USE_LLM_GATEWAY:
    DEPLOYMENT_NAME = "gpt-4o-deploy-gs"
    API_VERSION = "2024-05-13"
    llm_gateway_url = os.getenv("LLM_GATEWAY_URL")
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")

    proxy_url = f"{llm_gateway_url}/models/proxy"
    _ = append_cert_to_cacert(get_ssl_certificate(proxy_url))
    token_mgr = KeycloakTokenManager(
        keycloak_client_id=keycloak_client_id,
        keycloak_client_secret=keycloak_client_secret,
    )
    azure_openai_client = AzureOpenAI(
        api_key="some key",
        azure_endpoint=llm_gateway_url,
        api_version=API_VERSION,
    )

else:
    DEPLOYMENT_NAME = "gpt-4o-deploy"
    API_VERSION = "2024-02-01"
    AzureOpenAI(
        api_key=os.getenv("AZURE_GPT4V_API_KEY"),
        azure_endpoint=(os.getenv("AZURE_GPT4O_ENDPOINT")),
        api_version=API_VERSION,
    )


def get_user_prompt(headlines: list[Headline]):
    headlines_string = [f"{idx}: {h.title}" for idx, h in enumerate(headlines)]
    headlines_string = "\n".join(headlines_string)
    return f"""<新聞標題>
{headlines_string}
</新聞標題>
以上新聞標題由不同來源發布，請找出五個最熱門的話題/關鍵字。
對於每個主題/關鍵字，請提供一個簡短的總結，並提供與之相關的新聞標題的索引。
請按以下JSON格式回答：
[
    "話題/關鍵字": {{
        "總結": "關於話題/關鍵字的簡短總結。",
        "標題索引": [0,2,3,...],
    }},
    "話題/關鍵字": {{
        "總結": "關於話題/關鍵字的簡短總結。",
        "標題索引": [5,10,11,...],
    }},
    …
]
"""


def escape_markdown_v2(text):
    """Escape special characters for MarkdownV2."""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"(?<!\\)([{}])".format(re.escape(escape_chars)), r"\\\1", text)


def enrich_response(response_content: str, headlines: list[Headline]):
    response_content = capture_code(response_content, "json")
    response_json = json.loads(response_content)
    rich_responses = []
    for topic, details in response_json.items():
        summary_chunks = []
        summary_chunks.append(
            f"*{escape_markdown_v2(details['總結'])}*\n{escape_markdown_v2('-'*50)}\n"
        )
        topic_headlines = sorted([int(idx) for idx in details["標題索引"]])[:5]
        for i, headline_idx in enumerate(topic_headlines):
            selected = headlines[headline_idx]
            escaped_title = escape_markdown_v2(selected.title)
            escaped_publisher = escape_markdown_v2(selected.publisher)
            escaped_summary = escape_markdown_v2(selected.summary).replace("\n", "\n> ")
            summary_chunks.append(
                f"{i + 1}\. [*{escaped_title}*]({selected.link}) \- _{escaped_publisher}_\n"
                f">{escaped_summary}||\n\n"
            )
        rich_responses.append(summary_chunks)
    return rich_responses


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(RateLimitError),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
def completion_with_retry(**kwargs):
    return azure_openai_client.chat.completions.create(**kwargs)


def summarize():
    headlines = scrape_headlines()

    start_time = time.time()
    completion = completion_with_retry(
        messages=[
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [{"type": "text", "text": get_user_prompt(headlines)}],
            },
        ],
        model=DEPLOYMENT_NAME,
        extra_headers=(
            {"Authorization": f"Bearer {token_mgr.kc_get_access_token()}"}
            if USE_LLM_GATEWAY
            else {}
        ),
        temperature=0,
        seed=2024,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    response = completion.choices[0].message.content
    model = completion.model
    total_duration_sec = time.time() - start_time

    logger.info(f"Model: {model}")
    logger.info(f"Total duration: {total_duration_sec:.2f} seconds")

    rich_responses = enrich_response(response, headlines)

    save_as_json(
        {
            "last_updated": datetime_to_str(datetime.now()),
            "model": model,
            "usage": completion.usage.to_dict(),
            "duration": total_duration_sec,
            "summaries": rich_responses,
        },
        Config.SUMMARIES_FILE,
    )
    logger.info(f"Summaries saved to {Config.SUMMARIES_FILE}")

    return rich_responses


if __name__ == "__main__":
    summarize()
