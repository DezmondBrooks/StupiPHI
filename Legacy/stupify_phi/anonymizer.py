from faker import Faker

faker = Faker()

def anonymize(value: str, field_type: str) -> str:
    try:
        if field_type == "email":
            return faker.email()
        elif field_type == "ssn":
            return faker.ssn()
        elif field_type == "phone":
            return faker.phone_number()
        elif field_type == "name":
            return faker.name()
        else:
            return "[REDACTED]"
    except Exception:
        return "[FAILED]"
