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
| column | type |
|---|---|
| id | string (uuid) PK |
| title | string (derived from first message) |
| created_at | datetime |

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
