from fastapi.testclient import TestClient
from app.main import app

import pytest
from httpx import AsyncClient

client = TestClient(app)

# cors_middleware.add(app)
# static_middleware.add(app)

def db_connection():
    response = client.get("/")
    print(response.text)
    assert response.status_code == 200


def board_summary():
    response = client.post("/board_summary",json=
    {
        "board_id" : "2078193",
        "site" : "ygosu"
    })
    assert response.status_code == 200
    assert response.text == "이토 히로부미는 조선의 독립을 원했지만 안중근의 암살 행위로 인해 일본 강경파들이 격노하여 조선이 식민지화되었다."

