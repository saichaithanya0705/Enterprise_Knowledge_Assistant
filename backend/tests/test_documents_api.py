"""API-level tests for document ingestion and the chat endpoint (local fallback mode)."""
import io


def test_upload_rejects_unsupported_extension(client):
    resp = client.post(
        "/api/documents",
        files={"file": ("notes.exe", io.BytesIO(b"not a real doc"), "application/octet-stream")},
        data={"category": "General"},
    )
    assert resp.status_code == 400


def test_upload_and_ingest_txt_document(client):
    content = b"LEAVE POLICY\nEmployees get 18 days of annual leave per year."
    resp = client.post(
        "/api/documents",
        files={"file": ("leave.txt", io.BytesIO(content), "text/plain")},
        data={"category": "HR"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1

    listing = client.get("/api/documents").json()
    assert any(d["filename"] == "leave.txt" for d in listing)


def test_chat_without_documents_is_not_grounded(client):
    resp = client.post("/api/chat", json={"message": "What is the leave policy?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is False
    assert body["sources"] == []


def test_chat_grounds_answer_in_uploaded_document(client):
    content = b"IT SUPPORT\nTo reset your password, visit the self-service portal."
    client.post(
        "/api/documents",
        files={"file": ("it.txt", io.BytesIO(content), "text/plain")},
        data={"category": "IT"},
    )
    resp = client.post("/api/chat", json={"message": "How do I reset my password?"})
    body = resp.json()
    assert body["grounded"] is True
    assert any(s["filename"] == "it.txt" for s in body["sources"])
    assert body["debug"]["embedding_backend"] == "local_fallback"
