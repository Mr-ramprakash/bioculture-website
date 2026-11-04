import { products as catalogProducts } from "../data.js";

const configuredChatUrl = import.meta.env.VITE_CUSTOMER_CHAT_API_URL;
const configuredSessionUrl = import.meta.env.VITE_CUSTOMER_CHAT_SESSION_URL;
const isDevelopmentBuild = import.meta.env.DEV;
const TOKEN_REFRESH_SKEW_MS = 15_000;
const REQUEST_TIMEOUT_MS = 25_000;

let cachedToken = null;
let tokenExpiresAt = 0;
let tokenRequest = null;

function getChatUrl() {
  if (!configuredChatUrl) {
    throw new Error("Chat support is not configured for this website.");
  }
  try {
    return new URL(configuredChatUrl, window.location.origin);
  } catch {
    throw new Error("Chat support is not configured for this website.");
  }
}

function isLoopback(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function getSessionUrl(chatUrl) {
  if (!isDevelopmentBuild) {
    if (!configuredSessionUrl) {
      throw new Error("Chat support is not configured for this website.");
    }
    const sessionUrl = new URL(configuredSessionUrl, window.location.origin);
    if (sessionUrl.origin !== window.location.origin || sessionUrl.protocol !== "https:") {
      throw new Error("The production chat session must use this secure website origin.");
    }
    return sessionUrl;
  }
  if (!isLoopback(window.location.hostname) || !isLoopback(chatUrl.hostname)) {
    throw new Error("The local chat session is available only while running the website on this computer.");
  }
  const sessionUrl = new URL(chatUrl);
  sessionUrl.pathname = "/dev/session";
  sessionUrl.search = "";
  sessionUrl.hash = "";
  return sessionUrl;
}

async function fetchJson(url, options, timeoutMessage) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error?.name === "AbortError") throw new Error(timeoutMessage);
    throw new Error("Can't reach chat support. Please try again when the connection is available.");
  } finally {
    window.clearTimeout(timeout);
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function getChatSession(forceRefresh = false) {
  if (!forceRefresh && cachedToken && Date.now() < tokenExpiresAt - TOKEN_REFRESH_SKEW_MS) {
    return cachedToken;
  }
  if (tokenRequest) return tokenRequest;

  tokenRequest = (async () => {
    const sessionUrl = getSessionUrl(getChatUrl());
    const response = await fetchJson(
      sessionUrl,
      { method: "POST", credentials: "omit", headers: { Accept: "application/json" } },
      "The local chat session request timed out. Please try again.",
    );
    const data = await readJson(response);
    if (!response.ok) {
      if (response.status === 404 || response.status === 403) {
        throw new Error(isDevelopmentBuild
          ? "Local chat access is disabled. Check the backend development-session settings."
          : "Public chat sessions are not enabled for this website.");
      }
      if (response.status === 429) throw new Error("Chat is busy right now. Please wait a moment and try again.");
      throw new Error("Couldn't start a secure chat session. Please try again.");
    }
    if (
      !data ||
      typeof data.access_token !== "string" ||
      !data.access_token ||
      data.token_type !== "Bearer" ||
      data.company_code !== "BIOMAN" ||
      !Number.isFinite(data.expires_in) ||
      data.expires_in < 30 ||
      data.expires_in > 900
    ) {
      throw new Error("The backend returned an invalid chat session.");
    }
    cachedToken = data.access_token;
    tokenExpiresAt = Date.now() + data.expires_in * 1000;
    return cachedToken;
  })();

  try {
    return await tokenRequest;
  } finally {
    tokenRequest = null;
  }
}

function normalizeProductCard(card, actions) {
  if (!card || card.type !== "product" || typeof card.product_id !== "string") return null;
  const packMatch = /^bioculture-pack-(1|2|3|5|10)$/.exec(card.product_id);
  if (!packMatch) return null;
  const pack = Number(packMatch[1]);
  const trustedProduct = catalogProducts.find((item) => item.pack === pack);
  if (!trustedProduct || card.title !== "Bio-Culture" || card.variant !== `${pack} ${pack === 1 ? "packet" : "packets"}`) return null;
  if (card.description !== trustedProduct.description) return null;
  if (
    !card.price ||
    card.price.amount !== trustedProduct.price ||
    card.price.currency !== "INR"
  ) return null;

  const expectedVariantId = `pack-${pack}`;
  const isValidBuyAction = (action) =>
    action?.type === "buy_now" &&
    action.product_id === card.product_id &&
    action.variant_id === expectedVariantId &&
    action.pack === pack;
  if (!Array.isArray(card.buttons) || !card.buttons.some(isValidBuyAction)) return null;
  if (!Array.isArray(actions) || !actions.some(isValidBuyAction)) return null;

  return {
    pack: trustedProduct.pack,
    description: trustedProduct.description,
    price: trustedProduct.price,
    productId: card.product_id,
    variantId: expectedVariantId,
  };
}

function mapChatError(status) {
  if (status === 429) return "Chat is busy right now. Please wait a moment and try again.";
  if (status === 401) return "Your chat session expired. Please send your question again.";
  if (status === 413 || status === 422) return "Please shorten your question and try again.";
  if (status >= 500) return "AI chatbot is temporarily unavailable. Please try again later.";
  return "I couldn't send that message. Please try again.";
}

export async function sendCustomerChatMessage(message, sessionId = null) {
  const chatUrl = getChatUrl();
  const requestBody = { message };
  if (typeof sessionId === "string" && sessionId.length > 0) requestBody.session_id = sessionId;

  let token = await getChatSession();
  let response = await fetchJson(
    chatUrl,
    {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(requestBody),
    },
    "Chat support took too long to respond. Please try again.",
  );
  if (response.status === 401) {
    cachedToken = null;
    tokenExpiresAt = 0;
    token = await getChatSession(true);
    response = await fetchJson(
      chatUrl,
      {
        method: "POST",
        credentials: "omit",
        headers: { "Content-Type": "application/json", Accept: "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(requestBody),
      },
      "Chat support took too long to respond. Please try again.",
    );
  }

  const data = await readJson(response);
  if (!response.ok) throw new Error(mapChatError(response.status));
  if (
    !data ||
    typeof data.answer !== "string" ||
    !data.answer.trim() ||
    data.company_code !== "BIOMAN" ||
    typeof data.session_id !== "string"
  ) {
    throw new Error("Chat support returned an invalid response. Please try again.");
  }

  const normalizedProducts = Array.isArray(data.cards)
    ? data.cards.map((card) => normalizeProductCard(card, data.actions)).filter(Boolean)
    : [];

  return {
    answer: data.answer,
    sessionId: data.session_id,
    source: typeof data.source === "string" ? data.source : "",
    products: normalizedProducts,
  };
}
