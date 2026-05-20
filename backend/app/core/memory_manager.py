"""
记忆管理器 — 基于文本嵌入向量的语义搜索实现长期记忆。

架构：
- retrieve()：对查询文本做嵌入，与 Agent 的所有记忆计算余弦相似度，返回 top_k 条最相关的
- store()：对新事实做嵌入，检查是否已存在高度相似记录（余弦 > 0.95），
  若存在则覆盖更新，否则插入新记录
- extract_and_store()：让 LLM 从最近 6 条消息中提取 1-3 个用户关键信息，
  然后逐条调用 store() 存储

当前为暴力搜索方案（无向量数据库）— 小规模部署可接受。
大规模部署时建议替换为 pgvector 或外部向量存储。
"""

import json
import math
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.core.llm_gateway import llm_gateway
from app.config import settings


class MemoryManager:
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算两个向量的余弦相似度。空向量或零向量返回 0.0。"""
        if not a or not b or sum(a) == 0 or sum(b) == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def retrieve(self, db: AsyncSession, agent_id: UUID, query: str) -> list[str]:
        """返回与查询最相关的 top_k 条记忆内容。
        嵌入生成失败时返回空列表。"""
        try:
            embedding = await llm_gateway.get_embedding(query)
        except Exception:
            return []

        result = await db.execute(select(Memory).where(Memory.agent_id == agent_id))
        memories = result.scalars().all()

        scored = []
        for m in memories:
            try:
                emb = json.loads(m.embedding_json)
                score = self._cosine_similarity(embedding, emb)
                scored.append((score, m.content))
            except Exception:
                pass

        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:settings.memory_top_k]]

    async def store(self, db: AsyncSession, agent_id: UUID, content: str, conversation_id: UUID | None = None, api_base: str | None = None, api_key: str | None = None):
        """存储一条记忆。如果已存在高度相似记录（余弦 > 0.95），
        覆盖更新而非新增 — 这样能保持记忆库干净，避免冗余。"""
        try:
            embedding = await llm_gateway.get_embedding(content, api_base=api_base, api_key=api_key)
        except Exception:
            return

        result = await db.execute(select(Memory).where(Memory.agent_id == agent_id))
        memories = result.scalars().all()

        # 找到最相似的已有记忆，用于去重
        best_score = 0.0
        best_memory = None
        for m in memories:
            try:
                emb = json.loads(m.embedding_json)
                score = self._cosine_similarity(embedding, emb)
                if score > best_score:
                    best_score = score
                    best_memory = m
            except Exception:
                pass

        if best_memory and best_score > 0.95:
            best_memory.content = content
            best_memory.conversation_id = conversation_id
            best_memory.embedding_json = json.dumps(embedding)
        else:
            memory = Memory(agent_id=agent_id, conversation_id=conversation_id, content=content, embedding_json=json.dumps(embedding))
            db.add(memory)
        await db.commit()

    async def extract_and_store(self, db: AsyncSession, agent_id: UUID, messages: list[dict], conversation_id: UUID | None = None, model: str = "gpt-4o-mini", api_base: str | None = None, api_key: str | None = None):
        """让 LLM 从最近消息中提取用户关键信息，然后逐条存储。
        每次对话轮次结束后调用。只处理最近 6 条消息以保持提取 prompt 聚焦。"""
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-6:])
        prompt = (
            "Extract 1-3 key facts about the user from this conversation. "
            "Focus on preferences, identity, and recurring topics. "
            "Output one fact per line, no numbering or prefixes.\n\n"
            f"{text}"
        )
        try:
            response = await llm_gateway.chat_completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                api_base=api_base, api_key=api_key,
            )
            facts = response.content.strip().split("\n") if hasattr(response, 'content') else []
            for fact in facts:
                fact = fact.strip()
                if fact and len(fact) > 5:
                    await self.store(db, agent_id, fact, conversation_id, api_base=api_base, api_key=api_key)
        except Exception:
            pass


memory_manager = MemoryManager()