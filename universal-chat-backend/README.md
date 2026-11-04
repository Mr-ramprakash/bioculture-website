# AutomateGenie Universal Chat Backend

FastAPI service for the existing multi-company shopping/support chat API. The
Vercel deployment keeps Groq credentials server-side and retrieves approved
company knowledge through an API Gateway endpoint protected by HMAC. API
Gateway invokes the existing knowledge Lambda, which fetches approved,
company-scoped JSON from the protected Vercel backend. No S3, Bedrock, RDS, or
duplicate ERP DB is used by this chatbot migration.

## Endpoints and identity

- `GET /health` is a liveness check and makes no upstream calls.
- `POST /chat` accepts `{"message":"..."}` and optional `session_id`. The
  legacy `answer` field remains. Responses also include `company_code`, `source`,
  `session_id`, and optional structured `cards` and `actions`.
- Requests require `Authorization: Bearer <signed-tenant-token>`. A company code
  or company ID in the body is rejected. The token is HMAC-SHA256 signed with a
  tenant-specific key, expires within 15 minutes, and is verified against the
  server-side tenant registry. The server-minting helper is
  `chatbot.auth.mint_tenant_token`; call it only from a trusted site server.
  Never expose signing keys in a browser bundle. CORS/Origin checks alone are
  not authentication.

The React site never receives a signing key. For local development only, an
opt-in `POST /dev/session` endpoint can issue a five-minute token for the
server-configured tenant. It accepts only loopback clients and an allowlisted
loopback HTTP origin, is rate-limited, and is disabled by default. It returns
404 in production. A production deployment can explicitly enable
`POST /public/session`, which always selects `CHAT_PUBLIC_TENANT_ID`, requires
an exact allowlisted HTTPS origin, and mints a five-minute origin-bound token
with `public` scope. The tenant registry must separately set
`public_session_enabled`, `public_knowledge_only`, and `public_products` to
true. Public-scope chat uses only a connector's public knowledge method; the
generic REST connector additionally requires `approved: true` and `public: true`
on each record. The public bootstrap is off by default.

## Catalog and knowledge

`BiomanConnector` copies the approved current catalog values from the website:
pack identifiers 1, 2, 3, 5, and 10; current prices ₹895, ₹1,649, ₹2,449,
₹3,900, and ₹7,605. The source `original` values are deliberately omitted and
are not treated as verified MRP. Product answers/cards are created from the
connector and do not invoke Groq. Product identifiers such as
`bioculture-pack-2` are connector-local stable IDs; the existing site's actual
checkout selection continues to use `pack=2` through its own catalog callback.
This backend does not submit checkout or payment requests.

The existing Bioman seed is kept in `chatbot/connectors/bioman_knowledge.py` as
grouped answers with 100 searchable customer-question variations. The
`../knowledge-base/export_bioman.py` script exports all 21 entries as draft,
unapproved JSON. The standalone EC2 Knowledge API serves only approved public
records. `knowledge_store.search_approved_knowledge` remains the local matcher;
development can read local JSON, while production FastAPI calls EC2 with the
server-only `KNOWLEDGE_SERVICE_URL`, `KNOWLEDGE_SERVICE_KEY_ID`, and
`KNOWLEDGE_SERVICE_HMAC_SECRET` settings. Production does not fall back to a
local knowledge file.
It covers product information, benefits, usage, buying, payment, delivery,
orders, support, privacy, and terms. Policy answers identify details that the
website does not confirm; the Terms page itself says some policy details need
company review. The EC2 service selects the best matching approved JSON entry,
and Groq rewrites that approved context as a natural reply. Product
cards and prices continue to come from the validated connector catalog. When
there is no knowledge match, the service returns a fallback without asking
Groq to guess. A generic REST connector remains available for authorized
  catalog APIs. For knowledge, the Lambda maps the verified tenant company to
  that company's fixed knowledge-file scope in the Vercel backend.

Groq cannot be guaranteed never to hallucinate. The implementation avoids model
generation for price/product-card requests and instructs it to use only approved
knowledge for other replies. Review output quality and add stricter structured
validation before production use.

## Local setup

Requires Python 3.11 or newer.

```powershell
cd universal-chat-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env` to a Groq API key and `GROQ_MODEL_ID` to a model
currently available to the intended Groq account. This project intentionally
does not guess or default a model ID. Also replace the Bioman signing-key
placeholder with a random secret and configure the site server that will mint
short-lived signed tokens. Keep `.env` private and out of version control.

Start locally:

```powershell
uvicorn chatbot.main:app --reload
```

For the local React Vite site, set `CHAT_DEV_SESSION_ENABLED=true`,
`CHAT_DEV_TENANT_ID=BIOMAN`, and add the exact Vite origin (usually
`http://localhost:5173`) to `CORS_ORIGINS`. The browser bootstrap keeps the
short-lived access token in memory only; the signing key and Groq key remain in
the backend `.env`.

Run tests (they use mocked Groq/company APIs and make no external requests):

```powershell
python -m unittest discover -s tests -v
```

## Configuration

See `.env.example`. `GROQ_API_KEY` and `GROQ_MODEL_ID` are required for grounded
knowledge replies. The model ID must be selected after checking the current
Groq account/model availability. `CHAT_TENANT_SIGNING_KEYS_JSON` and
`CHAT_TENANT_REGISTRY_JSON` map each tenant to its connector and signing key.
For a REST tenant, registry fields are `connector: "rest"`, optional unique
`connector_key`, `company_code`, `catalog_url`, `knowledge_url`, and
`api_token_env` (the name of a backend environment variable holding its API
token). Each URL must be HTTPS.

For Vercel, the Python entry point is `api/index.py` and the root
`vercel.json` routes same-origin `/chat-api/*` paths to FastAPI. Copy the public
chat URL paths from `../.env.production.example`; keep `GROQ_API_KEY`, tenant
signing keys, and the three `KNOWLEDGE_SERVICE_*` settings in server-only
environment variables. `KNOWLEDGE_API_SHARED_SECRET` is separate and only
protects the retained internal Vercel knowledge route. See `.env.vercel.example`
and `../knowledge-service/EC2_DEPLOYMENT.md`.

Vercel uses a stateless session adapter, so process memory is not relied on for
conversation history; follow-up context and short product follow-ups do not
persist between invocations. The existing process-local rate limiter is not a
global production control. A shared Redis-compatible rate-limit store must be
configured before production traffic; this project does not provision one.
The knowledge client signs each POST using HMAC-SHA256 over the configured
timestamp/method/path and exact serialized body bytes. API Gateway currently
accepts timestamps within 60 seconds; without nonce tracking, captured requests
may be replayed within that interval. Do not put HMAC secrets in Vite variables.

The generic REST connector expects the catalog search URL to return a JSON
array with `product_id`, `variant_id`, `title`, `price_amount`, and `currency`;
`description` and Bioman-style integer `pack` are optional. The same catalog
URL plus `/{product_id}` must return the individual validated product. The
knowledge URL returns a JSON array with `approved: true`, `record_id`, `topic`,
`question`, and `answer`; optional `language` defaults to English. Adapt the
connector for company APIs that do not use these shapes rather than loosening
validation or trusting an LLM response.

Create a local test token (do not paste it into a public frontend):

```powershell
python -m scripts.mint_dev_token BIOMAN --origin http://localhost:5173
```

The website's trusted server should mint production tokens with
`origin=https://<exact-site-origin>` and an expiry no more than 15 minutes in
the future. Signing keys must stay on that server and this backend.

`CORS_ORIGINS` is a comma-separated exact-origin allowlist. It is a browser
policy, not authentication. The included rate limiter and conversation store
are process-local for development/single-worker use; replace them with a
distributed limiter and shared TTL session store for multi-worker production.
Configure HTTPS termination, secret rotation, monitoring, and upstream API
permissions in the chosen hosting environment.

## Response shape

```json
{
  "answer": "Bio-Culture, 2 packets of 500 gm, is currently listed at INR 1649.",
  "company_code": "BIOMAN",
  "source": "authorized_product_catalog",
  "session_id": "opaque-id",
  "cards": [
    {
      "type": "product",
      "product_id": "bioculture-pack-2",
      "title": "Bio-Culture",
      "variant": "2 packets",
      "description": "2 packets of 500 gm",
      "price": {"amount": 1649, "currency": "INR", "label": "current"},
      "buttons": [{"type": "buy_now", "label": "Buy Now", "product_id": "bioculture-pack-2", "variant_id": "pack-2", "pack": 2}]
    }
  ],
  "actions": [{"type": "buy_now", "label": "Buy Now", "product_id": "bioculture-pack-2", "variant_id": "pack-2", "pack": 2}]
}
```
