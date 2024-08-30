from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Session
from sqlalchemy.future import select
from loguru import logger

logger = logger.opt(exception=True)
sessions_router = APIRouter()


@sessions_router.post("/sessions/")
async def create_session(name: Optional[str] = None, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    创建一个新的会话，并返回会话ID。

    :param name: 可选的会话名称。
    :param db: 数据库会话依赖项，类型为 Session
    :return: 返回包含新会话ID和名称的JSON响应，状态码为201
    :raises HTTPException: 当数据库操作失败时抛出，状态码为500
    """
    try:
        new_session = Session(active=True, name=name)
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return JSONResponse(status_code=201, content={"message": "创建会话成功",
                                                      "session_id": new_session.id,
                                                      "session_name": new_session.name})
    except IntegrityError as IE:
        logger.error("创建会话失败，违反数据库完整性约束:", exc_info=True)
        raise HTTPException(status_code=400, detail="提供的数据违反了完整性约束") from IE
    except SQLAlchemyError as SE:
        logger.error("创建会话失败，执行数据库操作失败:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库查询执行失败") from SE
    except Exception as E:
        logger.error("创建会话失败，未知错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="未知错误") from E


@sessions_router.get("/sessions/")
async def list_sessions(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    获取所有会话的列表。

    :type db: object
    :param db: 数据库会话依赖项，类型为 Session
    :return: 返回包含所有会话ID的JSON响应，状态码为200
    :raises HTTPException: 当数据库查询执行失败时抛出，状态码为500
    :raises HTTPException: 当数据库连接失败时抛出，状态码为503
    """
    try:
        result = await db.execute(select(Session).where(Session.active == True))
        sessions = result.scalars().all()
        return JSONResponse(status_code=200,
                            content={"message": "获取所有会话id成功",
                                     "sessions": [{
                                         "session_id": session.id,
                                         "session_name": session.name
                                     }
                                         for session in sessions]})
    except OperationalError as OE:
        logger.error("从数据库获取会话失败，数据库操作失败:", exc_info=True)
        raise HTTPException(status_code=503, detail="数据库服务不可用") from OE
    except SQLAlchemyError as SE:
        logger.error("获取会话，执行数据库查询失败:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库查询执行失败") from SE
    except Exception as E:
        logger.error("获取会话列表未预期的错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="未知错误") from E


@sessions_router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    根据ID删除指定的会话。

    :param session_id: 会话ID，类型为 int
    :param db: 数据库会话依赖项，类型为 Session
    :return: 返回操作结果的JSON响应，状态码为200
    :raises HTTPException: 当会话ID不存在时抛出，状态码为404
    :raises HTTPException: 当数据库操作失败时抛出，状态码为500
    """
    try:
        result = await db.execute(select(Session).filter(Session.id == session_id))
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="会话ID不存在")

        session.active = False  # 标记为不活跃而不是删除
        await db.commit()
        return JSONResponse(status_code=200, content={"message": "会话已成功删除"})
    except HTTPException as HE:
        raise HE
    except SQLAlchemyError as SE:
        logger.error("删除指定会话，执行数据库查询失败:", exc_info=True)
        raise HTTPException(status_code=500, detail="数据库查询执行失败") from SE
    except Exception as E:
        logger.error("删除会话失败，未知错误:", exc_info=True)
        raise HTTPException(status_code=500, detail="删除会话失败") from E
