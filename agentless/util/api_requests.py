import base64
import json
import time
from typing import Dict, Union

import openai
import tiktoken
from tqdm import tqdm


def num_tokens_from_messages(message, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if isinstance(message, list):
        # use last message.
        num_tokens = len(encoding.encode(message[0]["content"]))
    else:
        num_tokens = len(encoding.encode(message))
    return num_tokens


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def user_message_step(image_path):
    cur_image = encode_image(image_path)
    message = {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{cur_image}"
                }
            }
        ]
    }
    return message


def create_chatgpt_config(
        message: Union[str, list],
        max_tokens: int,
        temperature: float = 1,
        batch_size: int = 1,
        system_message: str = "You are a helpful assistant.",
        model: str = "/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-72B-Instruct",
        instance_id: str = None,
) -> Dict:
    if isinstance(message, list):
        config = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "n": batch_size,
            "messages": [{"role": "system", "content": [{"type": "text", "text": system_message}]}] + message,
        }
    else:
        if model == "/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-72B-Instruct" or model == "/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-7B-Instruct":
            # 生成图像信息
            with open(f"/gemini/platform/public/users/linhao/origin_data.json", "r") as f:
                data_list = json.load(f)
            img_message = []
            for data in tqdm(data_list):
                if instance_id == data["instance_id"]:
                    index = 0
                    for problem in data["problem_statement"]:
                        if problem.startswith('http'):
                            img_message += user_message_step(f"images/{instance_id}/图片{index}.png")
                            index += 1
                        else:
                            continue
            #
            additional_message = message[-338:]
            while num_tokens_from_messages(system_message + message, model) > 99500:
                message = message[:-1000]
                message += additional_message
                print("aha", num_tokens_from_messages(system_message + message, model))
            config = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "n": batch_size,
                "messages": [
                    {"role": "system", "content": [{"type": "text", "text": system_message}]},
                    {"role": "user", "content": [{"type": "text", "text": message}]},
                ]+img_message,
            }
        elif model == "/gemini/platform/public/llm/huggingface/Qwen/Qwen2.5-Coder-32B-Instruct":
            additional_message = message[-338:]
            while num_tokens_from_messages(system_message + message, model) > 99500:
                message = message[:-1000]
                message += additional_message
                print("aha", num_tokens_from_messages(system_message + message, model))
            config = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "n": batch_size,
                "messages": [
                                {"role": "system", "content": [{"type": "text", "text": system_message}]},
                                {"role": "user", "content": [{"type": "text", "text": message}]},
                            ],
            }
    return config


def handler(signum, frame):
    # swallow signum and frame
    raise Exception("end of time")


def request_chatgpt_engine(config, logger, base_url=None, max_retries=40, timeout=100):
    ret = None
    retries = 0

    client = openai.OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="token-abc123",
    )

    while ret is None and retries < max_retries:
        try:
            # Attempt to get the completion
            logger.info("Creating API request")

            ret = client.chat.completions.create(**config)

        except openai.OpenAIError as e:
            if isinstance(e, openai.BadRequestError):
                logger.info("Request invalid")
                print(e)
                logger.info(e)
                raise Exception("Invalid API Request")
            elif isinstance(e, openai.RateLimitError):
                print("Rate limit exceeded. Waiting...")
                logger.info("Rate limit exceeded. Waiting...")
                print(e)
                logger.info(e)
                time.sleep(5)
            elif isinstance(e, openai.APIConnectionError):
                print("API connection error. Waiting...")
                logger.info("API connection error. Waiting...")
                print(e)
                logger.info(e)
                time.sleep(5)
            else:
                print("Unknown error. Waiting...")
                logger.info("Unknown error. Waiting...")
                print(e)
                logger.info(e)
                time.sleep(1)

        retries += 1

    logger.info(f"API response {ret}")
    return ret


def create_anthropic_config(
        message: str,
        prefill_message: str,
        max_tokens: int,
        temperature: float = 1,
        batch_size: int = 1,
        system_message: str = "You are a helpful assistant.",
        model: str = "claude-2.1",
) -> Dict:
    if isinstance(message, list):
        config = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system": system_message,
            "messages": message,
        }
    else:
        config = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system": system_message,
            "messages": [
                {"role": "user", "content": message},
                {"role": "assistant", "content": prefill_message},
            ],
        }
    return config


def request_anthropic_engine(client, config, logger, max_retries=40, timeout=100):
    ret = None
    retries = 0

    while ret is None and retries < max_retries:
        try:
            start_time = time.time()
            ret = client.messages.create(**config)
        except Exception as e:
            logger.error("Unknown error. Waiting...", exc_info=True)
            # Check if the timeout has been exceeded
            if time.time() - start_time >= timeout:
                logger.warning("Request timed out. Retrying...")
            else:
                logger.warning("Retrying after an unknown error...")
            time.sleep(10)
        retries += 1

    return ret
