from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.models import User, Message

def get_user_by_line_id(db: Session, line_id: str) -> Optional[User]:
    """
    根據LINE ID獲取用戶
    
    Args:
        db: 資料庫會話
        line_id: LINE用戶ID
        
    Returns:
        Optional[User]: 用戶對象，如果不存在則返回None
    """
    return db.query(User).filter(User.line_id == line_id).first()

def create_user(db: Session, line_id: str, name: str) -> User:
    """
    創建用戶
    
    Args:
        db: 資料庫會話
        line_id: LINE用戶ID
        name: 用戶名稱
        
    Returns:
        User: 創建的用戶對象
    """
    db_user = User(line_id=line_id, name=name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_message(db: Session, user_id: int, role: str, content: str) -> Message:
    """
    創建消息
    
    Args:
        db: 資料庫會話
        user_id: 用戶ID
        role: 角色 ("user" 或 "bot")
        content: 消息內容
        
    Returns:
        Message: 創建的消息對象
    """
    db_message = Message(user_id=user_id, role=role, content=content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_user_messages(db: Session, user_id: int, limit: int = 100) -> List[Message]:
    """
    獲取用戶消息歷史
    
    Args:
        db: 資料庫會話
        user_id: 用戶ID
        limit: 最大消息數量
        
    Returns:
        List[Message]: 消息列表
    """
    return db.query(Message).filter(Message.user_id == user_id).order_by(Message.created_at.desc()).limit(limit).all()

def delete_user_messages(db: Session, user_id: int) -> int:
    """
    刪除用戶消息歷史
    
    Args:
        db: 資料庫會話
        user_id: 用戶ID
        
    Returns:
        int: 刪除的消息數量
    """
    deleted_count = db.query(Message).filter(Message.user_id == user_id).delete()
    db.commit()
    return deleted_count 