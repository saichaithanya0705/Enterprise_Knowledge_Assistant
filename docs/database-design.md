# Database Design

SQLite via SQLAlchemy. Vectors are NOT stored here — see `docs/architecture.md` for why ChromaDB is the vector source of truth.

## documents
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| filename | string | |
| file_type | string | pdf/docx/txt/md |
| category | string | HR/IT/Finance/General |
| status | string | processing / ready / failed |
| char_count | int | |
| chunk_count | int | |
| error_message | text, nullable | set when ingestion fails |
| uploaded_by | string, nullable | FK → users.id; legacy rows remain unowned |
| created_at | datetime | |

## document_chunks
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK — also the ChromaDB vector id |
| document_id | string | FK → documents.id, cascade delete |
| chunk_index | int | order within the document |
| content | text | the chunk text |
| section | string, nullable | heading it was extracted under |
| created_at | datetime | |

## conversations
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| user_id | string, nullable | FK → users.id; ownership boundary |
| title | string | derived from first message |
| created_at | datetime | |
| is_deleted | bool | user deletion is reversible |
| deleted_at | datetime, nullable | |
| deleted_by | string, nullable | FK → users.id |

## messages
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| conversation_id | string | FK → conversations.id, cascade delete |
| role | string | user / assistant |
| content | text | |
| sources | JSON, nullable | list of source refs (assistant messages only) |
| debug_trace | JSON, nullable | full RAG pipeline trace (assistant messages only) |
| created_at | datetime | |

## feedback
| column | type |
|---|---|
| id | string (uuid) PK |
| message_id | string, FK → messages.id |
| rating | int (1 or -1) |
| comment | text, nullable |
| created_at | datetime |

## users
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| name / email | string | email is normalized and unique |
| password_hash | string | bcrypt hash; never serialized |
| role | string | USER / ADMIN |
| is_active | bool | inactive accounts are denied at the auth dependency |
| created_at / last_login_at | datetime | |

## restore_requests / audit_logs

Restore requests connect a deleted conversation, requester, reason, decision, resolver, and timestamps. Audit logs record actor identity, action, target, status, bounded metadata, and creation time for authentication and administrative events.
