INSERT INTO patients (first_name, last_name, dob, phone, email, address)
VALUES
('Danielle', 'Johnson', '1990-01-01', '533-521-8196x001', 'danielle.j@example.com', '386 Shane Harbors, Port Lindachester, MA 36922'),
('John', 'Doe', '1985-02-14', '555-123-4567', 'john.doe@example.com', '123 Main St, Springfield, CA');

INSERT INTO therapists (first_name, last_name, email)
VALUES
('Alex', 'Kim', 'alex.kim@clinic.example'),
('Sam', 'Patel', 'sam.patel@clinic.example');

INSERT INTO cases (patient_id, status)
VALUES
(1, 'open'),
(2, 'open');

INSERT INTO payments (patient_id, method, last4)
VALUES
(1, 'card', '4242'),
(2, 'card', '1111');

INSERT INTO appointments (case_id, therapist_id, scheduled_at, notes)
VALUES
(1, 1, NOW() + INTERVAL '2 days', 'Patient Danielle Johnson reports headache. Call 533-521-8196x001.'),
(2, 2, NOW() + INTERVAL '3 days', 'Patient John Doe prefers email john.doe@example.com.');