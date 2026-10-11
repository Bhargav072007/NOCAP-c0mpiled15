-- REVIEW ONLY: generated from current schema. Use Alembic for approved migrations.

CREATE TABLE access_tokens (
	digest VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	member_id VARCHAR(64),
	device_id VARCHAR(64),
	expires_at VARCHAR(40),
	revoked BOOLEAN NOT NULL,
	PRIMARY KEY (digest)
)

;
CREATE INDEX ix_access_tokens_org_id ON access_tokens (org_id);


CREATE TABLE audit_events (
	sequence SERIAL NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	actor VARCHAR(64) NOT NULL,
	action VARCHAR(100) NOT NULL,
	target VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (sequence)
)

;
CREATE INDEX ix_audit_events_org_id ON audit_events (org_id);


CREATE TABLE captures (
	sequence SERIAL NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	id VARCHAR(64) NOT NULL,
	device_id VARCHAR(64) NOT NULL,
	file_sha256 VARCHAR(64) NOT NULL,
	record_hash VARCHAR(64) NOT NULL,
	payload JSON NOT NULL,
	object_key VARCHAR(300) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (sequence),
	UNIQUE (org_id, id)
)

;
CREATE INDEX ix_captures_org_digest ON captures (org_id, file_sha256);
CREATE INDEX ix_captures_org_sequence ON captures (org_id, sequence);


CREATE TABLE comments (
	id VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	work_id VARCHAR(64) NOT NULL,
	author_id VARCHAR(64) NOT NULL,
	body TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_comments_org_id ON comments (org_id);
CREATE INDEX ix_comments_work_id ON comments (work_id);


CREATE TABLE devices (
	id VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	name VARCHAR(120) NOT NULL,
	location VARCHAR(240) NOT NULL,
	public_key TEXT NOT NULL,
	enabled BOOLEAN NOT NULL,
	last_seen VARCHAR(40),
	firmware VARCHAR(80),
	fixture BOOLEAN NOT NULL,
	last_hash VARCHAR(64) NOT NULL,
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_devices_org_id ON devices (org_id);


CREATE TABLE members (
	id VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	name VARCHAR(120) NOT NULL,
	email VARCHAR(254) NOT NULL,
	role VARCHAR(24) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (org_id, email)
)

;
CREATE INDEX ix_members_org_id ON members (org_id);


CREATE TABLE organizations (
	id VARCHAR(64) NOT NULL,
	name VARCHAR(120) NOT NULL,
	PRIMARY KEY (id)
)

;



CREATE TABLE reports (
	id VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	payload JSON NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_reports_org_id ON reports (org_id);


CREATE TABLE work_items (
	id VARCHAR(64) NOT NULL,
	org_id VARCHAR(64) NOT NULL,
	title VARCHAR(200) NOT NULL,
	section VARCHAR(120) NOT NULL,
	owner_id VARCHAR(64) NOT NULL,
	status VARCHAR(30) NOT NULL,
	priority VARCHAR(16) NOT NULL,
	capture_id VARCHAR(64),
	version INTEGER NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_work_items_org_id ON work_items (org_id);
