import base64
import sys
from pathlib import Path

import httpx


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))


def test_vision_text_client_sends_image_as_data_url(monkeypatch, tmp_path):
    from app.services import vision_text
    from app.services.vision_text import VisionTextClient

    image_path = tmp_path / "sample.webp"
    image_path.write_bytes(b"image-bytes")
    captured = {}

    def fake_post(url, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": "extracted korean text",
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(vision_text.httpx, "post", fake_post)

    client = VisionTextClient(
        base_url="http://vlm.example/v1",
        api_key="secret-token",
        model="qwen2.5-vl",
        timeout_seconds=7,
    )

    result = client.extract_text(image_path, prompt="read the text")

    assert result == "extracted korean text"
    assert captured["url"] == "http://vlm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["timeout"] == 7
    assert captured["json"]["model"] == "qwen2.5-vl"
    assert captured["json"]["temperature"] == 0
    content = captured["json"]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "read the text"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == (
        "data:image/webp;base64," + base64.b64encode(b"image-bytes").decode("ascii")
    )


def test_resolve_media_path_stays_under_media_root(tmp_path):
    from app.services.vision_text import resolve_media_path

    media_root = tmp_path / "media"
    image_path = media_root / "Dcinside" / "humor" / "1" / "image.webp"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")

    assert resolve_media_path("Dcinside/humor/1/image.webp", media_root) == image_path.resolve()


def test_resolve_media_path_rejects_path_traversal(tmp_path):
    from app.services.vision_text import VisionTextError, resolve_media_path

    media_root = tmp_path / "media"
    media_root.mkdir()

    try:
        resolve_media_path("../secret.webp", media_root)
    except VisionTextError as exc:
        assert "outside media root" in str(exc)
    else:
        raise AssertionError("path traversal should be rejected")


def test_vision_text_client_uses_central_ai_service(monkeypatch, tmp_path):
    from app.services import vision_text
    from app.services.vision_text import VisionTextClient

    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image-bytes")
    captured = {}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"text": "중앙 OCR"})

    monkeypatch.setattr(vision_text.httpx, "post", fake_post)

    result = VisionTextClient(
        service_url="http://ai-router.local/",
        service_token="service-secret",
        timeout_seconds=9,
    ).extract_text(image_path, prompt="텍스트 추출")

    assert result == "중앙 OCR"
    assert captured["url"] == "http://ai-router.local/api/ai/vision-text"
    assert captured["headers"] == {"X-AI-Service-Token": "service-secret"}
    assert captured["timeout"] == 9.0
    assert captured["json"]["prompt"] == "텍스트 추출"
    assert captured["json"]["image_data_url"].startswith("data:image/png;base64,")
