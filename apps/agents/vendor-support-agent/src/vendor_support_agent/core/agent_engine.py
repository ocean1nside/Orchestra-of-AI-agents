from __future__ import annotations

from vendor_support_agent.schemas.invoke import InvokeRequest, InvokeResponse


class AgentEngine:
    async def invoke(self, req: InvokeRequest) -> InvokeResponse:
        # MVP stub: real implementation will do RAG + LLM call.
        return InvokeResponse(
            answer=f"(stub) Получено сообщение из канала={req.channel}: {req.message}",
            sources=[],
            meta={"confidence": 0.0, "needs_human": True},
        )

