from stupify_phi.detector import detect_fields

def test_detect_email_and_ssn():
    row = {
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "note": "Just a comment."
    }
    detected = detect_fields(row)
    assert detected["email"] == "email"
    assert detected["ssn"] == "ssn"
    assert "note" not in detected
