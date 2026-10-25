import ssl

from nextmove.integrations import gemini, guardian_providers, serpapi


class FakeResponse:
    def __init__(self, body=b"{}"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.body


def verified_fake(captured):
    def open_url(request, *, timeout, context):
        captured.append(context)
        return FakeResponse()

    return open_url


def assert_verified(contexts):
    assert len(contexts) == 1
    assert contexts[0].verify_mode == ssl.CERT_REQUIRED
    assert contexts[0].check_hostname is True


def test_guardian_transport_uses_verified_certifi_context(monkeypatch):
    contexts = []
    monkeypatch.setattr(guardian_providers, "urlopen", verified_fake(contexts))
    assert guardian_providers._get_json("https://serpapi.com/search.json", 1) == {}
    assert_verified(contexts)


def test_general_serpapi_transport_uses_verified_certifi_context(monkeypatch):
    contexts = []
    monkeypatch.setattr(serpapi, "urlopen", verified_fake(contexts))
    assert serpapi._default_get("https://serpapi.com/search.json", 1) == {}
    assert_verified(contexts)


def test_gemini_transport_uses_verified_certifi_context(monkeypatch):
    contexts = []
    monkeypatch.setattr(gemini, "urlopen", verified_fake(contexts))
    assert gemini._default_post("https://generativelanguage.googleapis.com/test", {}, 1) == {}
    assert_verified(contexts)
