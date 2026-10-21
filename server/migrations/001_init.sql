CREATE TABLE IF NOT EXISTS domains (
    id           smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hostname     text NOT NULL UNIQUE CHECK (hostname ~ '^[a-z0-9.-]+$'),
    display_name text NOT NULL,
    is_active    boolean NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS check_results (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domain_id        smallint NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    checked_at       timestamptz NOT NULL DEFAULT now(),
    is_up            boolean NOT NULL,
    status_code      smallint CHECK (status_code BETWEEN 100 AND 599),
    response_time_ms integer CHECK (response_time_ms >= 0),
    error            text,
    CHECK (NOT is_up OR (status_code IS NOT NULL AND error IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_check_results_domain_checked
    ON check_results (domain_id, checked_at DESC);

INSERT INTO domains (hostname, display_name) VALUES
    ('german-emirates-club.com', 'German Emirates Club'),
    ('german-industry-club.com', 'German Industry Club'),
    ('german-medical-society.com', 'German Medical Society'),
    ('angels-bureau.com', 'Angels Bureau')
ON CONFLICT (hostname) DO NOTHING;
