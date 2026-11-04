import asyncio
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from chatbot.config import Settings
from chatbot.connectors.bioman import BiomanConnector
from chatbot.knowledge_store import search_approved_knowledge
from chatbot.main import create_app


class KnowledgeStoreTests(unittest.TestCase):
    def test_checked_in_bioman_records_remain_draft_and_unserved(self):
        self.assertEqual(asyncio.run(asyncio.to_thread(search_approved_knowledge, "BIOMAN", "Bio-Culture")), [])

    def test_vercel_function_explicitly_bundles_project_knowledge_files(self):
        project_root = Path(__file__).resolve().parents[2]
        config = json.loads((project_root / "vercel.json").read_text(encoding="utf-8"))
        self.assertNotIn("builds", config)
        function_config = config["functions"]["api/index.py"]
        self.assertIn("knowledge-base/**", function_config["includeFiles"])
        self.assertTrue((project_root / "api" / "index.py").is_file())
        self.assertEqual(config["rewrites"], [{
            "source": "/api/chat-api/:path*",
            "destination": "/api?__vercel_path=/api/chat-api/:path*",
        }])

    def test_vercel_rewrite_restores_health_and_protected_knowledge_paths(self):
        from vercel_entry_loader import load_root_vercel_entry

        vercel_app = load_root_vercel_entry().app

        client = TestClient(vercel_app)
        self.assertEqual(
            client.get("/api?__vercel_path=/api/chat-api/health").status_code,
            200,
        )
        protected = client.post(
            "/api?__vercel_path=/api/chat-api/internal/knowledge/search",
            json={"company_code": "BIOMAN", "tenant_id": "BIOMAN", "query": "test", "public_only": False},
        )
        self.assertEqual(protected.status_code, 401)
        self.assertEqual(
            client.get("/api?__vercel_path=/api/chat-api/not-an-endpoint").status_code,
            400,
        )

    def test_vercel_post_public_session_uses_production_origin_and_bioman_tenant(self):
        from vercel_entry_loader import load_root_vercel_entry

        VercelRewritePath = load_root_vercel_entry().VercelRewritePath

        origin = "https://bioculture-ai-chatbot.vercel.app"
        tenant = {
            "connector": "bioman",
            "active": True,
            "public_session_enabled": True,
            "public_knowledge_only": True,
            "public_products": True,
        }
        settings = Settings(
            app_env="production",
            cors_origins=(origin,),
            signing_keys={"BIOMAN": "test-only-bioman-signing-key-long-enough"},
            tenant_registry={"BIOMAN": tenant},
            public_session_enabled=True,
            public_tenant_id="BIOMAN",
            public_origins=(origin,),
        )
        fastapi_app = create_app(
            settings=settings,
            connectors={"BIOMAN": BiomanConnector()},
        )
        client = TestClient(VercelRewritePath(fastapi_app))

        response = client.post(
            "/api?__vercel_path=/api/chat-api/public/session",
            headers={"Origin": origin},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["company_code"], "BIOMAN")
        self.assertEqual(response.json()["token_type"], "Bearer")

        wrong_origin = client.post(
            "/api?__vercel_path=/api/chat-api/public/session",
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(wrong_origin.status_code, 403)

    def test_fixed_company_file_returns_only_relevant_approved_records(self):
        records = [
                {"record_id": "approved", "topic": "usage", "questions": ["How to mix Bio-Culture"], "answer": "Approved answer", "approved": True, "status": "approved", "public": True},
                {"record_id": "draft", "topic": "usage", "questions": ["How to mix Bio-Culture"], "answer": "Draft answer", "approved": False, "status": "draft", "public": True},
                {"record_id": "private", "topic": "usage", "questions": ["How to mix Bio-Culture"], "answer": "Private answer", "approved": True, "status": "approved", "public": False},
        ]
        with patch("chatbot.knowledge_store.Path.read_text", return_value=json.dumps({"company_code": "BIOMAN", "records": records})):
            public = search_approved_knowledge("BIOMAN", "How to mix Bio-Culture", public_only=True)
            internal = search_approved_knowledge("BIOMAN", "How to mix Bio-Culture")
        self.assertEqual([row.record_id for row in public], ["approved"])
        self.assertEqual({row.record_id for row in internal}, {"approved", "private"})

    def test_protected_endpoint_requires_secret_and_rejects_cross_company(self):
        signing_keys = {"BIOMAN": "bioman-test-secret-long-enough", "ROCOTILE": "rocotile-test-secret-long-enough"}
        registry = {
            "BIOMAN": {"connector": "bioman", "active": True, "company_code": "BIOMAN", "public_session_enabled": True, "public_knowledge_only": True},
            "ROCOTILE": {"connector": "knowledge", "active": False, "company_code": "ROCOTILE"},
        }
        config = Settings(signing_keys=signing_keys, tenant_registry=registry)
        client = TestClient(create_app(settings=config, connectors={"BIOMAN": BiomanConnector()}))
        payload = {"tenant_id": "BIOMAN", "company_code": "BIOMAN", "query": "Bio-Culture", "public_only": True}
        with patch.dict(os.environ, {"KNOWLEDGE_API_SHARED_SECRET": "test-only-shared-secret"}):
            self.assertEqual(client.post("/internal/knowledge/search", json=payload).status_code, 401)
            cross = {**payload, "tenant_id": "ROCOTILE"}
            response = client.post("/internal/knowledge/search", json=cross, headers={"Authorization": "Bearer test-only-shared-secret"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
