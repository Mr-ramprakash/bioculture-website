import asyncio
import hashlib
import hmac
import json
import os
import time
import unittest
import urllib.error
from unittest.mock import patch

from fastapi.testclient import TestClient

from chatbot.auth import mint_tenant_token
from chatbot.config import Settings
from chatbot.connectors.bioman import BiomanConnector
from chatbot.knowledge_api import (
    KNOWLEDGE_API_PATH,
    KnowledgeApiError,
    KnowledgeServiceClient,
    KnowledgeServiceProvider,
    _hmac_headers,
    _signed_request,
    configured_knowledge_provider,
)
from chatbot.main import create_app
from chatbot.service import FALLBACK_EN


API_URL = "https://knowledge.example/knowledge/search"
TEST_KEY_ID = "vercel-bioman-v1"
TEST_SECRET = "test-only-hmac-secret-with-adequate-entropy"


class StubGroq:
    def __init__(self):
        self.calls = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        return "Mocked grounded answer."


def approved_record(record_id="approved-1", answer="Approved public answer"):
    return {
        "record_id": record_id,
        "topic": "usage",
        "question": "How do I use it?",
        "answer": answer,
        "language": "en",
        "approved": True,
        "status": "approved",
        "public": True,
    }


class KnowledgeApiTests(unittest.TestCase):
    def test_hmac_header_signs_timestamp_nonce_method_path_and_exact_body(self):
        timestamp = "1793702254"
        nonce = "abcdefghijklmnopqrstuvwx"
        body = '{"query":"Bio-Culture தமிழ்"}'.encode("utf-8")
        headers = _hmac_headers(body, TEST_KEY_ID, TEST_SECRET, timestamp, nonce)
        canonical = f"{timestamp}\n{nonce}\nPOST\n{KNOWLEDGE_API_PATH}\n".encode("ascii") + body
        expected = hmac.new(TEST_SECRET.encode(), canonical, hashlib.sha256).hexdigest()
        self.assertEqual(headers["X-Knowledge-Key-Id"], TEST_KEY_ID)
        self.assertEqual(headers["X-Knowledge-Timestamp"], timestamp)
        self.assertEqual(headers["X-Knowledge-Nonce"], nonce)
        self.assertEqual(headers["X-Knowledge-Signature"], expected)
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_signed_request_posts_the_same_body_with_fresh_nonce(self):
        timestamp = "1793702254"
        body = b'{"query":"question"}'

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b'{"ok":true}'

        captured = {}

        def open_request(request, timeout):
            captured.update(request=request, timeout=timeout)
            return Response()

        with patch("chatbot.knowledge_api.time.time", return_value=int(timestamp)):
            with patch("chatbot.knowledge_api.secrets.token_urlsafe", return_value="a" * 32):
                with patch("chatbot.knowledge_api._open_without_redirect", side_effect=open_request):
                    result = _signed_request(API_URL, body, TEST_KEY_ID, TEST_SECRET, 4.5)

        request = captured["request"]
        self.assertEqual(result, b'{"ok":true}')
        self.assertEqual(request.data, body)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, API_URL)
        self.assertEqual(captured["timeout"], 4.5)
        sent = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(sent["x-knowledge-key-id"], TEST_KEY_ID)
        self.assertEqual(sent["x-knowledge-timestamp"], timestamp)
        self.assertEqual(sent["x-knowledge-nonce"], "a" * 32)
        canonical = f"{timestamp}\n{'a' * 32}\nPOST\n{KNOWLEDGE_API_PATH}\n".encode() + body
        self.assertEqual(sent["x-knowledge-signature"], hmac.new(TEST_SECRET.encode(), canonical, hashlib.sha256).hexdigest())

    def test_client_requires_https_exact_path_valid_key_id_and_strong_secret(self):
        for url in (
            "http://knowledge.example/knowledge/search",
            "https://knowledge.example/wrong-path",
            "https://knowledge.example/knowledge/search?x=1",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                KnowledgeServiceClient(url, TEST_KEY_ID, TEST_SECRET)
        with self.assertRaises(ValueError):
            KnowledgeServiceClient(API_URL, "bad key id", TEST_SECRET)
        with self.assertRaisesRegex(ValueError, "at least 32 bytes"):
            KnowledgeServiceClient(API_URL, TEST_KEY_ID, "short")

    def test_configured_provider_uses_url_key_id_and_secret_environment_variables(self):
        environment = {
            "KNOWLEDGE_SERVICE_URL": API_URL,
            "KNOWLEDGE_SERVICE_KEY_ID": TEST_KEY_ID,
            "KNOWLEDGE_SERVICE_HMAC_SECRET": TEST_SECRET,
        }
        with patch.dict(os.environ, environment, clear=True):
            provider = configured_knowledge_provider()
        self.assertIsInstance(provider, KnowledgeServiceProvider)
        self.assertIsInstance(provider.client, KnowledgeServiceClient)
        self.assertEqual(provider.client.url, API_URL)
        self.assertEqual(provider.client.key_id, TEST_KEY_ID)

    def test_invalid_configuration_logs_no_url_or_secret(self):
        bad_url = "http://knowledge.example/knowledge/search?secret-in-url"
        with self.assertLogs("automategenie.knowledge", level="WARNING") as captured:
            with patch.dict(os.environ, {
                "KNOWLEDGE_SERVICE_URL": bad_url,
                "KNOWLEDGE_SERVICE_KEY_ID": TEST_KEY_ID,
                "KNOWLEDGE_SERVICE_HMAC_SECRET": TEST_SECRET,
            }, clear=True):
                provider = configured_knowledge_provider()
        self.assertIsNone(provider.client)
        logs = "\n".join(captured.output)
        self.assertIn("Knowledge service configuration is invalid", logs)
        self.assertNotIn("secret-in-url", logs)
        self.assertNotIn(TEST_SECRET, logs)

    def test_client_sends_only_query_and_filters_all_three_public_approval_fields(self):
        records = [
            approved_record("public-1"),
            {**approved_record("draft"), "status": "draft"},
            {**approved_record("unapproved"), "approved": False},
            {**approved_record("private"), "public": False},
            {**approved_record("no-status"), "status": None},
        ]
        captured = {}

        def signed(url, body, key_id, secret, timeout):
            captured.update(url=url, body=body, key_id=key_id, secret=secret, timeout=timeout)
            return json.dumps({"company_code": "BIOMAN", "records": records}).encode("utf-8")

        client = KnowledgeServiceClient(API_URL, TEST_KEY_ID, TEST_SECRET)
        with patch("chatbot.knowledge_api._signed_request", side_effect=signed):
            found = asyncio.run(client.search("BIOMAN", "  How do I use it?  ", public_only=False))

        self.assertEqual(captured["url"], API_URL)
        self.assertEqual(captured["key_id"], TEST_KEY_ID)
        self.assertEqual(captured["secret"], TEST_SECRET)
        self.assertEqual(json.loads(captured["body"]), {"query": "How do I use it?"})
        self.assertEqual([item.record_id for item in found], ["public-1"])

    def test_non_bioman_company_never_calls_the_fixed_bioman_service(self):
        client = KnowledgeServiceClient(API_URL, TEST_KEY_ID, TEST_SECRET)
        with patch("chatbot.knowledge_api._signed_request", side_effect=AssertionError("must not call BIOMAN API")) as signed:
            self.assertEqual(asyncio.run(client.search("ROCOTILE", "question")), [])
        signed.assert_not_called()

    def test_different_company_or_malformed_response_is_rejected(self):
        client = KnowledgeServiceClient(API_URL, TEST_KEY_ID, TEST_SECRET)
        for response in (b'{"company_code":"ROCOTILE","records":[]}', b"not-json", b'{"company_code":"BIOMAN","records":{}}'):
            with self.subTest(response=response):
                with patch("chatbot.knowledge_api._signed_request", return_value=response):
                    with self.assertRaises(KnowledgeApiError):
                        asyncio.run(client.search("BIOMAN", "question"))

    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = configured_knowledge_provider()
        with self.assertRaisesRegex(KnowledgeApiError, "not configured"):
            asyncio.run(provider.search("BIOMAN", "question"))

    def test_auth_rejection_and_timeout_are_safe_and_do_not_log_query_or_secret(self):
        query = "private customer question"
        http_error = urllib.error.HTTPError(API_URL, 401, "Unauthorized", {}, None)
        with self.assertLogs("automategenie.knowledge", level="WARNING") as captured:
            with patch("chatbot.knowledge_api._open_without_redirect", side_effect=http_error):
                with self.assertRaisesRegex(KnowledgeApiError, "request was rejected"):
                    _signed_request(API_URL, json.dumps({"query": query}).encode(), TEST_KEY_ID, TEST_SECRET, 5)
        logs = "\n".join(captured.output)
        self.assertIn("status=401", logs)
        self.assertNotIn(query, logs)
        self.assertNotIn(TEST_SECRET, logs)
        with patch("chatbot.knowledge_api._open_without_redirect", side_effect=TimeoutError()):
            with self.assertRaisesRegex(KnowledgeApiError, "unavailable"):
                _signed_request(API_URL, b'{"query":"q"}', TEST_KEY_ID, TEST_SECRET, 5)

    def test_production_chat_uses_ec2_knowledge_and_preserves_groq_response(self):
        tenant_key = "bioman-test-secret-that-is-long-enough"
        settings = Settings(
            app_env="production",
            groq_api_key="test-only",
            groq_model_id="test-model",
            signing_keys={"BIOMAN": tenant_key},
            tenant_registry={"BIOMAN": {"connector": "bioman", "active": True, "company_code": "BIOMAN"}},
        )
        groq = StubGroq()
        record = approved_record(answer="Verified public usage guidance")
        record_payload = {"company_code": "BIOMAN", "records": [record]}
        captured_bodies = []

        def fake_signed(_url, body, _key_id, _secret, _timeout):
            captured_bodies.append(json.loads(body))
            return json.dumps(record_payload).encode()

        environment = {
            "KNOWLEDGE_SERVICE_URL": API_URL,
            "KNOWLEDGE_SERVICE_KEY_ID": TEST_KEY_ID,
            "KNOWLEDGE_SERVICE_HMAC_SECRET": TEST_SECRET,
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch("chatbot.knowledge_api._signed_request", side_effect=fake_signed):
                app = create_app(settings=settings, connectors={"BIOMAN": BiomanConnector()}, groq_client=groq)
                client = TestClient(app)
                token = mint_tenant_token("BIOMAN", tenant_key, expires_at=int(time.time()) + 300)
                response = client.post("/chat", json={"message": "How do I use it?"}, headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "approved_company_knowledge")
        self.assertEqual(response.json()["answer"], "Mocked grounded answer.")
        self.assertEqual(captured_bodies, [{"query": "How do I use it?"}])
        context = groq.calls[0]["messages"][-1]["content"]
        self.assertIn("Verified public usage guidance", context)
        self.assertNotIn("status", context)

    def test_production_product_cards_and_price_actions_remain_unchanged(self):
        tenant_key = "bioman-test-secret-that-is-long-enough"
        settings = Settings(
            app_env="production",
            signing_keys={"BIOMAN": tenant_key},
            tenant_registry={"BIOMAN": {"connector": "bioman", "active": True, "company_code": "BIOMAN"}},
        )
        env = {
            "KNOWLEDGE_SERVICE_URL": API_URL,
            "KNOWLEDGE_SERVICE_KEY_ID": TEST_KEY_ID,
            "KNOWLEDGE_SERVICE_HMAC_SECRET": TEST_SECRET,
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("chatbot.knowledge_api._signed_request", return_value=b'{"company_code":"BIOMAN","records":[]}'):
                client = TestClient(create_app(settings=settings, connectors={"BIOMAN": BiomanConnector()}))
                token = mint_tenant_token("BIOMAN", tenant_key, expires_at=int(time.time()) + 300)
                response = client.post("/chat", json={"message": "I want 2 packets of Bio-Culture"}, headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["source"], "authorized_product_catalog")
        self.assertEqual(payload["cards"][0]["price"], {"amount": 1649, "currency": "INR", "label": "current"})
        self.assertEqual(payload["actions"][0]["pack"], 2)
        self.assertEqual(payload["actions"][0]["variant_id"], "pack-2")

    def test_production_unknown_question_keeps_the_existing_safe_fallback(self):
        tenant_key = "bioman-test-secret-that-is-long-enough"
        settings = Settings(
            app_env="production",
            signing_keys={"BIOMAN": tenant_key},
            tenant_registry={"BIOMAN": {"connector": "bioman", "active": True, "company_code": "BIOMAN"}},
        )
        env = {
            "KNOWLEDGE_SERVICE_URL": API_URL,
            "KNOWLEDGE_SERVICE_KEY_ID": TEST_KEY_ID,
            "KNOWLEDGE_SERVICE_HMAC_SECRET": TEST_SECRET,
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("chatbot.knowledge_api._signed_request", return_value=b'{"company_code":"BIOMAN","records":[]}'):
                client = TestClient(create_app(settings=settings, connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()))
                token = mint_tenant_token("BIOMAN", tenant_key, expires_at=int(time.time()) + 300)
                response = client.post("/chat", json={"message": "Will you book my flight?"}, headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["answer"], FALLBACK_EN)
        self.assertEqual(response.json()["source"], "no_verified_match")


if __name__ == "__main__":
    unittest.main()
