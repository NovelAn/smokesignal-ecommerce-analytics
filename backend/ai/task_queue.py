"""
Async Task Queue - 异步任务队列
支持后台AI分析任务，防止API超时
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import traceback


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败


class InMemoryTaskQueue:
    """
    内存任务队列

    特性:
    - 异步任务处理（不阻塞API响应）
    - 并发控制（最多5个并发任务）
    - 任务状态查询
    """

    def __init__(self, max_concurrent: int = 5):
        """
        初始化任务队列

        Args:
            max_concurrent: 最大并发任务数
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Dict[str, Any]] = {}  # {task_id: task_info}
        self.processing_count = 0
        self._queue = asyncio.Queue()
        self._worker_task = None

    async def enqueue(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List,
        orders: List,
        analyzer_orchestrator
    ) -> str:
        """
        将分析任务加入队列

        Args:
            buyer_nick: 买家昵称
            profile: 客户档案
            chats: 聊天记录
            orders: 订单记录
            analyzer_orchestrator: 分析器编排器实例

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())

        # 创建任务
        task = {
            "task_id": task_id,
            "buyer_nick": buyer_nick,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "input": {
                "profile": profile,
                "chats": chats,
                "orders": orders
            },
            "analyzer": analyzer_orchestrator
        }

        self.tasks[task_id] = task
        await self._queue.put(task_id)

        # 启动worker（如果未启动）
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

        print(f"[Task Queue] 任务已入队: {task_id} ({buyer_nick})")

        return task_id

    async def _worker(self):
        """后台worker - 处理队列中的任务"""
        print(f"[Task Queue] Worker启动，最大并发: {self.max_concurrent}")

        while True:
            try:
                # 等待任务
                task_id = await self._queue.get()

                # 等待并发槽位
                while self.processing_count >= self.max_concurrent:
                    await asyncio.sleep(0.1)

                # 处理任务
                asyncio.create_task(self._process_task(task_id))

            except asyncio.CancelledError:
                print(f"[Task Queue] Worker被取消")
                break
            except Exception as e:
                print(f"[Task Queue] Worker错误: {e}")

    async def _process_task(self, task_id: str):
        """处理单个任务"""
        task = self.tasks.get(task_id)
        if not task:
            return

        self.processing_count += 1
        task["status"] = TaskStatus.PROCESSING.value
        task["started_at"] = datetime.now().isoformat()

        buyer_nick = task["buyer_nick"]
        analyzer = task["analyzer"]

        try:
            print(f"[Task Queue] 开始处理: {task_id} ({buyer_nick})")

            # 调用AI分析器
            result = analyzer.analyze_buyer_persona(
                buyer_nick=buyer_nick,
                profile=task["input"]["profile"],
                chats=task["input"]["chats"],
                orders=task["input"]["orders"]
            )

            # 保存结果
            task["result"] = result
            task["status"] = TaskStatus.COMPLETED.value
            task["completed_at"] = datetime.now().isoformat()

            print(f"[Task Queue] 任务完成: {task_id} ({buyer_nick})")

        except Exception as e:
            error_msg = f"{str(e)[:200]}"
            task["error"] = error_msg
            task["status"] = TaskStatus.FAILED.value
            task["completed_at"] = datetime.now().isoformat()

            print(f"[Task Queue] 任务失败: {task_id} ({buyer_nick}) - {error_msg}")
            print(traceback.format_exc())

        finally:
            self.processing_count -= 1

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态和结果

        Args:
            task_id: 任务ID

        Returns:
            {
                "task_id": str,
                "status": str,  # pending/processing/completed/failed
                "created_at": str,
                "started_at": str,
                "completed_at": str,
                "result": dict or None,
                "error": str or None,
                "buyer_nick": str
            }
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        # 返回任务信息（不包含input和analyzer）
        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "completed_at": task["completed_at"],
            "result": task.get("result"),
            "error": task.get("error"),
            "buyer_nick": task["buyer_nick"]
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取队列统计

        Returns:
            {
                "total_tasks": int,
                "pending": int,
                "processing": int,
                "completed": int,
                "failed": int,
                "processing_count": int,
                "queue_size": int
            }
        """
        status_counts = {
            TaskStatus.PENDING.value: 0,
            TaskStatus.PROCESSING.value: 0,
            TaskStatus.COMPLETED.value: 0,
            TaskStatus.FAILED.value: 0
        }

        for task in self.tasks.values():
            status_counts[task["status"]] += 1

        return {
            "total_tasks": len(self.tasks),
            "pending": status_counts[TaskStatus.PENDING.value],
            "processing": status_counts[TaskStatus.PROCESSING.value],
            "completed": status_counts[TaskStatus.COMPLETED.value],
            "failed": status_counts[TaskStatus.FAILED.value],
            "processing_count": self.processing_count,
            "queue_size": self._queue.qsize()
        }

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理旧任务（避免内存泄漏）

        Args:
            max_age_hours: 任务最大保留时间（小时）

        Returns:
            清理的任务数
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        tasks_to_delete = []

        for task_id, task in self.tasks.items():
            created_at = datetime.fromisoformat(task["created_at"])
            if created_at < cutoff_time:
                # 只删除已完成的任务
                if task["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    tasks_to_delete.append(task_id)

        for task_id in tasks_to_delete:
            del self.tasks[task_id]

        if tasks_to_delete:
            print(f"[Task Queue] 清理了 {len(tasks_to_delete)} 个旧任务")

        return len(tasks_to_delete)


# 全局单例
_task_queue_instance = None


def get_task_queue() -> InMemoryTaskQueue:
    """获取任务队列单例"""
    global _task_queue_instance
    if _task_queue_instance is None:
        _task_queue_instance = InMemoryTaskQueue()
    return _task_queue_instance
