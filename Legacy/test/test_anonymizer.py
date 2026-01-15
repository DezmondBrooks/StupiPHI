from stupify_phi.anonymizer import anonymize

def test_email_anonymization():
    fake = anonymize("john@example.com", "email")
    assert "@" in fake
    assert fake != "john@example.com"

def test_ssn_anonymization():
    fake = anonymize("123-45-6789", "ssn")
    assert fake != "123-45-6789"
    assert len(fake.split("-")) == 3

def test_default_redaction():
    result = anonymize("some value", "unknown_type")
    assert result == "[REDACTED]"
