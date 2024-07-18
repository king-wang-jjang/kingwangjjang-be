from fastapi.testclient import TestClient
from app.main import app

import pytest
from httpx import AsyncClient

client = TestClient(app)

# cors_middleware.add(app)
# static_middleware.add(app)

@pytest.mark.anyio
async def test_create_item():
    response = client.post("/test", json  =  {
        "companyId": "6690cf7fa4897bf6b90541c1",
        "userNm": "고객 이름",
        "rank": "직급",
        "companyContact": "123456",
        "mobileContact": "고객사mobile",
        "email": "ewraw@naver.com",
        "responsibleParty": "고객 분류",
        "role": 0
    } )
    assert response.status_code == 200