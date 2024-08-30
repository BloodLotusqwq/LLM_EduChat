from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Session(Base):
    """
    代表数据库中的一个会话实体。

    属性:
        id: 会话的唯一标识符，整数类型，自动增长的主键。
        active: 布尔字段，表示会话是否活跃，默认为True。
        name: 字符串字段，会话的名字，可以为空，表示名字是可选的。
        messages: 与Message模型的一对多关系，按消息的ID排序。
    """
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, index=True)
    active = Column(Boolean, default=True)
    name = Column(String, nullable=True)  # 可选字段，允许为空
    messages = relationship("Message", back_populates="session", order_by="Message.id")


class Message(Base):
    """
    代表数据库中的一个消息实体。

    属性:
        id: 消息的唯一标识符，整数类型，自动增长的主键。
        session_id: 外键，指向关联的会话ID。
        character_name: 字符串字段，消息发送者的角色名。
        message: 字符串字段，消息内容。
        timestamp: 日期时间字段，记录消息的发送时间，默认为当前UTC时间。
        is_deleted: 布尔字段，标记消息是否被删除，默认为False。
        session: 与Session模型的多对一关系。
    """
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id'))
    character_name = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    session = relationship("Session", back_populates="messages")
