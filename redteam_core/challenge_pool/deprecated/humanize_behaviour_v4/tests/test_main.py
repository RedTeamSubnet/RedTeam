# -*- coding: utf-8 -*-

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_read_main():
    _response = client.get("/health")
    assert _response.status_code == 200
