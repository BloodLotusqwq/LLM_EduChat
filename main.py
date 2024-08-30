import traceback

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from crud.message_crud import messages_router
from crud.session_crud import sessions_router
from database import init_db

# app是fastapi的应用，include_router是用来添加路由的，tags是用来给这个路由里面的接口打标签分类的，而/api是前缀
app = FastAPI()
app.include_router(sessions_router, tags=["sessions"], prefix="/api")
app.include_router(messages_router, tags=["messages"], prefix="/api")

# 这里进行了很简单的日志处理，但在生产环境当中，要记住添加logger，或者将异常存入数据库当中
# 有不同的风格来记录异常，但我们使用的是在异常发生处进行记录和处理，所以在这里只是为了和前端通信，返回异常信息给前端
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"message": f"内部服务器错误，无法完成数据库操作{exc}",
                 "exception_detail": traceback.format_exc().splitlines()}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": "服务器错误" + exc.detail,
                 "exception_detail": traceback.format_exc().splitlines()}
    )


@app.exception_handler(Exception)
async def http_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"服务器未知错误{exc}",
                 "exception_detail": traceback.format_exc().splitlines()}
    )


# 这里是初始化事件，实际上可以定义多个
# 不过它们是按照顺序去注册的，这意味着如果你注册了多个，会先运行上面的
@app.on_event("startup")
async def startup_event():
    await init_db()


if __name__ == "__main__":
    # 你可以使用这里的代码来手动开启fastapi应用，实际上和使用fastapi dev没有区别
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
