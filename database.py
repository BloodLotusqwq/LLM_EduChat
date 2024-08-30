from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base

# 这里使用的是sqlite的异步链接，所以需要加上aiosqlite
# 由于sqlite数据库实际上就是一个文件，因此不需要修改，修改了./chat.db这部分也只是修改了连接的路径
# 如果你写成:memory:就会在内存当中跑，但是不会保留结果

DATABASE_URL = "sqlite+aiosqlite:///./chat.db"

# 创建异步的SQLAlchemy引擎，设置echo为True以输出日志信息，有助于调试
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建异步会话工厂，配置为不自动提交和不自动刷新，绑定到创建的异步引擎
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)


async def init_db():
    """
    初始化数据库，创建所有在Base.metadata中定义的表。
    """
    async with engine.begin() as conn:  # 使用上下文管理器确保连接正确关闭
        await conn.run_sync(Base.metadata.create_all)  # 创建表


async def get_db() -> AsyncSession:
    """
    生成器函数，提供数据库会话并确保会话在使用后关闭。

    :return: 返回一个异步会话对象
    :rtype: AsyncSession
    """
    async with AsyncSessionLocal() as session:  # 使用上下文管理器自动管理会话生命周期
        yield session  # 提供会话给调用者使用
