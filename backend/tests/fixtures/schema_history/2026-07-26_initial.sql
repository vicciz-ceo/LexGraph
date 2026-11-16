-- LexGraph SQLite schema as created by Base.metadata.create_all() at commit
-- 251e19d (2026-07-26), generated from that commit's own ORM models.
-- Every workspace bootstrapped or demo-seeded from 251e19d until 47507b3 (both 2026-07-26) has exactly
-- this schema; the next schema change is the raw-text columns (47507b3).
-- Do not edit: tests replay it to build a genuinely old database for
-- app.migrate (backend/tests/integration/test_migrate_runner.py).

CREATE TABLE organizations (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(255) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	email VARCHAR(255) NOT NULL,
	display_name VARCHAR(255) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE repositories (
	id VARCHAR(36) NOT NULL,
	organization_id VARCHAR(36) NOT NULL,
	name VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
);

CREATE TABLE matters (
	id VARCHAR(36) NOT NULL,
	repository_id VARCHAR(36) NOT NULL,
	name VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(repository_id) REFERENCES repositories (id)
);

CREATE TABLE assertions (
	id VARCHAR(36) NOT NULL,
	organization_id VARCHAR(36) NOT NULL,
	repository_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	assertion_type VARCHAR(255) NOT NULL,
	proposition TEXT NOT NULL,
	subject_entity_type VARCHAR(255) NOT NULL,
	subject_entity_id VARCHAR(255) NOT NULL,
	object_entity_type VARCHAR(255),
	object_entity_id VARCHAR(255),
	origin VARCHAR(64) NOT NULL,
	status VARCHAR(64) NOT NULL,
	author_user_id VARCHAR(36) NOT NULL,
	confidence FLOAT,
	jurisdiction VARCHAR(255),
	effective_from DATETIME,
	effective_to DATETIME,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	submitted_at DATETIME,
	reviewed_by VARCHAR(36),
	reviewed_at DATETIME,
	superseded_by_assertion_id VARCHAR(36),
	current_revision_number INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(repository_id) REFERENCES repositories (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id),
	FOREIGN KEY(author_user_id) REFERENCES users (id),
	FOREIGN KEY(reviewed_by) REFERENCES users (id),
	FOREIGN KEY(superseded_by_assertion_id) REFERENCES assertions (id)
);

CREATE TABLE documents (
	id VARCHAR(36) NOT NULL,
	repository_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(repository_id) REFERENCES repositories (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id)
);

CREATE TABLE matter_roles (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	role VARCHAR(32) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_matter_roles_user_matter UNIQUE (user_id, matter_id),
	CONSTRAINT ck_matter_roles_role_valid CHECK (role IN ('viewer', 'contributor', 'reviewer', 'admin')),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id)
);

CREATE TABLE assertion_comments (
	id VARCHAR(36) NOT NULL,
	assertion_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	parent_comment_id VARCHAR(36),
	comment_text TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(assertion_id) REFERENCES assertions (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(parent_comment_id) REFERENCES assertion_comments (id)
);

CREATE TABLE assertion_revisions (
	id VARCHAR(36) NOT NULL,
	assertion_id VARCHAR(36) NOT NULL,
	revision_number INTEGER NOT NULL,
	proposition TEXT NOT NULL,
	assertion_type VARCHAR(255) NOT NULL,
	subject_entity_type VARCHAR(255) NOT NULL,
	subject_entity_id VARCHAR(255) NOT NULL,
	object_entity_type VARCHAR(255),
	object_entity_id VARCHAR(255),
	jurisdiction VARCHAR(255),
	effective_from DATETIME,
	effective_to DATETIME,
	revision_reason TEXT,
	edited_by_user_id VARCHAR(36) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(assertion_id) REFERENCES assertions (id),
	FOREIGN KEY(edited_by_user_id) REFERENCES users (id)
);

CREATE TABLE source_spans (
	id VARCHAR(36) NOT NULL,
	document_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	quote_text TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(document_id) REFERENCES documents (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id)
);

CREATE TABLE assertion_evidence (
	id VARCHAR(36) NOT NULL,
	assertion_id VARCHAR(36) NOT NULL,
	source_span_id VARCHAR(36) NOT NULL,
	evidence_role VARCHAR(64) NOT NULL,
	added_by_user_id VARCHAR(36) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(assertion_id) REFERENCES assertions (id),
	FOREIGN KEY(source_span_id) REFERENCES source_spans (id),
	FOREIGN KEY(added_by_user_id) REFERENCES users (id)
);

CREATE TABLE assertion_ratings (
	id VARCHAR(36) NOT NULL,
	organization_id VARCHAR(36) NOT NULL,
	repository_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	assertion_id VARCHAR(36) NOT NULL,
	assertion_revision_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	strength INTEGER NOT NULL,
	rationale TEXT,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_assertion_ratings_user_revision UNIQUE (user_id, assertion_revision_id),
	CONSTRAINT ck_assertion_ratings_strength_range CHECK (strength BETWEEN 1 AND 5),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(repository_id) REFERENCES repositories (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id),
	FOREIGN KEY(assertion_id) REFERENCES assertions (id),
	FOREIGN KEY(assertion_revision_id) REFERENCES assertion_revisions (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE audit_events (
	id VARCHAR(36) NOT NULL,
	actor_user_id VARCHAR(36) NOT NULL,
	event_type VARCHAR(128) NOT NULL,
	timestamp DATETIME NOT NULL,
	repository_id VARCHAR(36) NOT NULL,
	matter_id VARCHAR(36) NOT NULL,
	assertion_id VARCHAR(36),
	assertion_revision_id VARCHAR(36),
	previous_value TEXT,
	new_value TEXT,
	correlation_id VARCHAR(64),
	PRIMARY KEY (id),
	FOREIGN KEY(actor_user_id) REFERENCES users (id),
	FOREIGN KEY(repository_id) REFERENCES repositories (id),
	FOREIGN KEY(matter_id) REFERENCES matters (id),
	FOREIGN KEY(assertion_id) REFERENCES assertions (id),
	FOREIGN KEY(assertion_revision_id) REFERENCES assertion_revisions (id)
);
