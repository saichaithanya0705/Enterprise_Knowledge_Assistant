"""Regression tests for public API contracts and conversation lifecycle."""

import asyncio
import sqlite3

import io

import pytest


def _create_legacy_feedback_schema(database_path, *, duplicate_feedback=False):
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE conversations (
                id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                created_at DATETIME
            );
            CREATE TABLE messages (
                id VARCHAR(36) PRIMARY KEY,
                conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                sources JSON,
                debug_trace JSON,
                created_at DATETIME
            );
            CREATE TABLE feedback (
                id VARCHAR(36) PRIMARY KEY,
                message_id VARCHAR(36) NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at DATETIME
            );
            INSERT INTO conversations (id, title) VALUES ('conversation-1', 'Legacy');
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES ('message-1', 'conversation-1', 'assistant', 'Existing answer');
            INSERT INTO feedback (id, message_id, rating)
            VALUES ('feedback-1', 'message-1', 1);
            """
        )
        if duplicate_feedback:
            connection.execute(
                "INSERT INTO feedback (id, message_id, rating) VALUES (?, ?, ?)",
                ("feedback-2", "message-1", -1),
            )
        connection.commit()
    finally:
        connection.close()


def _init_against_existing_sqlite(monkeypatch, database_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    from app.core.config import get_settings
    import app.db.database as database_module

    get_settings.cache_clear()
    database_module.reset_for_tests()
    database_module.init_db()
    return database_module, get_settings


def _chat(client, message="What is the policy?", conversation_id=None):
    payload = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    return client.post("/api/chat", json=payload)


def test_render_root_health_check_supports_head(anonymous_client):
    response = anonymous_client.head("/")

    assert response.status_code == 200


def test_history_preserves_persisted_debug_trace(client):
    response = _chat(client)
    assert response.status_code == 200
    body = response.json()

    history = client.get(f"/api/conversations/{body['conversation_id']}/messages")
    assert history.status_code == 200
    assistant = next(message for message in history.json() if message["role"] == "assistant")
    assert assistant["debug"] == body["debug"]
    assert assistant["debug"]["retrieved_chunks"] == []


def test_malformed_persisted_debug_is_ignored_without_leaking_content(client, caplog):
    from app.db.database import SessionLocal
    from app.models.conversation import Message

    response = _chat(client)
    assert response.status_code == 200

    secret = "provider-secret-in-persisted-json"
    db = SessionLocal()
    try:
        message = db.query(Message).filter(Message.id == response.json()["message_id"]).one()
        message.debug_trace = secret
        db.commit()
    finally:
        db.close()

    with caplog.at_level("WARNING"):
        history = client.get(f"/api/conversations/{response.json()['conversation_id']}/messages")

    assert history.status_code == 200
    assistant = next(message for message in history.json() if message["role"] == "assistant")
    assert assistant["debug"] is None
    assert secret not in caplog.text
    assert response.json()["message_id"] in caplog.text
    assert "str" in caplog.text


def test_feedback_validates_rating_comment_and_message_role(client):
    response = _chat(client)
    assert response.status_code == 200
    body = response.json()
    history = client.get(f"/api/conversations/{body['conversation_id']}/messages").json()
    user_message = next(message for message in history if message["role"] == "user")

    assert client.post(
        "/api/feedback", json={"message_id": body["message_id"], "rating": 1, "comment": "Helpful"}
    ).status_code == 201
    assert client.post(
        "/api/feedback", json={"message_id": body["message_id"], "rating": 0}
    ).status_code == 422
    assert client.post(
        "/api/feedback", json={"message_id": body["message_id"], "rating": 1, "comment": "x" * 2001}
    ).status_code == 422
    assert client.post(
        "/api/feedback", json={"message_id": "missing-message", "rating": -1}
    ).status_code == 404
    assert client.post(
        "/api/feedback", json={"message_id": user_message["id"], "rating": -1}
    ).status_code == 400


def test_feedback_duplicate_is_rejected_without_creating_a_second_row(client):
    from sqlalchemy import inspect

    from app.db.database import SessionLocal
    from app.models.conversation import Feedback

    response = _chat(client)
    message_id = response.json()["message_id"]
    assert client.post("/api/feedback", json={"message_id": message_id, "rating": 1}).status_code == 201
    duplicate = client.post("/api/feedback", json={"message_id": message_id, "rating": -1})
    assert duplicate.status_code == 409

    db = SessionLocal()
    try:
        assert db.query(Feedback).filter(Feedback.message_id == message_id).count() == 1
        unique_constraints = inspect(db.bind).get_unique_constraints("feedback")
        assert any(tuple(item["column_names"]) == ("message_id",) for item in unique_constraints)
    finally:
        db.close()


def test_init_db_migrates_existing_sqlite_feedback_table_to_unique_message_ids(
    monkeypatch, tmp_path
):
    from sqlalchemy import inspect
    from sqlalchemy.exc import IntegrityError

    from app.db.database import SessionLocal
    from app.models.conversation import Feedback

    database_path = tmp_path / "legacy.db"
    _create_legacy_feedback_schema(database_path)

    database_module, get_settings = _init_against_existing_sqlite(monkeypatch, database_path)
    try:
        database_module.init_db()
        db = SessionLocal()
        try:
            inspector = inspect(db.bind)
            matching_indexes = [
                index
                for index in inspector.get_indexes("feedback")
                if index["name"] == "uq_feedback_message_id"
            ]
            matching_constraints = [
                constraint
                for constraint in inspector.get_unique_constraints("feedback")
                if constraint["name"] == "uq_feedback_message_id"
            ]
            assert matching_indexes or matching_constraints

            db.add(Feedback(message_id="message-1", rating=-1))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        finally:
            db.close()
    finally:
        database_module.reset_for_tests()
        get_settings.cache_clear()


def test_init_db_feedback_unique_migration_is_idempotent_across_repeated_startup(
    monkeypatch, tmp_path
):
    from sqlalchemy import inspect

    database_path = tmp_path / "repeated-startup.db"
    _create_legacy_feedback_schema(database_path)

    database_module, get_settings = _init_against_existing_sqlite(monkeypatch, database_path)
    try:
        database_module.init_db()
        database_module.init_db()
        db = database_module.SessionLocal()
        try:
            indexes = inspect(db.bind).get_indexes("feedback")
            matching = [
                index
                for index in indexes
                if index["name"] == "uq_feedback_message_id"
            ]
            assert matching
            assert bool(matching[0]["unique"]) is True
        finally:
            db.close()
    finally:
        database_module.reset_for_tests()
        get_settings.cache_clear()


def test_init_db_rejects_existing_duplicate_feedback_without_deleting_rows(monkeypatch, tmp_path):
    database_path = tmp_path / "duplicate-legacy.db"
    _create_legacy_feedback_schema(database_path, duplicate_feedback=True)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    from app.core.config import get_settings
    import app.db.database as database_module

    get_settings.cache_clear()
    database_module.reset_for_tests()
    try:
        with pytest.raises(RuntimeError, match="duplicate feedback message_id.*[Rr]esolve"):
            database_module.init_db()
    finally:
        database_module.reset_for_tests()
        get_settings.cache_clear()

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM feedback WHERE message_id = 'message-1'"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'index' AND name = 'uq_feedback_message_id'"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_feedback_concurrent_delete_is_mapped_to_not_found(client, monkeypatch):
    from app.api.routes import feedback as feedback_route
    from app.repositories.conversation_repo import MessageNotFoundError

    response = _chat(client)

    def raise_deleted(*args, **kwargs):
        raise MessageNotFoundError(response.json()["message_id"])

    monkeypatch.setattr(feedback_route.conversation_repo, "add_feedback", raise_deleted)
    result = client.post(
        "/api/feedback", json={"message_id": response.json()["message_id"], "rating": 1}
    )
    assert result.status_code == 404
    assert result.json()["detail"] == "Message not found"


def test_feedback_database_error_is_rolled_back_and_sanitized(client, monkeypatch):
    from app.api.routes import feedback as feedback_route
    from app.repositories.conversation_repo import FeedbackPersistenceError

    response = _chat(client)

    def raise_database_error(*args, **kwargs):
        raise FeedbackPersistenceError("database password leaked")

    monkeypatch.setattr(feedback_route.conversation_repo, "add_feedback", raise_database_error)
    result = client.post(
        "/api/feedback", json={"message_id": response.json()["message_id"], "rating": 1}
    )
    assert result.status_code == 500
    assert result.json()["detail"] == "Unable to record feedback."
    assert "database password leaked" not in result.text


def test_feedback_commit_failure_rolls_back_insert(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    from app.db.database import SessionLocal
    from app.models.conversation import Feedback
    from app.repositories import conversation_repo
    from app.repositories.conversation_repo import FeedbackPersistenceError

    response = _chat(client)
    message_id = response.json()["message_id"]
    db = SessionLocal()

    def fail_commit():
        raise OperationalError("INSERT", {}, RuntimeError("secret database detail"))

    monkeypatch.setattr(db, "commit", fail_commit)
    try:
        with pytest.raises(FeedbackPersistenceError):
            conversation_repo.add_feedback(db, message_id, 1, None)
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(Feedback).filter(Feedback.message_id == message_id).count() == 0
    finally:
        verification_db.close()


def test_upload_category_is_a_closed_set(client):
    response = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"policy"), "text/plain")},
        data={"category": "Payroll"},
    )
    assert response.status_code == 422


def test_soft_delete_preserves_history_and_admin_hard_delete_cascades_feedback(client):
    from sqlalchemy import text

    from app.db.database import SessionLocal
    from app.models.conversation import Feedback, Message

    response = _chat(client)
    assert response.status_code == 200
    body = response.json()
    feedback = client.post(
        "/api/feedback", json={"message_id": body["message_id"], "rating": 1}
    )
    assert feedback.status_code == 201

    db = SessionLocal()
    try:
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert db.query(Message).count() == 2
        assert db.query(Feedback).count() == 1
    finally:
        db.close()

    assert client.delete(f"/api/conversations/{body['conversation_id']}").status_code == 204

    db = SessionLocal()
    try:
        assert db.query(Message).count() == 2
        assert db.query(Feedback).count() == 1
    finally:
        db.close()

    assert client.delete(
        f"/api/admin/conversations/{body['conversation_id']}/permanent"
    ).status_code == 204

    db = SessionLocal()
    try:
        assert db.query(Message).count() == 0
        assert db.query(Feedback).count() == 0
    finally:
        db.close()


def test_unknown_conversation_id_is_not_silently_created(client):
    response = _chat(client, conversation_id="does-not-exist")
    assert response.status_code == 404
    assert client.get("/api/conversations").json() == []


def test_new_chat_without_conversation_id_still_creates_conversation(client):
    response = _chat(client)
    assert response.status_code == 200
    assert response.json()["conversation_id"]


def test_chat_5xx_does_not_expose_internal_exception_text(client, monkeypatch):
    from app.api.routes import chat as chat_route

    async def explode(*args, **kwargs):
        raise RuntimeError("secret provider credentials")

    monkeypatch.setattr(chat_route, "answer_question", explode)
    response = _chat(client)
    assert response.status_code == 500
    assert "secret provider credentials" not in response.text
    assert response.json()["detail"] == "Failed to generate a response."


def test_failed_generation_does_not_persist_new_conversation_or_user_turn(client, monkeypatch):
    from app.services import chat_service
    from app.db.database import SessionLocal
    from app.models.conversation import Conversation, Message

    async def fail(*args, **kwargs):
        raise RuntimeError("secret provider credentials")

    monkeypatch.setattr(chat_service, "generate_answer", fail)
    response = _chat(client)
    assert response.status_code == 500

    db = SessionLocal()
    try:
        assert db.query(Conversation).count() == 0
        assert db.query(Message).count() == 0
    finally:
        db.close()


def test_failed_generation_does_not_leave_user_only_turn(client, monkeypatch):
    from app.services import chat_service
    from app.db.database import SessionLocal
    from app.models.conversation import Message

    first = _chat(client)
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    async def fail(*args, **kwargs):
        raise RuntimeError("secret provider credentials")

    monkeypatch.setattr(chat_service, "generate_answer", fail)
    failed = _chat(client, conversation_id=conversation_id)
    assert failed.status_code == 500

    db = SessionLocal()
    try:
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).all()
        assert [message.role for message in messages] == ["user", "assistant"]
    finally:
        db.close()


def test_concurrent_turns_are_serialized_and_second_history_includes_first_answer(client, monkeypatch):
    from app.db.database import SessionLocal
    from app.models.conversation import Message
    from app.services import chat_service

    first = _chat(client)
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]
    seen_histories = []
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def generate(context, question, history, prepared_messages):
        seen_histories.append((question, [item["content"] for item in history]))
        if question == "first concurrent question":
            first_started.set()
            await release_first.wait()
        return f"answer to {question}", "test_backend"

    monkeypatch.setattr(chat_service, "generate_answer", generate)

    async def run_turns():
        db_one = SessionLocal()
        db_two = SessionLocal()
        try:
            first_task = asyncio.create_task(
                chat_service.answer_question(db_one, conversation_id, "first concurrent question")
            )
            await first_started.wait()
            second_task = asyncio.create_task(
                chat_service.answer_question(db_two, conversation_id, "second concurrent question")
            )
            await asyncio.sleep(0)
            assert len(seen_histories) == 1
            release_first.set()
            return await asyncio.gather(first_task, second_task)
        finally:
            db_one.close()
            db_two.close()

    asyncio.run(run_turns())

    assert seen_histories[1][0] == "second concurrent question"
    assert "answer to first concurrent question" in seen_histories[1][1]
    assert not chat_service._TURN_LOCKS._entries

    db = SessionLocal()
    try:
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
        assert [message.content for message in messages[-4:]] == [
            "first concurrent question",
            "answer to first concurrent question",
            "second concurrent question",
            "answer to second concurrent question",
        ]
    finally:
        db.close()


def test_cancelled_waiting_turn_does_not_release_active_lock():
    from app.services.chat_service import _ConversationTurnLocks

    async def exercise():
        registry = _ConversationTurnLocks()
        holder_ready = asyncio.Event()
        release_holder = asyncio.Event()

        async def holder():
            async with registry.hold("conversation"):
                holder_ready.set()
                await release_holder.wait()

        async def waiter():
            async with registry.hold("conversation"):
                return "acquired"

        holder_task = asyncio.create_task(holder())
        await holder_ready.wait()
        waiter_task = asyncio.create_task(waiter())
        await asyncio.sleep(0)
        waiter_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter_task
        assert registry._entries["conversation"].lock.locked()
        release_holder.set()
        await holder_task
        assert not registry._entries

    asyncio.run(exercise())


def test_document_ingestion_error_is_generic_and_not_logged_with_exception_text(client, monkeypatch, caplog):
    from app.api.routes import documents as documents_route

    async def fail(*args, **kwargs):
        raise RuntimeError("secret filesystem path and upstream token")

    monkeypatch.setattr(documents_route, "ingest_document", fail)
    with caplog.at_level("WARNING"):
        response = client.post(
            "/api/documents",
            files={"file": ("policy.txt", io.BytesIO(b"policy"), "text/plain")},
            data={"category": "General"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Could not process document."
    assert "secret filesystem path" not in response.text
    assert "secret filesystem path" not in caplog.text


def test_document_list_does_not_expose_ingestion_exception_sentinel(client, monkeypatch, caplog):
    from app.services import document_service

    sentinel = "secret provider token and filesystem path"

    async def fail_embedding(*args, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(document_service, "embed_texts", fail_embedding)
    with caplog.at_level("WARNING"):
        response = client.post(
            "/api/documents",
            files={"file": ("policy.txt", io.BytesIO(b"policy"), "text/plain")},
            data={"category": "General"},
        )

    assert response.status_code == 422
    listed = client.get("/api/documents")
    assert listed.status_code == 200
    failed = listed.json()[0]
    assert failed["error_message"] == "Document processing failed. Please try again or contact support."
    assert sentinel not in listed.text
    assert sentinel not in caplog.text


def test_document_list_sanitizes_legacy_persisted_error_message(client):
    from app.db.database import SessionLocal
    from app.models.document import Document

    sentinel = "legacy upstream response with secret token"
    db = SessionLocal()
    try:
        db.add(
            Document(
                filename="legacy.txt",
                file_type="txt",
                category="General",
                status="failed",
                error_message=sentinel,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert sentinel not in response.text
    assert response.json()[0]["error_message"] == "Document processing failed. Please try again or contact support."


@pytest.mark.parametrize("rating", [-2, 0, 2, "positive"])
def test_feedback_rejects_non_binary_ratings(client, rating):
    response = _chat(client)
    assert response.status_code == 200
    assert client.post(
        "/api/feedback", json={"message_id": response.json()["message_id"], "rating": rating}
    ).status_code == 422
