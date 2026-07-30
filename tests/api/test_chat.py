from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_chat_service
from app.main import app
from app.schemas.chat import ChatHistoryResponse, ChatTurnResponse


class FakeChatService:
    def __init__(self) -> None:
        self.analysis_id = uuid4()
        self.conversation_id = uuid4()
        self.turn_id = uuid4()

    async def send_message(self, analysis_id, content):
        if analysis_id != self.analysis_id:
            return None
        return ChatTurnResponse(
            turn_id=self.turn_id,
            content="저장된 분석 결과를 설명합니다.",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )

    async def history(self, analysis_id):
        if analysis_id != self.analysis_id:
            return None
        return ChatHistoryResponse(
            conversation_id=self.conversation_id,
            messages=[],
        )

    async def clear(self, analysis_id):
        return analysis_id == self.analysis_id


def test_chat_message_stream_and_persistent_history_endpoints() -> None:
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service

    try:
        with TestClient(app) as client:
            sent = client.post(
                f"/api/v1/analyses/{service.analysis_id}/chat/messages",
                json={"content": "이 결과를 설명해줘"},
            )
            history = client.get(
                f"/api/v1/analyses/{service.analysis_id}/chat/messages",
            )
            cleared = client.delete(
                f"/api/v1/analyses/{service.analysis_id}/chat/messages",
            )
    finally:
        app.dependency_overrides.clear()

    assert sent.status_code == 200
    assert sent.headers["content-type"].startswith("text/event-stream")
    assert "event: message_delta" in sent.text
    assert history.status_code == 200
    assert history.json()["conversation_id"] == str(service.conversation_id)
    assert cleared.status_code == 204


def test_chat_approval_endpoint_is_removed() -> None:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/analyses/{uuid4()}/chat/approvals",
            json={
                "turn_id": str(uuid4()),
                "tool_call_id": "update-income",
                "approved": True,
            },
        )

    assert response.status_code == 404
