"""
存储后端实现
使用 SQLite 数据库存储对话历史
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json


class StorageBackend:
    """存储后端基类"""
    
    async def load_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """加载历史对话"""
        raise NotImplementedError
    
    async def save_message(self, user_id: str, message: Dict):
        """保存单条消息"""
        raise NotImplementedError
    
    async def clear_history(self, user_id: str):
        """清空历史"""
        raise NotImplementedError


class SQLiteStorage(StorageBackend):
    """SQLite 数据库存储"""
    
    def __init__(self, db_path: str = "./data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引以加快查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id_timestamp 
            ON messages(user_id, created_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    async def load_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """加载最近的对话历史（按插入顺序）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取最近 limit 条消息，按 ID 升序（插入顺序）
            cursor.execute("""
                SELECT role, content, metadata, timestamp 
                FROM messages 
                WHERE user_id = ? 
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            
            # 按 ID 升序返回（从早到晚）
            history = []
            for row in reversed(rows):
                msg = {
                    "role": row["role"],
                    "content": row["content"],
                }
                if row["metadata"]:
                    try:
                        msg["metadata"] = json.loads(row["metadata"])
                    except json.JSONDecodeError:
                        pass
                history.append(msg)
            
            return history
        
        finally:
            conn.close()
    
    async def save_message(self, user_id: str, message: Dict):
        """保存单条消息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            metadata = message.get("metadata")
            
            # 将 metadata 序列化为 JSON
            metadata_json = None
            if metadata:
                metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO messages (user_id, role, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                role,
                content,
                metadata_json,
                datetime.now().isoformat()
            ))
            
            conn.commit()
        
        finally:
            conn.close()
    
    async def clear_history(self, user_id: str):
        """清空用户历史"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.commit()
        
        finally:
            conn.close()


def create_storage(**kwargs) -> StorageBackend:
    """创建 SQLite 存储后端"""
    return SQLiteStorage(**kwargs)
