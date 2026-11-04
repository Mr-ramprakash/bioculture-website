import assert from "node:assert/strict";
import test from "node:test";
import { products } from "../../data.js";
import { findRequestedProduct, openCatalogCheckout } from "./productSuggestions.js";

test("two 500 gm Bio-Culture pack request resolves to the catalog product and price", () => {
  const product = findRequestedProduct("I want to buy Bio-Culture 2 packets of 500 gm");
  assert.equal(product, products.find((item) => item.pack === 2));
  assert.equal(product.description, "2 packets of 500 gm");
  assert.equal(product.price, 1649);
});

test("unsupported packs and questions without a catalog pack do not create product offers", () => {
  assert.equal(findRequestedProduct("Buy Bio-Culture 99 packets of 500 gm"), null);
  assert.equal(findRequestedProduct("What is Bio-Culture?"), null);
});

test("chat checkout callback receives the canonical catalog product, not caller price", () => {
  const selected = [];
  const untrustedCandidate = { pack: 2, price: 1, description: "wrong" };
  assert.equal(openCatalogCheckout(untrustedCandidate, (product) => selected.push(product)), true);
  assert.equal(selected[0], products.find((item) => item.pack === 2));
  assert.equal(selected[0].price, 1649);
});

test("invalid product candidates cannot open checkout", () => {
  let called = false;
  assert.equal(openCatalogCheckout({ pack: 99 }, () => { called = true; }), false);
  assert.equal(called, false);
});
