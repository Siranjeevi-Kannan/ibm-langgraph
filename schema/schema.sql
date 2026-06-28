DROP TABLE IF EXISTS interactions;

CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT    NOT NULL,
    intent      TEXT    NOT NULL,
    query       TEXT    NOT NULL,
    response    TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interactions_customer_id
    ON interactions (customer_id);

CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
    ON interactions (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_interactions_intent
    ON interactions (intent);

CREATE TABLE IF NOT EXISTS approval_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  TEXT    NOT NULL,
    query        TEXT    NOT NULL,
    intent       TEXT    NOT NULL,
    decision     TEXT    NOT NULL,
    supervisor   TEXT    DEFAULT 'human_supervisor',
    notes        TEXT    DEFAULT '',
    timestamp    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_approval_log_customer_id
    ON approval_log (customer_id);