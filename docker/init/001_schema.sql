-- Minimal toy healthcare-ish schema for slice extraction demos

CREATE TABLE patients (
  id BIGSERIAL PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  dob DATE NOT NULL,
  phone TEXT,
  email TEXT,
  address TEXT
);

CREATE TABLE therapists (
  id BIGSERIAL PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT
);

CREATE TABLE cases (
  id BIGSERIAL PRIMARY KEY,
  patient_id BIGINT NOT NULL REFERENCES patients(id),
  status TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE payments (
  id BIGSERIAL PRIMARY KEY,
  patient_id BIGINT NOT NULL REFERENCES patients(id),
  method TEXT NOT NULL,
  last4 TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE appointments (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT NOT NULL REFERENCES cases(id),
  therapist_id BIGINT NOT NULL REFERENCES therapists(id),
  scheduled_at TIMESTAMP NOT NULL,
  notes TEXT
);