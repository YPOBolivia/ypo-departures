CREATE SCHEMA IF NOT EXISTS departures;
SET search_path = departures;

CREATE TABLE IF NOT EXISTS events (
  id             serial PRIMARY KEY,
  code           text UNIQUE NOT NULL,
  name           text NOT NULL,
  scope          text NOT NULL DEFAULT 'chapter' CHECK (scope IN ('chapter','regional')),
  audience_label text NOT NULL,
  chips          text[] NOT NULL DEFAULT '{}',
  tags           text[] NOT NULL DEFAULT '{}',
  mail_lists     text[] NOT NULL DEFAULT '{}',
  start_date     date,
  end_date       date,
  city           text,
  status         text NOT NULL DEFAULT 'scheduled'
                 CHECK (status IN ('scheduled','captain','dated','boarding','final_call','gate_closed','delayed','in_flight','landed')),
  status_note    text,
  previous_date  text,
  day_chair      text,
  champions      text,
  quote          text,
  photo_token    text,
  connect_url    text,
  score          numeric(3,1),
  score_n        int,
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS photos (
  id         serial PRIMARY KEY,
  token      text UNIQUE NOT NULL,
  mime       text NOT NULL,
  data       bytea NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_queue (
  id          serial PRIMARY KEY,
  event_id    int NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  stage       text NOT NULL,
  recipients  text[] NOT NULL,
  subject     text NOT NULL,
  html        text NOT NULL,
  text        text NOT NULL,
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','discarded')),
  error       text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  decided_at  timestamptz
);
CREATE INDEX IF NOT EXISTS email_queue_pending ON email_queue (status, event_id);

CREATE TABLE IF NOT EXISTS status_log (
  id          serial PRIMARY KEY,
  event_id    int NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  from_status text,
  to_status   text NOT NULL,
  at          timestamptz NOT NULL DEFAULT now()
);
