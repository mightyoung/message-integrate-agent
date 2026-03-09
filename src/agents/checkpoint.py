"""
Checkpoint Manager - 状态持久化

实现 SQLite 支持的检查点管理器：
- 保存 Agent 循环状态
- 支持从检查点恢复
- 支持时间点回滚

参考:
- LangGraph Checkpointer
- oh-my-openagent 状态管理
"""
import asyncio
import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    session_id: str
    step_index: int
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hash: str = ""


class CheckpointManager:
    """检查点管理器

    使用 SQLite 持久化 Agent 状态：
    - 每个步骤后保存检查点
    - 支持按 session_id 恢复
    - 支持时间点回滚
    """

    def __init__(
        self,
        db_path: str = ".learnings/checkpoints.db",
        max_checkpoints: int = 100,
    ):
        """初始化检查点管理器

        Args:
            db_path: 数据库路径
            max_checkpoints: 最大检查点数量
        """
        self.db_path = Path(db_path)
        self.max_checkpoints = max_checkpoints
        self._lock = asyncio.Lock()

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_db()

        logger.info(f"CheckpointManager initialized (db={db_path}, max={max_checkpoints})")

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 创建检查点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                state TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                hash TEXT
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON checkpoints(session_id, step_index DESC)
        """)

        conn.commit()
        conn.close()

    async def save(
        self,
        context: Any,
        steps: List[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """保存检查点

        Args:
            context: Agent 上下文
            steps: 执行步骤列表
            metadata: 附加元数据

        Returns:
            str: 检查点 ID
        """
        async with self._lock:
            checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(steps)}"

            # 序列化状态
            state = {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "original_message": context.original_message,
                "current_plan": context.current_plan,
                "executed_steps": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                        "output": str(s.output_data) if s.output_data else None,
                        "error": s.error,
                    }
                    for s in steps
                ],
                "intermediate_results": context.intermediate_results,
            }

            # 计算 hash
            import hashlib
            state_str = json.dumps(state, sort_keys=True)
            state_hash = hashlib.sha256(state_str.encode()).hexdigest()[:16]

            # 保存到数据库
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO checkpoints (id, session_id, step_index, state, metadata, created_at, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint_id,
                context.session_id,
                len(steps),
                json.dumps(state),
                json.dumps(metadata or {}),
                datetime.now().isoformat(),
                state_hash,
            ))

            conn.commit()
            conn.close()

            # 清理旧检查点
            await self._cleanup(context.session_id)

            logger.debug(f"Saved checkpoint {checkpoint_id} for session {context.session_id}")
            return checkpoint_id

    async def load(
        self,
        session_id: str,
        step_index: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """加载检查点

        Args:
            session_id: 会话 ID
            step_index: 步骤索引，None 表示最新

        Returns:
            Optional[Dict]: 检查点状态
        """
        async with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            if step_index is not None:
                cursor.execute("""
                    SELECT state FROM checkpoints
                    WHERE session_id = ? AND step_index = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (session_id, step_index))
            else:
                cursor.execute("""
                    SELECT state FROM checkpoints
                    WHERE session_id = ?
                    ORDER BY step_index DESC, created_at DESC
                    LIMIT 1
                """, (session_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                state = json.loads(row[0])
                logger.debug(f"Loaded checkpoint for session {session_id}")
                return state

            return None

    async def list_checkpoints(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """列出检查点

        Args:
            session_id: 会话 ID
            limit: 数量限制

        Returns:
            List[Dict]: 检查点列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, session_id, step_index, created_at, hash
            FROM checkpoints
            WHERE session_id = ?
            ORDER BY step_index DESC, created_at DESC
            LIMIT ?
        """, (session_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "session_id": row[1],
                "step_index": row[2],
                "created_at": row[3],
                "hash": row[4],
            }
            for row in rows
        ]

    async def rollback(
        self,
        session_id: str,
        step_index: int,
    ) -> Optional[Dict[str, Any]]:
        """回滚到指定步骤

        Args:
            session_id: 会话 ID
            step_index: 目标步骤索引

        Returns:
            Optional[Dict]: 回滚后的状态
        """
        return await self.load(session_id, step_index)

    async def delete_session(self, session_id: str):
        """删除会话的所有检查点

        Args:
            session_id: 会话 ID
        """
        async with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()

            logger.info(f"Deleted all checkpoints for session {session_id}")

    async def _cleanup(self, session_id: str):
        """清理旧检查点

        Args:
            session_id: 会话 ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 只保留最近的 max_checkpoints 个
        cursor.execute("""
            DELETE FROM checkpoints
            WHERE session_id = ? AND id NOT IN (
                SELECT id FROM checkpoints
                WHERE session_id = ?
                ORDER BY step_index DESC, created_at DESC
                LIMIT ?
            )
        """, (session_id, session_id, self.max_checkpoints))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM checkpoints")
        sessions = cursor.fetchone()[0]

        conn.close()

        return {
            "total_checkpoints": total,
            "total_sessions": sessions,
            "db_path": str(self.db_path),
        }


# ==================== 便捷函数 ====================

def create_checkpoint_manager(
    db_path: str = ".learnings/checkpoints.db",
    max_checkpoints: int = 100,
) -> CheckpointManager:
    """创建检查点管理器

    Args:
        db_path: 数据库路径
        max_checkpoints: 最大检查点数量

    Returns:
        CheckpointManager: 检查点管理器
    """
    return CheckpointManager(db_path=db_path, max_checkpoints=max_checkpoints)


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 创建管理器
        manager = create_checkpoint_manager("/tmp/test_checkpoints.db")

        # 模拟上下文
        class MockContext:
            session_id = "test_session"
            user_id = "test_user"
            original_message = "Hello"
            current_plan = ["step1", "step2"]
            executed_steps = []
            intermediate_results = {}

        # 模拟步骤
        class MockStep:
            id = "step1"
            name = "THINK"
            status = "completed"
            output_data = "result"
            error = None

        context = MockContext()
        steps = [MockStep()]

        # 保存检查点
        cp_id = await manager.save(context, steps, {"test": True})
        print(f"Saved checkpoint: {cp_id}")

        # 加载检查点
        state = await manager.load("test_session")
        print(f"Loaded state: {state is not None}")

        # 列出检查点
        checkpoints = await manager.list_checkpoints("test_session")
        print(f"Checkpoints: {len(checkpoints)}")

        # 统计
        stats = manager.get_stats()
        print(f"Stats: {stats}")

    asyncio.run(test())
