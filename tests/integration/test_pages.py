from fastapi.testclient import TestClient

from tests.fakes import ScriptedProvider
from tests.integration.conftest import ProviderSetter


def create_conversation(client: TestClient, topic: str = "work") -> int:
    response = client.post("/api/conversations", json={"topic": topic})
    assert response.status_code == 201
    return response.json()["conversation_id"]


def send(client: TestClient, conversation_id: int, request_id: str, text: str) -> None:
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": request_id, "text": text},
    )
    assert response.status_code == 200


def test_home_without_conversations_shows_welcome(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Chào bạn!" in response.text
    assert "Chưa có cuộc trò chuyện nào." in response.text


def test_home_redirects_to_latest_conversation(client: TestClient) -> None:
    create_conversation(client, "first")
    latest_id = create_conversation(client, "second")

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/conversations/{latest_id}"


def test_conversation_page_shows_sidebar_and_history(client: TestClient) -> None:
    other_id = create_conversation(client, "Quán cà phê")
    conversation_id = create_conversation(client, "Công việc tester")
    send(client, conversation_id, "req-1", "Yesterday I go to work.")

    response = client.get(f"/conversations/{conversation_id}")

    assert response.status_code == 200
    html = response.text
    assert f'href="/conversations/{other_id}"' in html
    assert 'aria-current="page"' in html
    assert f'data-conversation-id="{conversation_id}"' in html
    assert "Yesterday I go to work." in html
    assert "That sounds nice! What did you do after that?" in html
    assert "I went" in html
    assert "Ngữ pháp" in html


def test_failed_turn_is_marked_in_history(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider(["broken", "broken"]))
    conversation_id = create_conversation(client)
    send(client, conversation_id, "req-1", "Hello")

    html = client.get(f"/conversations/{conversation_id}").text

    assert "Chưa có phản hồi cho câu này." in html


def test_user_and_ai_content_is_escaped(client: TestClient) -> None:
    conversation_id = create_conversation(client, "<b>topic</b>")
    send(client, conversation_id, "req-1", '<script>alert("xss")</script>')

    html = client.get(f"/conversations/{conversation_id}").text

    assert '<script>alert("xss")</script>' not in html
    assert "&lt;script&gt;alert(&#34;xss&#34;)&lt;/script&gt;" in html
    assert "<b>topic</b>" not in html
    assert "&lt;b&gt;topic&lt;/b&gt;" in html


def test_pages_send_security_headers(client: TestClient) -> None:
    response = client.get("/")

    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_api_docs_are_not_blocked_by_page_csp(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "content-security-policy" not in response.headers


def test_unknown_conversation_page_returns_404(client: TestClient) -> None:
    response = client.get("/conversations/999999")

    assert response.status_code == 404
    assert "Không tìm thấy cuộc trò chuyện" in response.text


def test_static_files_are_served(client: TestClient) -> None:
    assert client.get("/static/js/chat.js").status_code == 200
    assert client.get("/static/css/chat.css").status_code == 200


def test_mobile_nav_toggle_controls_the_sidebar(client: TestClient) -> None:
    conversation_id = create_conversation(client)

    html = client.get(f"/conversations/{conversation_id}").text

    assert 'id="sidebar"' in html
    assert 'aria-controls="sidebar"' in html
    assert 'aria-expanded="false"' in html
    assert "Mở danh sách hội thoại" in html


def test_reader_bar_is_rendered_hidden_with_its_controls(client: TestClient) -> None:
    conversation_id = create_conversation(client)

    html = client.get(f"/conversations/{conversation_id}").text

    assert 'id="reader-bar"' in html
    assert 'role="toolbar"' in html
    assert 'id="reader-play"' in html
    assert 'id="reader-stop"' in html
    assert 'id="reader-filter"' in html
    assert "data-conversation-id" in html
