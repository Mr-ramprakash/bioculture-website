from __future__ import annotations

import asyncio
import json
import os
import time
import unittest
from dataclasses import dataclass, replace
from unittest.mock import AsyncMock, patch

import httpx

from fastapi.testclient import TestClient

from chatbot.auth import TenantTokenError, mint_tenant_token, verify_tenant_token
from chatbot.config import ConfigurationError, Settings
from chatbot.connectors.base import KnowledgeRecord, Product
from chatbot.connectors.bioman import BIOMAN_PRODUCTS, BiomanConnector
from chatbot.connectors.bioman_knowledge import BIOMAN_KNOWLEDGE, QUESTION_VARIATION_COUNT
from chatbot.connectors.generic_rest import ConnectorConfigurationError, GenericRestConnector
from chatbot.main import _create_runtime_app, create_app as _create_app
from chatbot.rate_limit import DevelopmentRateLimiter
from chatbot.service import FALLBACK_EN, ChatDependencyError, ChatService as _ChatService
from chatbot.sessions import InMemorySessionStore, SessionTenantMismatch


KEYS = {"BIOMAN": "bioman-test-secret-that-is-long-enough", "ROCOTILE": "rocotile-test-secret-that-is-long-enough"}
REGISTRY = {
    "BIOMAN": {"connector": "bioman", "active": True},
    "ROCOTILE": {"connector": "rest", "connector_key": "rocotile-test", "company_code": "ROCOTILE", "active": True},
}


@dataclass
class StubConnector:
    company_code: str
    products: list[Product]
    knowledge: list[KnowledgeRecord]

    async def search_products(self, query):
        return list(self.products)

    async def validate_product(self, product_id, variant_id, pack=None):
        return next((p for p in self.products if p.product_id == product_id and p.variant_id == variant_id and p.pack == pack), None)

    async def search_knowledge(self, query):
        return list(self.knowledge)


class StubGroq:
    def __init__(self, result="A grounded response.", failure=None):
        self.result = result
        self.failure = failure
        self.calls = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return self.result


class EmptyKnowledgeProvider:
    async def search(self, company_code, query, *, public_only=False):
        return []


def ChatService(connectors, groq_client, session_store, max_history_messages=10):
    return _ChatService(connectors, groq_client, session_store, max_history_messages)


def create_app(**kwargs):
    return _create_app(**kwargs)


def settings():
    return Settings(
        groq_api_key="test-only",
        groq_model_id="test-configured-model",
        cors_origins=("http://localhost:5173",),
        signing_keys=KEYS,
        tenant_registry=REGISTRY,
        rate_limit_requests=5,
        rate_limit_window_seconds=60,
        session_ttl_seconds=1800,
        max_message_length=2000,
        max_history_messages=4,
        groq_timeout_seconds=2,
    )


def token(tenant="BIOMAN", origin=None):
    return mint_tenant_token(tenant, KEYS[tenant], expires_at=int(time.time()) + 300, origin=origin)


class BackendTests(unittest.TestCase):
    def test_enabled_public_sessions_with_incomplete_bioman_registry_are_diagnosed(self):
        origin = "https://bioculture-ai-chatbot.vercel.app"
        environment = {
            "VERCEL_ENV": "production",
            "APP_ENV": "production",
            "CHAT_PUBLIC_SESSION_ENABLED": "true",
            "CHAT_PUBLIC_TENANT_ID": "BIOMAN",
            "CHAT_PUBLIC_ORIGINS": origin,
            "CORS_ORIGINS": origin,
            "CHAT_TENANT_SIGNING_KEYS_JSON": '{"BIOMAN":"test-only-bioman-signing-key"}',
            "CHAT_TENANT_REGISTRY_JSON": '{"BIOMAN":{"connector":"bioman","active":true}}',
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "Public tenant must explicitly enable"):
                Settings.from_environment()
            with self.assertLogs("automategenie.chat", level="WARNING") as captured:
                runtime_app = _create_runtime_app()

        from vercel_entry_loader import load_root_vercel_entry

        VercelRewritePath = load_root_vercel_entry().VercelRewritePath

        response = TestClient(VercelRewritePath(runtime_app)).post(
            "/api?__vercel_path=/api/chat-api/public/session",
            headers={"Origin": origin},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})
        diagnostics = "\n".join(captured.output)
        self.assertIn("app_env=development", diagnostics)
        self.assertIn("public_session_enabled=False", diagnostics)
        self.assertIn("bioman_active=False", diagnostics)
        self.assertIn("bioman_publicly_enabled=False", diagnostics)
        self.assertIn("public_session_route_registered=True", diagnostics)
        self.assertIn("configuration_valid=False", diagnostics)
        self.assertIn("enable public sessions, public knowledge, and public products", diagnostics)
        self.assertNotIn("test-only-bioman-signing-key", diagnostics)

    def test_app_environment_defaults_from_vercel_production_context(self):
        with patch.dict(os.environ, {"VERCEL_ENV": "production"}, clear=True):
            self.assertEqual(Settings.from_environment().app_env, "production")

    def test_chat_and_catalog_work_without_ec2_environment_in_development(self):
        groq = StubGroq()
        connector = BiomanConnector()
        with patch.dict(os.environ, {
            "KNOWLEDGE_SERVICE_URL": "", "KNOWLEDGE_SERVICE_KEY_ID": "",
            "KNOWLEDGE_SERVICE_HMAC_SECRET": "",
        }):
            with patch.object(connector, "search_products", wraps=connector.search_products) as catalog_search:
                client = TestClient(_create_app(settings=settings(), connectors={"BIOMAN": connector}, groq_client=groq))
                headers = {"Authorization": f"Bearer {token()}"}
                greeting = client.post("/chat-api/chat", json={"message": "hello"}, headers=headers)
                catalog = client.post("/chat-api/chat", json={"message": "I want 2 packets of Bio-Culture"}, headers=headers)
                self.assertGreaterEqual(catalog_search.await_count, 1)
        self.assertEqual(greeting.status_code, 200)
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.json()["source"], "authorized_product_catalog")
        self.assertEqual(groq.calls, [])

    def test_vercel_same_origin_route_aliases_reach_fastapi(self):
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()))
        self.assertEqual(client.get("/chat-api/health").status_code, 200)
        self.assertEqual(client.get("/api/chat-api/health").status_code, 200)
        self.assertEqual(client.post("/chat-api/chat", json={"message": "hello"}).status_code, 401)
        self.assertEqual(client.post("/api/chat-api/chat", json={"message": "hello"}).status_code, 401)
        self.assertEqual(client.post("/chat-api/public/session", headers={"Origin": "https://shop.example"}).status_code, 404)

    def test_bioman_connector_preserves_pack_mapping_and_catalog_price(self):
        self.assertEqual([p.pack for p in BIOMAN_PRODUCTS], [1, 2, 3, 5, 10])
        connector = BiomanConnector()
        implicit_product = asyncio.run(connector.search_products("I want 2 packets of 500 gm."))
        self.assertEqual([p.product_id for p in implicit_product], ["bioculture-pack-2"])
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()))
        response = client.post(
            "/chat",
            json={"message": "I want 2 packets of 500 gm."},
            headers={"Authorization": f"Bearer {token()}"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"answer", "company_code", "source", "session_id", "cards", "actions"})
        self.assertEqual(body["cards"][0]["product_id"], "bioculture-pack-2")
        self.assertEqual(set(body["cards"][0]), {"type", "product_id", "title", "variant", "description", "price", "buttons"})
        self.assertEqual(body["cards"][0]["price"], {"amount": 1649, "currency": "INR", "label": "current"})
        self.assertEqual(body["actions"][0]["pack"], 2)
        self.assertEqual(body["actions"][0]["variant_id"], "pack-2")
        self.assertNotIn("mrp", str(body).lower())

    def test_bioman_knowledge_has_100_searchable_question_variations(self):
        self.assertEqual(QUESTION_VARIATION_COUNT, 100)
        self.assertEqual(sum(len(entry.questions) for entry in BIOMAN_KNOWLEDGE), 100)
        self.assertGreaterEqual(len({entry.topic for entry in BIOMAN_KNOWLEDGE}), 12)
        connector = BiomanConnector()
        for entry in BIOMAN_KNOWLEDGE:
            for question in entry.questions:
                matches = asyncio.run(connector.search_knowledge(question))
                self.assertIn(entry.record_id, [record.record_id for record in matches], question)

    def test_local_public_json_retrieval_and_groq_grounding_need_no_aws_configuration(self):
        records = [{
            "record_id": "sludge", "topic": "Product benefits",
            "questions": ["Could this make me pump my septic tank less often?"],
            "answer": "Pump-out intervals depend on tank design and use; this is not guaranteed.",
            "status": "approved", "approved": True, "public": True,
        }]
        with patch("chatbot.knowledge_store.Path.read_text", return_value=json.dumps({"company_code": "BIOMAN", "records": records})):
            groq = StubGroq("The website FAQ says it may help, but results depend on the tank and its use.")
            service = ChatService({"BIOMAN": BiomanConnector()}, groq, InMemorySessionStore())
            with patch.dict(os.environ, {}, clear=True):
                result = asyncio.run(service.answer(
                    tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
                    message="Could this make me pump my septic tank less often?", session_id=None,
                    public_only=True,
                ))
        self.assertEqual(result.source, "approved_company_knowledge")
        self.assertEqual(result.answer, groq.result)
        self.assertEqual(len(groq.calls), 1)
        context = groq.calls[0]["messages"][-1]["content"]
        self.assertIn("Pump-out intervals depend on tank design", context)
        self.assertIn("concise, natural, conversational answer", groq.calls[0]["system"])

    def test_public_json_never_returns_draft_unapproved_or_private_records(self):
        records = [
            {"record_id": "public", "topic": "usage", "questions": ["How do I mix Bio-Culture?"], "answer": "Public approved fact", "status": "approved", "approved": True, "public": True},
            {"record_id": "draft", "topic": "usage", "questions": ["How do I mix Bio-Culture?"], "answer": "DRAFT SECRET", "status": "draft", "approved": False, "public": True},
            {"record_id": "unapproved", "topic": "usage", "questions": ["How do I mix Bio-Culture?"], "answer": "UNAPPROVED SECRET", "status": "approved", "approved": False, "public": True},
            {"record_id": "private", "topic": "usage", "questions": ["How do I mix Bio-Culture?"], "answer": "PRIVATE SECRET", "status": "approved", "approved": True, "public": False},
        ]
        with patch("chatbot.knowledge_store.Path.read_text", return_value=json.dumps({"company_code": "BIOMAN", "records": records})):
            groq = StubGroq("Grounded public answer")
            service = ChatService({"BIOMAN": BiomanConnector()}, groq, InMemorySessionStore())
            result = asyncio.run(service.answer(
                tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
                message="How do I mix Bio-Culture?", session_id=None, public_only=True,
            ))
        context = groq.calls[0]["messages"][-1]["content"]
        self.assertIn("Public approved fact", context)
        self.assertNotIn("SECRET", context)
        self.assertEqual(result.source, "approved_company_knowledge")

    def test_groq_receives_only_verified_bioman_company_knowledge(self):
        records = [{"record_id": "bioman", "topic": "usage", "questions": ["What is the Bioman verified process?"], "answer": "BIOMAN APPROVED FACT", "status": "approved", "approved": True, "public": True}]
        with patch("chatbot.knowledge_store.Path.read_text", return_value=json.dumps({"company_code": "BIOMAN", "records": records})):
            groq = StubGroq()
            service = ChatService({"rocotile-test": StubConnector("ROCOTILE", [], [])}, groq, InMemorySessionStore())
            result = asyncio.run(service.answer(
                tenant_id="ROCOTILE", company_code="ROCOTILE", connector_name="rocotile-test",
                message="What is the Bioman verified process?", session_id=None, public_only=True,
            ))
        self.assertEqual(result.source, "no_verified_match")
        self.assertEqual(groq.calls, [])

    def test_unconfirmed_delivery_and_refund_details_are_explicitly_limited(self):
        connector = BiomanConnector()
        delivery = asyncio.run(connector.search_knowledge("Can you give me an exact delivery date?"))
        refund = asyncio.run(connector.search_knowledge("What is the refund eligibility and timeline?"))
        self.assertEqual(delivery[0].record_id, "delivery-estimates")
        self.assertIn("do not have a verified delivery date", delivery[0].answer)
        self.assertEqual(refund[0].record_id, "cancellation-refunds")
        self.assertIn("cannot promise eligibility or timing", refund[0].answer)

    def test_product_list_returns_only_approved_catalog_variants(self):
        groq = StubGroq("Should not choose products or prices")
        price_list = asyncio.run(BiomanConnector().search_products("Show me the price list"))
        self.assertEqual([product.pack for product in price_list], [1, 2, 3, 5, 10])
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=groq))
        response = client.post(
            "/chat",
            json={"message": "What products do you have?"},
            headers={"Authorization": f"Bearer {token()}"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([card["product_id"] for card in body["cards"]], [f"bioculture-pack-{pack}" for pack in (1, 2, 3, 5, 10)])
        self.assertEqual([card["price"]["amount"] for card in body["cards"]], [895, 1649, 2449, 3900, 7605])
        self.assertEqual([action["pack"] for action in body["actions"]], [1, 2, 3, 5, 10])
        self.assertEqual(groq.calls, [])

    def test_price_followup_reuses_only_user_context_and_never_calls_groq(self):
        groq = StubGroq("This must not be used for catalog pricing")
        connector = BiomanConnector()
        service = ChatService({"BIOMAN": connector}, groq, InMemorySessionStore())
        first = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="I want 2 packets of 500 gm.", session_id=None,
        ))
        followup = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="What's the price?", session_id=first.session_id,
        ))
        mrp_followup = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="What's the MRP?", session_id=first.session_id,
        ))
        buy_followup = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="How can I buy it?", session_id=first.session_id,
        ))
        self.assertEqual(followup.cards[0].product_id, "bioculture-pack-2")
        self.assertEqual(followup.cards[0].price.amount, 1649)
        self.assertEqual(followup.source, "authorized_product_catalog")
        self.assertIn("official MRP", mrp_followup.answer)
        self.assertIn("has not been verified", mrp_followup.answer)
        self.assertIn("INR 1,649", mrp_followup.answer)
        self.assertEqual(mrp_followup.cards[0].price.amount, 1649)
        self.assertEqual(buy_followup.cards[0].product_id, "bioculture-pack-2")
        self.assertEqual(buy_followup.cards[0].price.amount, 1649)
        self.assertEqual(buy_followup.source, "authorized_product_catalog")
        self.assertEqual(groq.calls, [])

    def test_usage_shortcut_does_not_answer_from_unapproved_local_seed(self):
        groq = StubGroq("An unsafe paraphrase")
        service = ChatService({"BIOMAN": BiomanConnector()}, groq, InMemorySessionStore())
        first = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="How do I use Bio-Culture?", session_id=None,
        ))
        tamil = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="Explain that in Tamil.", session_id=first.session_id,
        ))
        self.assertNotIn("half a bucket", first.answer)
        self.assertEqual(first.source, "no_verified_match")
        self.assertEqual(tamil.source, "no_verified_match")
        self.assertEqual(groq.calls, [])

    def test_unknown_question_returns_existing_safe_fallback_without_groq(self):
        groq = StubGroq("This must not be used for an unknown question")
        service = ChatService({"BIOMAN": BiomanConnector()}, groq, InMemorySessionStore())
        result = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="Can you book me a flight to Delhi?", session_id=None,
        ))
        self.assertEqual(result.answer, FALLBACK_EN)
        self.assertEqual(result.source, "no_verified_match")
        self.assertEqual(groq.calls, [])

    def test_greeting_and_thanks_are_friendly_without_groq(self):
        groq = StubGroq("Should not answer greetings")
        service = ChatService({"BIOMAN": BiomanConnector()}, groq, InMemorySessionStore())
        greeting = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="Hi", session_id=None,
        ))
        thanks = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="Thank you.", session_id=greeting.session_id,
        ))
        self.assertIn("here to help", greeting.answer)
        self.assertIn("You're welcome", thanks.answer)
        self.assertEqual(greeting.source, "conversation")
        self.assertEqual(thanks.source, "conversation")
        self.assertEqual(groq.calls, [])

    def test_weak_queries_do_not_retrieve_unrelated_knowledge_and_tamil_fallback_is_localized(self):
        connector = BiomanConnector()
        self.assertEqual(asyncio.run(connector.search_knowledge("Explain in Tamil.")), [])
        self.assertEqual(asyncio.run(connector.search_knowledge("What's the weather?")), [])
        price = asyncio.run(connector.search_knowledge("What's the price?"))
        definition = asyncio.run(connector.search_knowledge("What is Bio-Culture?"))
        self.assertEqual(price[0].record_id, "price-help")
        self.assertEqual(definition[0].record_id, "product-overview")
        groq = StubGroq()
        service = ChatService({"BIOMAN": connector}, groq, InMemorySessionStore())
        result = asyncio.run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="Explain in Tamil.", session_id=None,
        ))
        self.assertIn("இதற்கான", result.answer)
        self.assertEqual(result.source, "no_verified_match")
        self.assertEqual(groq.calls, [])

    def test_invalid_product_candidate_never_generates_card_or_action(self):
        invalid = Product("invented", "Imaginary", "", "unverified", 1, "INR", 2)
        class RejectingConnector(StubConnector):
            async def validate_product(self, product_id, variant_id, pack=None):
                return None

        connector = RejectingConnector("BIOMAN", [invalid], [])
        service = ChatService({"BIOMAN": connector}, StubGroq(), InMemorySessionStore())
        async_response = __import__("asyncio").run(service.answer(
            tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN",
            message="buy something", session_id=None,
        ))
        self.assertEqual(async_response.cards, [])
        self.assertEqual(async_response.actions, [])

    def test_tenant_session_history_isolation(self):
        sessions = InMemorySessionStore()
        session_id, _ = sessions.get_or_create("BIOMAN", "shared-id")
        sessions.append("BIOMAN", session_id, "question", "answer")
        with self.assertRaises(SessionTenantMismatch):
            sessions.get_or_create("ROCOTILE", session_id)

    def test_signed_token_cannot_be_tampered_or_switched_to_another_tenant(self):
        app = create_app(settings=settings(), connectors={
            "BIOMAN": BiomanConnector(),
            "rocotile-test": StubConnector("ROCOTILE", [], []),
        }, groq_client=StubGroq())
        client = TestClient(app)
        original = token()
        payload, signature = original.split(".")
        changed = payload[:-1] + ("A" if payload[-1] != "A" else "B") + "." + signature
        self.assertEqual(client.post("/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {changed}"}).status_code, 401)
        self.assertEqual(client.post("/chat", json={"message": "hi", "company_code": "ROCOTILE"}, headers={"Authorization": f"Bearer {original}"}).status_code, 422)

    def test_expired_and_origin_mismatched_tokens_are_rejected(self):
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()))
        expiry = int(time.time()) + 300
        expired = mint_tenant_token("BIOMAN", KEYS["BIOMAN"], expires_at=expiry)
        with self.assertRaises(TenantTokenError):
            verify_tenant_token(expired, KEYS, REGISTRY, now=expiry)
        origin_bound = token(origin="https://bioman.example")
        response = client.post("/chat", json={"message": "hello"}, headers={
            "Authorization": f"Bearer {origin_bound}", "Origin": "https://other.example",
        })
        self.assertEqual(response.status_code, 401)

    def test_local_dev_session_mints_short_lived_origin_bound_bioman_token(self):
        local_settings = replace(settings(), dev_session_enabled=True, dev_tenant_id="BIOMAN")
        client = TestClient(
            create_app(settings=local_settings, connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()),
            client=("127.0.0.1", 12345),
        )
        response = client.post("/dev/session", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["company_code"], "BIOMAN")
        self.assertEqual(body["expires_in"], 300)
        principal = verify_tenant_token(
            body["access_token"], KEYS, REGISTRY, request_origin="http://localhost:5173",
        )
        self.assertEqual(principal.tenant_id, "BIOMAN")
        self.assertEqual(principal.company_code, "BIOMAN")

    def test_local_dev_session_is_disabled_or_rejects_nonlocal_requests(self):
        disabled = TestClient(
            create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()),
            client=("127.0.0.1", 12345),
        )
        self.assertEqual(disabled.post("/dev/session", headers={"Origin": "http://localhost:5173"}).status_code, 404)

        enabled = replace(settings(), dev_session_enabled=True, dev_tenant_id="BIOMAN")
        remote = TestClient(
            create_app(settings=enabled, connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()),
            client=("203.0.113.20", 12345),
        )
        self.assertEqual(remote.post("/dev/session", headers={"Origin": "http://localhost:5173"}).status_code, 403)
        local_bad_origin = TestClient(
            create_app(settings=enabled, connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()),
            client=("127.0.0.1", 12345),
        )
        self.assertEqual(local_bad_origin.post("/dev/session", headers={"Origin": "https://evil.example"}).status_code, 403)

    def test_production_public_session_is_fixed_to_public_bioman_scope(self):
        prod_registry = {
            **REGISTRY,
            "BIOMAN": {
                "connector": "bioman", "active": True,
                "public_session_enabled": True, "public_knowledge_only": True, "public_products": True,
            },
        }
        prod_settings = replace(
            settings(), app_env="production", public_session_enabled=True,
            public_tenant_id="BIOMAN", public_origins=("https://shop.example",),
            cors_origins=("https://shop.example",), tenant_registry=prod_registry,
            dev_session_enabled=True,
        )
        client = TestClient(create_app(
            settings=prod_settings, connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq(),
            knowledge_provider=EmptyKnowledgeProvider(),
        ))
        self.assertEqual(client.post("/dev/session", headers={"Origin": "https://shop.example"}).status_code, 404)
        self.assertEqual(client.post("/public/session", headers={"Origin": "https://evil.example"}).status_code, 403)
        session = client.post("/public/session", headers={"Origin": "https://shop.example"})
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["company_code"], "BIOMAN")
        principal = verify_tenant_token(
            session.json()["access_token"], KEYS, prod_registry,
            request_origin="https://shop.example",
        )
        self.assertTrue(principal.public_only)
        chat = client.post("/chat", json={"message": "What is Bio-Culture?"}, headers={
            "Origin": "https://shop.example",
            "Authorization": f"Bearer {session.json()['access_token']}",
        })
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.json()["company_code"], "BIOMAN")

    def test_public_token_is_rejected_if_company_public_flags_are_missing(self):
        tenant_registry = {"BIOMAN": {"connector": "bioman", "active": True}}
        public_token = mint_tenant_token(
            "BIOMAN", KEYS["BIOMAN"], expires_at=int(time.time()) + 300,
            origin="https://shop.example", scope="public",
        )
        with self.assertRaises(TenantTokenError):
            verify_tenant_token(public_token, KEYS, tenant_registry, request_origin="https://shop.example")

    def test_local_cors_preflight_allows_chat_authorization_headers(self):
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=StubGroq()))
        response = client.options("/chat", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_company_context_comes_from_signed_token_and_is_returned(self):
        rocotile_connector = StubConnector("ROCOTILE", [], [KnowledgeRecord("r1", "care", "question", "Rocotile approved answer")])
        groq = StubGroq(FALLBACK_EN)
        client = TestClient(create_app(settings=settings(), connectors={
            "BIOMAN": BiomanConnector(), "rocotile-test": rocotile_connector,
        }, groq_client=groq))
        response = client.post("/chat", json={"message": "Tamil question"}, headers={"Authorization": f"Bearer {token('ROCOTILE')}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["company_code"], "ROCOTILE")
        self.assertEqual(response.json()["source"], "no_verified_match")
        self.assertEqual(groq.calls, [])

    def test_groq_conversation_is_grounded_and_history_is_bounded(self):
        groq = StubGroq("Verified answer")
        record = KnowledgeRecord("k1", "usage", "How to use", "Approved usage detail")
        connector = StubConnector("BIOMAN", [], [record])
        service = ChatService({"BIOMAN": connector}, groq, InMemorySessionStore(max_messages=4), max_history_messages=2)
        import asyncio
        with patch("chatbot.service.search_approved_knowledge", return_value=[record]):
            first = asyncio.run(service.answer(tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN", message="How to use?", session_id=None))
            asyncio.run(service.answer(tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN", message="Follow-up?", session_id=first.session_id))
        self.assertIn("Approved usage detail", groq.calls[0]["messages"][-1]["content"])
        self.assertIn("Tamil", groq.calls[0]["system"])
        self.assertEqual(len(groq.calls[1]["messages"]), 3)

    def test_invalid_groq_response_and_provider_failure_are_safe(self):
        knowledge = [KnowledgeRecord("k", "topic", "question", "approved fact")]
        with patch("chatbot.service.search_approved_knowledge", return_value=knowledge):
            for client in (StubGroq(" "), StubGroq(failure=RuntimeError("secret must not surface"))):
                service = ChatService({"BIOMAN": StubConnector("BIOMAN", [], knowledge)}, client, InMemorySessionStore())
                with self.assertRaises(ChatDependencyError):
                    asyncio.run(service.answer(tenant_id="BIOMAN", company_code="BIOMAN", connector_name="BIOMAN", message="question", session_id=None))

    def test_http_error_handling_auth_validation_and_rate_limit(self):
        client = TestClient(create_app(
            settings=settings(), connectors={"BIOMAN": BiomanConnector()},
            groq_client=StubGroq(), rate_limiter=DevelopmentRateLimiter(requests=1, window_seconds=60),
        ))
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.post("/chat", json={"message": "hello"}).status_code, 401)
        headers = {"Authorization": f"Bearer {token()}"}
        self.assertEqual(client.post("/chat", json={"message": " "}, headers=headers).status_code, 422)
        self.assertEqual(client.post("/chat", json={"message": "hello"}, headers=headers).status_code, 429)

    def test_missing_groq_configuration_only_fails_when_grounded_generation_is_needed(self):
        client = TestClient(create_app(settings=settings(), connectors={"BIOMAN": BiomanConnector()}, groq_client=None))
        record = KnowledgeRecord("k", "benefits", "pumping frequency", "Approved benefit.")
        with patch("chatbot.service.search_approved_knowledge", return_value=[record]):
            response = client.post("/chat", json={"message": "Can Bio-Culture reduce septic tank pumping frequency?"}, headers={"Authorization": f"Bearer {token()}"})
        self.assertEqual(response.status_code, 503)

    def test_generic_rest_connector_requires_https_and_filters_unapproved_knowledge(self):
        with self.assertRaises(ConnectorConfigurationError):
            GenericRestConnector("ROCOTILE", "http://catalog.local", "https://knowledge.example", "server-secret")

        def handler(request):
            if request.url.path.endswith("/knowledge"):
                return httpx.Response(200, json=[
                    {"approved": False, "record_id": "x", "topic": "topic", "question": "q", "answer": "unapproved"},
                    {"approved": True, "record_id": "y", "topic": "care", "question": "care", "answer": "approved"},
                ])
            return httpx.Response(200, json=[
                {"product_id": "good", "title": "Tile", "pack": 1, "price_amount": 12, "currency": "INR"},
                {"product_id": "nan", "title": "Bad", "pack": 1, "price_amount": "NaN", "currency": "INR"},
            ])

        connector = GenericRestConnector(
            "ROCOTILE", "https://catalog.example/products", "https://knowledge.example/knowledge",
            "server-secret", transport=httpx.MockTransport(handler),
        )
        import asyncio
        products = asyncio.run(connector.search_products("tile"))
        knowledge = asyncio.run(connector.search_knowledge("care"))
        self.assertEqual([product.product_id for product in products], ["good"])
        self.assertEqual([record.record_id for record in knowledge], ["y"])

    def test_generic_rest_public_knowledge_requires_explicit_public_flag(self):
        def handler(request):
            return httpx.Response(200, json=[
                {"approved": True, "public": False, "record_id": "private", "topic": "internal", "question": "q", "answer": "private"},
                {"approved": True, "public": True, "record_id": "public", "topic": "site", "question": "q", "answer": "public"},
            ])

        connector = GenericRestConnector(
            "ROCOTILE", "https://catalog.example/products", "https://knowledge.example/knowledge",
            "server-secret", transport=httpx.MockTransport(handler),
        )
        public = asyncio.run(connector.search_public_knowledge("q"))
        self.assertEqual([record.record_id for record in public], ["public"])

    def test_generic_rest_products_support_non_pack_variants(self):
        products = GenericRestConnector._parse_products([{
            "product_id": "tile-a", "variant_id": "blue-medium", "title": "Rocotile",
            "price_amount": 999, "currency": "INR",
        }])
        self.assertEqual(products[0].variant_id, "blue-medium")
        self.assertIsNone(products[0].pack)


if __name__ == "__main__":
    unittest.main()
