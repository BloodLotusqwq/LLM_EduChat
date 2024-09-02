from typing import Optional, AsyncGenerator
from fastapi.responses import StreamingResponse
import aiohttp
import requests
from fastapi import HTTPException

from config import api_url, api_key as api_key_, model_name


def call_openai_chat_api(
        model: str,
        messages: list[dict[str, str]],
        api_key: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
) -> dict[str, any]:
    """
    调用 OpenAI API 以使用指定的模型进行聊天。同步代码。

    使用示例:
        .. code-block::

            response = call_openai_chat_api(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "你是谁？"}],
                api_key="your_openai_api_key"
            )

    :param model: 使用的模型名称。
    :param messages: 提供给模型的消息列表，每条消息包含角色和内容。
    :param api_key: 用于认证的 API 密钥。
    :param temperature: 控制输出随机性的参数。默认为 None。
    :param max_tokens: 生成的最大令牌数。默认为 None。
    :param top_p: 控制采样概率的参数。默认为 None。
    :param frequency_penalty: 频率惩罚参数。默认为 None。
    :param presence_penalty: 存在惩罚参数。默认为 None。

    :return: 包含 API 响应的字典。
    :rtype: Dict[str, Any]

    :raises HTTPException: 当 HTTP 请求失败时抛出。
    :raises APIException: 当 API 返回错误时抛出。
    """
    url = api_url
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty
    }
    # 移除 None 值
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # 检查是否有 HTTP 错误
        return response.json()
    except requests.exceptions.HTTPError as HE:
        raise HTTPException(response.status_code, f"{response.text}")from HE
    except requests.exceptions.RequestException as RE:
        raise HTTPException(400, detail=f"API 请求异常: {model}, 错误信息: {RE}") from RE
    except Exception as E:
        raise HTTPException(500, detail=f"未预期的错误: {model}, 错误信息: {E}") from E


async def async_call_openai_chat_api(
        model: str,
        messages: list[dict[str, str]],
        api_key: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
) -> dict[str, any]:
    """
    异步调用 OpenAI API，使用指定模型进行聊天。

    使用示例:
        .. code-block::

            response = await call_openai_chat_api(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "你是谁？"}],
                api_key="your_openai_api_key"
            )

    :param model: 使用的模型名称。
    :param messages: 提供给模型的消息列表，每条消息包含角色和内容。
    :param api_key: 用于认证的 API 密钥。
    :param temperature: 控制输出随机性的参数。默认为 None。
    :param max_tokens: 生成的最大令牌数。默认为 None。
    :param top_p: 控制采样概率的参数。默认为 None。
    :param frequency_penalty: 频率惩罚参数。默认为 None。
    :param presence_penalty: 存在惩罚参数。默认为 None。

    :return: 包含 API 响应的字典。

    :raise HTTPException: 当 HTTP 请求失败时抛出。
    :raise APIException: 当 API 返回错误时抛出。

    注意:
        - 使用异步 `aiohttp.ClientSession` 进行网络请求。
        - 使用 `async with` 确保会话正确关闭。
        - 检查并处理可能的 HTTP 和网络异常。
    """
    url = api_url
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty
    }
    # 移除 None 值
    payload = {k: v for k, v in payload.items() if v is not None}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()  # 检查是否有 HTTP 错误
                return await response.json()
        except aiohttp.ClientResponseError as CRE:
            raise HTTPException(status_code=CRE.status, detail=f"{CRE.message}") from CRE
        except aiohttp.ClientError as CE:
            raise HTTPException(status_code=400, detail=f"API 请求异常: {model}, 错误信息: {CE}") from CE
        except Exception as E:
            raise HTTPException(status_code=500, detail=f"未预期的错误: {model}, 错误信息: {E}") from E


# 测试 call_openai_api 函数
def test_call_openai_api():
    messages = [{"role": "user", "content": "你是谁？"}]

    try:
        response = call_openai_chat_api(
            model=model_name,
            messages=messages,
            api_key=api_key_
        )
        print("API Response:", response)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    test_call_openai_api()
