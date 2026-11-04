import React, { useEffect, useRef, useState } from "react";
import { sendCustomerChatMessage } from "../../services/customerChatApi.js";
import "./customer-chat.css";

const WELCOME_MESSAGE =
  "Hi! Ask me about Bio-Culture products, usage, or delivery. I can help in English or Tamil.";

export default function CustomerChatWidget({ onBuyProduct }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, role: "assistant", text: WELCOME_MESSAGE },
  ]);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const sessionIdRef = useRef(null);

  useEffect(() => {
    if (open) {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      inputRef.current?.focus();
    }
  }, [open, messages, loading]);

  async function submitMessage(event) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((current) => [...current, { id: Date.now(), role: "user", text: question }]);
    setLoading(true);
    try {
      const result = await sendCustomerChatMessage(question, sessionIdRef.current);
      sessionIdRef.current = result.sessionId;
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: "assistant", text: result.answer, products: result.products },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: error.message || "Chat support is temporarily unavailable. Please try again shortly.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="customer-chat-widget">
      {open && (
        <section className="customer-chat-panel" aria-label="Bioman support chat">
          <header className="customer-chat-header">
            <div>
              <strong>Bioman Support</strong>
              <span>Product information</span>
            </div>
            <button
              className="customer-chat-close"
              type="button"
              aria-label="Close chat"
              onClick={() => setOpen(false)}
            >
              {"\u00D7"}
            </button>
          </header>
          <div className="customer-chat-messages" ref={listRef} aria-live="polite">
            {messages.map((message) => (
              <React.Fragment key={message.id}>
                <p
                  className={`customer-chat-message customer-chat-${message.role}${message.error ? " customer-chat-error" : ""}`}
                >
                  {message.text}
                </p>
                {message.products?.map((product) => (
                  <article className="customer-chat-product-card" key={product.productId}>
                    <strong>Bio-Culture</strong>
                    <span>{product.description}</span>
                    <b>
                      {"\u20B9"}
                      {product.price.toLocaleString("en-IN")}
                    </b>
                    <button
                      type="button"
                      onClick={() => onBuyProduct?.(product)}
                    >
                      Buy Now
                    </button>
                  </article>
                ))}
              </React.Fragment>
            ))}
            {loading && (
              <p className="customer-chat-message customer-chat-assistant" role="status">
                Looking that up{"\u2026"}
              </p>
            )}
          </div>
          <form className="customer-chat-form" onSubmit={submitMessage}>
            <label className="customer-chat-sr-only" htmlFor="customer-chat-input">
              Your question
            </label>
            <input
              id="customer-chat-input"
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={`Type your question${"\u2026"}`}
              maxLength={2000}
              disabled={loading}
              autoComplete="off"
            />
            <button type="submit" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className="customer-chat-launcher"
        type="button"
        aria-expanded={open}
        aria-label={open ? "Close Bioman support chat" : "Open Bioman support chat"}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">{open ? "\u00D7" : "?"}</span>
        <span className="customer-chat-launcher-label">{open ? "Close" : "Ask Bioman"}</span>
      </button>
    </div>
  );
}
