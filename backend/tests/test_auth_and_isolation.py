"""Integration coverage for authentication, RBAC, recovery, and isolation.

These tests deliberately exercise the API through separate identities.  The
authenticated identity must always come from the bearer token; a caller must
not be able to substitute another user's resource ID to read, mutate, or
continue that resource.
"""

import io


def _chat(api_client, headers, message="What is the policy?", conversation_id=None):
    payload = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    return api_client.post("/api/chat", json=payload, headers=headers)


def _register(api_client, email, password="Strongpass1!", name="Test User"):
    return api_client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Weak Password",
            "email": "weak-password@example.com",
            "password": "weakpass",
            "confirm_password": "weakpass",
        },
    )

    assert response.status_code == 400


def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Mismatched Password",
            "email": "mismatch@example.com",
            "password": "Strongpass1!",
            "confirm_password": "Different1!",
        },
    )

    assert response.status_code == 400


def test_register_rejects_duplicate_email(client):
    first = _register(client, "duplicate@example.com")
    assert first.status_code == 201, first.text

    duplicate = _register(client, "duplicate@example.com")

    assert duplicate.status_code == 409


def test_protected_routes_reject_missing_and_invalid_tokens(anonymous_client, client):
    missing = anonymous_client.get("/api/conversations")
    assert missing.status_code == 401

    invalid = client.get(
        "/api/conversations",
        headers={"Authorization": "Bearer definitely-not-a-valid-token"},
    )
    assert invalid.status_code == 401


def test_non_admin_is_denied_all_admin_entry_points(client, auth_headers):
    for path in (
        "/api/admin/users",
        "/api/admin/conversations",
        "/api/admin/audit-logs",
        "/api/admin/analytics/overview",
        "/api/admin/restore-requests",
    ):
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 403, path


def test_non_admin_is_denied_every_document_library_operation(client, auth_headers):
    responses = (
        client.get("/api/documents", headers=auth_headers),
        client.post(
            "/api/documents",
            files={"file": ("policy.txt", io.BytesIO(b"private policy"), "text/plain")},
            data={"category": "General"},
            headers=auth_headers,
        ),
        client.get("/api/documents/not-a-document/chunks", headers=auth_headers),
        client.delete("/api/documents/not-a-document", headers=auth_headers),
    )

    assert [response.status_code for response in responses] == [403, 403, 403, 403]


def test_conversation_list_read_delete_and_chat_are_user_scoped(
    client, auth_headers, admin_headers
):
    admin_chat = _chat(client, admin_headers, "admin-only conversation")
    assert admin_chat.status_code == 200, admin_chat.text
    foreign_id = admin_chat.json()["conversation_id"]

    user_chat = _chat(client, auth_headers, "user-owned conversation")
    assert user_chat.status_code == 200, user_chat.text
    own_id = user_chat.json()["conversation_id"]

    listing = client.get("/api/conversations", headers=auth_headers)
    assert listing.status_code == 200
    assert {conversation["id"] for conversation in listing.json()} == {own_id}

    read_foreign = client.get(
        f"/api/conversations/{foreign_id}/messages", headers=auth_headers
    )
    assert read_foreign.status_code == 404

    delete_foreign = client.delete(
        f"/api/conversations/{foreign_id}", headers=auth_headers
    )
    assert delete_foreign.status_code == 404

    continue_foreign = _chat(
        client,
        auth_headers,
        "attempt to continue another user's conversation",
        conversation_id=foreign_id,
    )
    assert continue_foreign.status_code == 404

    own_listing_after_attempt = client.get(
        "/api/conversations", headers=auth_headers
    )
    assert {conversation["id"] for conversation in own_listing_after_attempt.json()} == {
        own_id
    }


def test_unknown_conversation_id_is_not_silently_replaced(client, auth_headers):
    before = client.get("/api/conversations", headers=auth_headers)
    assert before.status_code == 200
    before_ids = {conversation["id"] for conversation in before.json()}

    response = _chat(
        client,
        auth_headers,
        "attempt to use an unknown conversation",
        conversation_id="conversation-that-does-not-exist",
    )

    assert response.status_code == 404
    after = client.get("/api/conversations", headers=auth_headers)
    assert after.status_code == 200
    assert {conversation["id"] for conversation in after.json()} == before_ids


def test_soft_delete_restore_request_and_admin_resolution(
    client, auth_headers, admin_headers
):
    created = _chat(client, auth_headers, "conversation to recover")
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    deleted = client.delete(
        f"/api/conversations/{conversation_id}", headers=auth_headers
    )
    assert deleted.status_code == 204

    active = client.get("/api/conversations", headers=auth_headers)
    assert active.status_code == 200
    assert conversation_id not in {row["id"] for row in active.json()}

    deleted_listing = client.get("/api/conversations/deleted", headers=auth_headers)
    assert deleted_listing.status_code == 200
    assert conversation_id in {row["id"] for row in deleted_listing.json()}

    restore_request = client.post(
        f"/api/conversations/{conversation_id}/restore-requests",
        json={"reason": "Needed for an ongoing policy review"},
        headers=auth_headers,
    )
    assert restore_request.status_code == 201, restore_request.text
    request_id = restore_request.json()["id"]
    assert restore_request.json()["status"] == "PENDING"

    resolved = client.post(
        f"/api/admin/restore-requests/{request_id}/resolve",
        json={"approve": True, "resolution_reason": "Approved for reference"},
        headers=admin_headers,
    )
    assert resolved.status_code == 204, resolved.text

    restored = client.get("/api/conversations", headers=auth_headers)
    assert restored.status_code == 200
    assert conversation_id in {row["id"] for row in restored.json()}

    my_requests = client.get(
        "/api/conversations/restore-requests/mine", headers=auth_headers
    )
    assert my_requests.status_code == 200
    request = next(row for row in my_requests.json() if row["id"] == request_id)
    assert request["status"] == "APPROVED"


def test_duplicate_pending_restore_request_is_rejected(
    client, auth_headers
):
    created = _chat(client, auth_headers, "conversation with one restore request")
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    deleted = client.delete(
        f"/api/conversations/{conversation_id}", headers=auth_headers
    )
    assert deleted.status_code == 204

    payload = {"reason": "Please restore this conversation"}
    first = client.post(
        f"/api/conversations/{conversation_id}/restore-requests",
        json=payload,
        headers=auth_headers,
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        f"/api/conversations/{conversation_id}/restore-requests",
        json=payload,
        headers=auth_headers,
    )
    assert duplicate.status_code == 409


def test_admin_can_see_deleted_conversations_but_user_cannot(
    client, auth_headers, admin_headers
):
    created = _chat(client, auth_headers, "deleted conversation visible to admin")
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]
    assert (
        client.delete(
            f"/api/conversations/{conversation_id}", headers=auth_headers
        ).status_code
        == 204
    )

    admin_listing = client.get("/api/admin/conversations", headers=admin_headers)
    assert admin_listing.status_code == 200
    row = next(row for row in admin_listing.json() if row["id"] == conversation_id)
    assert row["is_deleted"] is True
    assert row["deleted_by"] is not None

    user_active_listing = client.get("/api/conversations", headers=auth_headers)
    assert conversation_id not in {
        row["id"] for row in user_active_listing.json()
    }


def test_user_sources_and_debug_are_redacted_but_admin_trace_is_visible(
    client, auth_headers, admin_headers
):
    marker = "USER_MUST_NOT_RECEIVE_RAW_SOURCE_EXCERPT"
    upload = client.post(
        "/api/documents",
        files={
            "file": (
                "redaction-policy.txt",
                io.BytesIO(
                    f"SECURITY POLICY\n{marker}: internal source-only text.".encode()
                ),
                "text/plain",
            )
        },
        data={"category": "General"},
        headers=admin_headers,
    )
    assert upload.status_code == 201, upload.text

    question = f"What does {marker} mean?"
    user_response = _chat(client, auth_headers, question)
    assert user_response.status_code == 200, user_response.text
    user_body = user_response.json()
    assert user_body.get("debug") is None
    assert user_body["sources"]
    assert all("excerpt" not in source for source in user_body["sources"])
    assert marker not in str(user_body["sources"])

    conversation_id = user_body["conversation_id"]
    admin_history = client.get(
        f"/api/admin/conversations/{conversation_id}/messages",
        headers=admin_headers,
    )
    assert admin_history.status_code == 200
    assistant = next(
        message for message in admin_history.json() if message["role"] == "assistant"
    )
    assert assistant["debug"] is not None
    assert assistant["sources"]
    assert any(marker in source["excerpt"] for source in assistant["sources"])
    assert (
        assistant["debug"]["original_query"]
        == question
    )


def test_feedback_is_denied_for_another_users_message(
    client, auth_headers, admin_headers
):
    user_response = _chat(client, auth_headers, "answer requiring user-owned feedback")
    assert user_response.status_code == 200, user_response.text

    denied = client.post(
        "/api/feedback",
        json={"message_id": user_response.json()["message_id"], "rating": 1},
        headers=admin_headers,
    )

    assert denied.status_code == 404


def test_last_admin_cannot_deactivate_or_remove_own_admin_role(
    client, admin_headers
):
    me = client.get("/api/auth/me", headers=admin_headers)
    assert me.status_code == 200
    admin_id = me.json()["id"]

    deactivate = client.patch(
        f"/api/admin/users/{admin_id}/active",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deactivate.status_code == 400

    demote = client.patch(
        f"/api/admin/users/{admin_id}/role",
        json={"role": "USER"},
        headers=admin_headers,
    )
    assert demote.status_code == 400
