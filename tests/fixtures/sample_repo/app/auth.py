# Authentication helpers for the fixture.
def validate_token(token):
    return bool(token and token.startswith("demo_"))
