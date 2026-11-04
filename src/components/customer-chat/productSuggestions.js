import { products } from "../../data.js";

const BIOCULTURE_NAME = /\bbio\s*[- ]?\s*culture\b/i;

export function findRequestedProduct(message) {
  if (!BIOCULTURE_NAME.test(message)) return null;

  const packMatch = message.match(
    /\b(\d+)\s*(?:packets?|packs?)\s*(?:of\s*)?(?:500\s*g(?:m|ram)?s?)?\b/i,
  );
  if (!packMatch) return null;

  const requestedPack = Number(packMatch[1]);
  if (!Number.isSafeInteger(requestedPack)) return null;
  return products.find((product) => product.pack === requestedPack) ?? null;
}

export function openCatalogCheckout(candidate, onOpen) {
  const product = products.find((item) => item.pack === candidate?.pack);
  if (!product || typeof onOpen !== "function") return false;
  onOpen(product);
  return true;
}
