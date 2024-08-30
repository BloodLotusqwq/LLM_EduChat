import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from config import model_name, api_key
from database import get_db
from models import Session, Message
from sqlalchemy.future import select
from loguru import logger

from usel_api import async_call_openai_chat_api

logger = logger.opt(exception=True)
messages_router = APIRouter()


class ChatSchema(BaseModel):
    """
    :param session_id: 会话ID
    :param user_message: 用户的消息
    """
    session_id: int = Field(...)
    user_message: str = Field(...)


@messages_router.post("/chat/")
async def chat_with_openai(chat_schema: ChatSchema, db: AsyncSession = Depends(get_db)):
    """
    使用OpenAI的API处理用户消息，并返回AI的响应。

    :param chat_schema:对话的输入模型
    :param db: 数据库会话依赖项
    :return: 返回AI响应的JSON响应
    """
    try:
        # 从数据库获取该会话的所有消息
        result = await db.execute(select(Message).where(Message.session_id == chat_schema.session_id,
                                                        Message.is_deleted == False))
        messages = result.scalars().all()
        chat_history = [{"role": "system" if msg.character_name == "assistant" else "user", "content": msg.message}
                        for msg in messages]

        chat_history.append({"role": "user", "content": chat_schema.user_message})
        # chat_history.append({"role": "system", "content": "请不要使用markdown格式的输出，而是更适合纯文本的形式"})
        response = await async_call_openai_chat_api(
            model=model_name,
            messages=chat_history,
            api_key=api_key
        )

        ai_message = response['choices'][0]['message']['content']
        user_message_ = Message(session_id=chat_schema.session_id, character_name="user",
                                message=chat_schema.user_message)
        ai_message_ = Message(session_id=chat_schema.session_id, character_name="assistant", message=ai_message)
        db.add(user_message_)
        db.add(ai_message_)
        await db.commit()
        await db.refresh(ai_message_)
        await db.refresh(user_message_)
        return JSONResponse(status_code=200, content={"message": "获取回答成功",
                                                      "ai_message_id": ai_message_.id,
                                                      "user_message_id": user_message_.id,
                                                      "response": ai_message,
                                                      "character_name": "assistant"})
    except HTTPException as HE:
        raise HE
    except (SQLAlchemyError, KeyError) as SE:
        logger.error("数据库操作失败或API响应解析错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库操作或API调用失败") from SE
    except Exception as E:
        logger.error("与OpenAI通信时发生未预期的错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="与OpenAI通信时发生未知错误") from E


@messages_router.get("/messages/{session_id}")
async def get_messages(session_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    获取指定会话中的所有消息。

    :param session_id: 会话ID，类型为 int
    :param db: 数据库会话依赖项，类型为 Session
    :return: 返回包含所有消息的JSON响应，状态码为200
    :raises HTTPException: 当会话ID不存在时抛出，状态码为404
    :raises HTTPException: 当数据库操作失败时抛出，状态码为500
    """
    try:
        # 异步验证会话ID是否存在
        result = await db.execute(select(Session).filter(Session.id == session_id))
        session_exists = result.scalars().first()
        if not session_exists:
            raise HTTPException(status_code=404, detail="会话ID不存在")

        # 异步获取消息
        result = await db.execute(select(Message).where(Message.session_id == session_id,
                                                        Message.is_deleted == False))
        messages = result.scalars().all()
        return JSONResponse(status_code=200, content={
            "message": "获取指定会话中的所有消息成功",
            "messages": [{
                "id": message.id,
                'character_name': message.character_name,
                'message': message.message
            } for message in messages]
        })
    except HTTPException as HE:
        # 直接抛出已经捕获的HTTP异常
        raise HE
    except SQLAlchemyError as SE:
        logger.error("获取会话中信息时数据库查询失败:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库查询消息失败") from SE
    except Exception as E:
        logger.error("获取会话中信息时获取消息未预期的错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="未知错误") from E


@messages_router.delete("/messages/{message_id}")
async def delete_message(message_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    删除指定ID的消息。

    :param message_id: 消息ID，类型为 int
    :param db: 数据库会话依赖项，类型为 Session
    :return: 返回操作结果的JSON响应，状态码为200，包含操作消息
    :raises HTTPException: 当消息ID不存在时抛出，状态码为404
    :raises HTTPException: 当数据库操作失败时抛出，状态码为500
    """
    try:
        result = await db.execute(select(Message).filter(Message.id == message_id))
        message = result.scalars().first()
        if not message:
            raise HTTPException(status_code=404, detail="消息ID不存在")
        if message.is_deleted:
            logger.info("该信息已被标记删除，重复删除")
        # 标记消息为已删除，而不是从数据库中完全删除
        else:
            message.is_deleted = True
            await db.commit()
        return JSONResponse(status_code=200, content={"message": "消息已成功删除"})
    except HTTPException as HE:
        raise HE
    except SQLAlchemyError as SE:
        logger.error("删除消息时，数据库删除操作失败:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库删除消息失败") from SE
    except Exception as E:
        logger.error("删除消息时未预期的错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="未知错误") from E
