import React, { useEffect, useState } from "react";
import { createBioCultureOrder, createSupportIssue } from "./services/api.js";
import { faqs, features, products, usageSteps } from "./data.js";
const logoUrl = "/Bioman Logo.jpeg";
const productImageUrl = "/Bioman Bio Culture Green Pouches.png";
function OfferBar() {
  return (
    <div className="offer-bar">
      {"\u{1F6D2}"} Limited-Time Offer: FREE Shipping on All Orders
    </div>
  );
}
function Hero() {
  return (
    <section className="hero">
      <div className="hero-inner">
        <div className="hero-copy">
          <img
            className="brand-logo"
            src={logoUrl}
            alt="Bioman \u2014 Say goodbye to septic tank"
          />
          <h1>
            Experience the Power of Bio-Culture for Efficient Sewage Management
            in:
          </h1>
          <ul className="hero-benefits">
            <li>Septic Systems</li>
            <li>Leach Pipes</li>
            <li>drain pipes</li>
          </ul>
          <button
            className="shop-button"
            onClick={() =>
              document
                .getElementById("products")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            SHOP NOW
          </button>
          <div className="review-line">
            <span className="stars" aria-label="4.5 out of 5 stars">
              {"\u2605\u2605\u2605\u2605\u2606"}
            </span>
            <span>4.5 out of 5 stars from 158 reviews.</span>
          </div>
        </div>
        <img
          className="hero-product"
          src={productImageUrl}
          alt="Bio-Culture packets"
        />
      </div>
    </section>
  );
}
function FeatureStrip() {
  return (
    <section className="feature-strip" aria-label="Product benefits">
      {features.map(([image, label]) => (
        <div className="feature" key={label}>
          <img src={image} alt="" />
          <p>{label}</p>
        </div>
      ))}
    </section>
  );
}
function ProductCard({ product, onBuy }) {
  return (
    <article className={`product-card pack-${product.pack}`}>
      <h2>Bio-Culture</h2>
      <p className="product-description">{product.description}</p>
      <p className="pack-label">Pack of {product.pack}</p>
      <p className="product-price">
        {"\u20B9"}
        {product.price}
      </p>
      <p className="original-price">
        {"\u20B9"}
        {product.original}
      </p>
      <p className="saving">
        Save Upto {"\u20B9"}
        {product.save}
      </p>
      <button className="buy-button" onClick={() => onBuy(product)}>
        BUY NOW
      </button>
    </article>
  );
}
function ProductGrid({ onBuy }) {
  return (
    <section className="products" id="products" aria-label="Bio-Culture packs">
      {products.map((product) => (
        <ProductCard key={product.pack} product={product} onBuy={onBuy} />
      ))}
    </section>
  );
}
function HowToUse() {
  return (
    <section className="how-section">
      <h2>How To Use</h2>
      <div className="how-box">
        {usageSteps.map(([image, text], index) => (
          <div className="how-item" key={text}>
            <img src={image} alt="" />
            <div className="how-step">
              <strong>{index + 1}.</strong>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
function ProductNote() {
  return (
    <section className="product-note">
      <p>
        Note: The product is based on natural ingredients, hence can vary in
        colour &amp; consistency. This does not affect product performance.
      </p>
      <p>
        Company's liability is limited to uniform quality of the product, as
        product usage conditions are beyond our control.
      </p>
    </section>
  );
}
function FAQ() {
  const [openIndex, setOpenIndex] = useState(0);
  return (
    <section className="faq-section">
      <h2>
        Have questions?
        <br />
        {"We\u2019ve got the answers!"}
      </h2>
      <div className="faq-box">
        {faqs.map((faq, index) => (
          <article className="faq-item" key={faq.question}>
            <button
              className="faq-question"
              aria-expanded={openIndex === index}
              onClick={() => setOpenIndex(openIndex === index ? -1 : index)}
            >
              <span>{faq.question}</span>
              <span aria-hidden="true">
                {openIndex === index ? "\u2212" : "+"}
              </span>
            </button>
            {openIndex === index && (
              <div className="faq-answer">
                {faq.answer.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
function SiteFooter({ onContact }) {
  return (
    <footer className="site-footer">
      <nav aria-label="Footer links">
        <a href="#privacy">Privacy Policy</a>
        <a href="#terms">Terms and Conditions</a>
        <a
          href="#contact"
          onClick={(event) => {
            event.preventDefault();
            onContact();
          }}
        >
          Contact us
        </a>
      </nav>
      <p>
        {"\u00A9"} 2026 Bioman Sewage Solutions Private Limited. All Rights
        Reserved
      </p>
    </footer>
  );
}
function PolicyPage({ type }) {
  const isPrivacy = type === "privacy";
  const title = isPrivacy ? "Privacy Policy" : "TERMS & CONDITIONS";

  return (
    <main className="policy-page">
      <a className="policy-back-link" href="/">
        &larr; Back to home
      </a>
      <article className="policy-content">
        <h1>{title}</h1>
        <p className="policy-updated">
          {isPrivacy
            ? "Last updated on Jan 9th 2024"
            : "Last Updated: 27 October 2026"}
        </p>
        {isPrivacy ? (
          <>
            <p>
              This privacy policy sets out how BIOMAN SEWAGE SOLUTIONS PRIVATE
              LIMITED uses and protects any information that you give BIOMAN
              SEWAGE SOLUTIONS PRIVATE LIMITED when you use this website.
            </p>
            <p>
              BIOMAN SEWAGE SOLUTIONS PRIVATE LIMITED is committed to ensuring
              that your privacy is protected. Should we ask you to provide
              certain information by which you can be identified when using this
              website, and then you can be assured that it will only be used in
              accordance with this privacy statement.
            </p>
            <p>
              BIOMAN SEWAGE SOLUTIONS PRIVATE LIMITED may change this policy
              from time to time by updating this page. You should check this
              page from time to time to ensure that you are happy with any
              changes.
            </p>
            <h2>We may collect the following information:</h2>
            <ul>
              <li>Name and job title</li>
              <li>Contact information including email address</li>
              <li>
                Demographic information such as postcode, preferences and
                interests
              </li>
              <li>
                Other information relevant to customer surveys and/or offers
              </li>
            </ul>
            <h2>What we do with the information we gather</h2>
            <p>
              We require this information to understand your needs and provide
              you with a better service, and in particular for the following
              reasons:
            </p>
            <ul>
              <li>Internal record keeping.</li>
              <li>
                We may use the information to improve our products and services.
              </li>
              <li>
                We may periodically send promotional emails about new products,
                special offers or other information which we think you may find
                interesting using the email address which you have provided.
              </li>
              <li>
                From time to time, we may also use your information to contact
                you for market research purposes. We may contact you by email,
                phone, fax or mail. We may use the information to customise the
                website according to your interests.
              </li>
            </ul>
            <p>
              We are committed to ensuring that your information is secure. In
              order to prevent unauthorised access or disclosure we have put in
              suitable measures.
            </p>
            <h2>How we use cookies</h2>
            <p>
              A cookie is a small file which asks permission to be placed on
              your computer&apos;s hard drive. Once you agree, the file is added
              and the cookie helps analyses web traffic or lets you know when
              you visit a particular site. Cookies allow web applications to
              respond to you as an individual. The web application can tailor
              its operations to your needs, likes and dislikes by gathering and
              remembering information about your preferences.
            </p>
            <p>
              We use traffic log cookies to identify which pages are being used.
              This helps us analyses data about webpage traffic and improve our
              website in order to tailor it to customer needs. We only use this
              information for statistical analysis purposes and then the data is
              removed from the system.
            </p>
            <p>
              Overall, cookies help us provide you with a better website, by
              enabling us to monitor which pages you find useful and which you
              do not. A cookie in no way gives us access to your computer or any
              information about you, other than the data you choose to share
              with us.
            </p>
            <p>
              You can choose to accept or decline cookies. Most web browsers
              automatically accept cookies, but you can usually modify your
              browser setting to decline cookies if you prefer. This may prevent
              you from taking full advantage of the website.
            </p>
            <h2>Controlling your personal information</h2>
            <p>
              You may choose to restrict the collection or use of your personal
              information in the following ways:
            </p>
            <ul>
              <li>
                whenever you are asked to fill in a form on the website, look
                for the box that you can click to indicate that you do not want
                the information to be used by anybody for direct marketing
                purposes
              </li>
              <li>
                if you have previously agreed to us using your personal
                information for direct marketing purposes, you may change your
                mind at any time by writing to or emailing us at{" "}
                <a href="mailto:customercare@bioman.co.in">
                  customercare@bioman.co.in
                </a>
              </li>
            </ul>
            <p>
              We will not sell, distribute or lease your personal information to
              third parties unless we have your permission or are required by
              law to do so. We may use your personal information to send you
              promotional information about third parties which we think you may
              find interesting if you tell us that you wish this to happen.
            </p>
            <p>
              If you believe that any information we are holding on you is
              incorrect or incomplete, please write to or email us as soon as
              possible, at the above address. We will promptly correct any
              information found to be incorrect.
            </p>
          </>
        ) : (
          <>
            <h2>1. Introduction</h2>
            <p>
              These Terms and Conditions govern your access to and use of the
              Bio-Culture website and the purchase of products offered through
              it.
            </p>
            <p>
              In these Terms and Conditions,{" "}
              <strong>“Company,” “we,” “us,” and “our”</strong> refer to{" "}
              <strong>BIOMAN SEWAGE SOLUTIONS PRIVATE LIMITED</strong>, having
              its registered or operational office at:
            </p>
            <p>
              265/1, Agragaram Main Road, Ayanambakkam, Chennai, Tamil Nadu –
              600095, India.
            </p>
            <p>
              The terms <strong>“you,” “your,” “customer,” and “user”</strong>{" "}
              refer to any individual or legal entity accessing our website or
              purchasing products through it.
            </p>
            <p>
              By accessing our website or placing an order, you acknowledge that
              you have read and understood these Terms and Conditions.
            </p>

            <h2>2. Website Information</h2>
            <p>
              We make reasonable efforts to ensure that the information
              published on our website is accurate and up to date. However,
              product descriptions, prices, offers, images, and other
              information may occasionally contain errors or omissions.
            </p>
            <p>
              We reserve the right to correct errors, update information, modify
              website content, or discontinue offers without prior notice,
              subject to applicable law.
            </p>
            <p>
              Product images are provided for illustrative purposes. Actual
              product packaging, colour, or appearance may vary slightly.
            </p>

            <h2>3. Products and Intended Use</h2>
            <p>
              Our Bio-Culture products are intended to be used in accordance
              with the instructions provided on the product packaging or
              website.
            </p>
            <p>
              Customers are responsible for reading and following the
              recommended usage instructions. Product performance may vary
              depending on septic tank conditions, tank size, usage patterns,
              maintenance practices, and other environmental factors.
            </p>
            <p>
              We do not guarantee specific results where outcomes depend on
              conditions beyond our reasonable control.
            </p>

            <h2>4. Pricing and Payment</h2>
            <p>
              All product prices displayed on our website are stated in Indian
              Rupees (INR), unless otherwise specified.
            </p>
            <p>
              Prices, discounts, and promotional offers may change from time to
              time. The applicable price for an order will be the price
              displayed at checkout when the order is placed, subject to
              correction of any genuine pricing error and applicable law.
            </p>
            <p>
              Payments must be completed through the payment methods made
              available on our website. Online payments may be processed by
              third-party payment service providers, including Razorpay.
            </p>
            <p>
              We do not store or directly process your complete card details
              when payment processing is handled by a third-party payment
              provider. Such transactions are subject to the applicable
              provider&apos;s terms and policies.
            </p>
            <p>
              An order is not considered paid until the payment is successfully
              confirmed.
            </p>

            <h2>5. Order Confirmation and Acceptance</h2>
            <p>
              Submitting an order does not automatically guarantee its
              acceptance or fulfilment.
            </p>
            <p>
              Orders are subject to payment confirmation, product availability,
              and verification where reasonably necessary.
            </p>
            <p>
              We reserve the right to cancel or decline an order where permitted
              by law, including in cases of suspected fraud, incorrect pricing,
              or product unavailability. Where payment has already been
              collected for an order that is cancelled, the amount paid will be
              refunded in accordance with applicable law and our applicable
              refund process.
            </p>
            <p>
              Customers should provide accurate contact and delivery information
              when placing an order.
            </p>

            <h2>6. Shipping and Delivery</h2>
            <p>
              We aim to process and deliver orders within the estimated delivery
              period communicated to the customer.
            </p>
            <p>
              Delivery timelines are estimates and may be affected by courier
              availability, weather, transport disruptions, incorrect addresses,
              or other circumstances beyond our reasonable control.
            </p>
            <p>
              Customers are responsible for providing a complete and accurate
              delivery address, contact number, and other required information.
            </p>
            <p>
              Any shipping charges, delivery restrictions, or applicable
              delivery conditions will be communicated during checkout or
              through the relevant order information.
            </p>

            <h2>7. Cancellation, Returns, and Refunds</h2>
            <p>
              Cancellation, return, replacement, and refund requests will be
              handled in accordance with our applicable policies and consumer
              protection laws.
            </p>
            <p>
              Customers should contact our support team with their order details
              and the reason for the request.
            </p>
            <p>
              If an eligible refund is approved, it will be processed through
              the original payment method or another appropriate method, as
              applicable. The time taken for the refund to appear in the
              customer&apos;s account may depend on the payment provider or
              banking institution.
            </p>
            <p>
              <strong>
                The Company should publish a clear cancellation, return, and
                refund policy before accepting customer orders.
              </strong>{" "}
              Any applicable eligibility conditions, time limits, and exceptions
              should be stated in that policy.
            </p>

            <h2>8. Customer Responsibilities</h2>
            <p>When using our website, you agree to:</p>
            <ul>
              <li>
                Provide accurate and complete information when placing orders or
                submitting enquiries.
              </li>
              <li>Use our products according to the instructions provided.</li>
              <li>
                Avoid using the website for unlawful, fraudulent, or
                unauthorised purposes.
              </li>
              <li>
                Avoid attempting to disrupt, damage, or gain unauthorised access
                to our website or systems.
              </li>
              <li>
                Respect the Company&apos;s intellectual property rights and
                those of third parties.
              </li>
            </ul>
            <p>
              We may take appropriate action where website use violates these
              Terms and Conditions or applicable law.
            </p>

            <h2>9. Intellectual Property</h2>
            <p>
              Unless otherwise stated, the content on this website, including
              text, product descriptions, graphics, logos, images, design
              elements, and other materials, is owned by or licensed to BIOMAN
              SEWAGE SOLUTIONS PRIVATE LIMITED.
            </p>
            <p>
              You may not reproduce, distribute, modify, republish, or
              commercially exploit this content without prior written
              permission, except where permitted by applicable law.
            </p>
            <p>
              All third-party trademarks and logos appearing on the website
              remain the property of their respective owners.
            </p>

            <h2>10. Third-Party Websites and Services</h2>
            <p>
              Our website may contain links to third-party websites or use
              third-party services, including payment processing services.
            </p>
            <p>
              These third parties operate under their own terms, conditions, and
              privacy policies. We are not responsible for the content,
              security, or practices of external websites to the extent
              permitted by applicable law.
            </p>
            <p>
              Customers should review the relevant third-party terms and
              policies before using those services.
            </p>

            <h2>11. Limitation of Liability</h2>
            <p>
              To the extent permitted by applicable law, the Company shall not
              be liable for losses arising from temporary website
              unavailability, technical interruptions, or circumstances beyond
              its reasonable control.
            </p>
            <p>
              Nothing in these Terms and Conditions excludes or limits any
              liability that cannot legally be excluded or limited under
              applicable law, including any rights or remedies available to
              consumers.
            </p>
            <p>
              The Company does not guarantee uninterrupted website access or
              that the website will always be free from technical errors.
            </p>

            <h2>12. Payment Transaction Issues</h2>
            <p>
              Payment transactions may occasionally be declined, delayed, or
              interrupted because of payment provider restrictions, banking
              issues, technical failures, or other reasons.
            </p>
            <p>
              Where a payment is declined or fails, customers should check the
              transaction status with their bank or payment provider before
              attempting another payment.
            </p>
            <p>
              If an amount has been debited but the order or payment status is
              not updated, customers should contact our support team and provide
              the relevant transaction details. We will investigate the matter
              and take appropriate action in accordance with applicable law and
              the payment provider&apos;s procedures.
            </p>

            <h2>13. Privacy and Personal Information</h2>
            <p>
              Personal information collected through our website will be handled
              in accordance with our Privacy Policy and applicable data
              protection laws.
            </p>
            <p>
              Customers should review our Privacy Policy to understand how their
              personal information is collected, used, stored, and shared.
            </p>
            <p>
              <strong>Privacy Policy:</strong> A separate Privacy Policy should
              be published and linked from the website before this section is
              finalised.
            </p>

            <h2>14. Changes to These Terms</h2>
            <p>
              We may revise these Terms and Conditions from time to time to
              reflect changes in our business practices, products, website
              features, or legal obligations.
            </p>
            <p>
              The revised version will be published on this page with an updated
              revision date. Changes will apply in accordance with applicable
              law.
            </p>
            <p>Customers are encouraged to review this page periodically.</p>

            <h2>15. Governing Law and Dispute Resolution</h2>
            <p>
              These Terms and Conditions shall be governed by the laws of India.
            </p>
            <p>
              Disputes arising from the use of our website or purchases made
              through it shall be handled in accordance with applicable Indian
              law. Nothing in these Terms and Conditions limits any consumer
              rights or remedies available under applicable law.
            </p>

            <h2>16. Contact Information</h2>
            <p>
              For questions about these Terms and Conditions, orders, payments,
              or product-related concerns, please contact our support team
              through the <strong>Contact Us</strong> section of our website.
            </p>
            <p>
              <strong>Company:</strong> BIOMAN SEWAGE SOLUTIONS PRIVATE LIMITED
              <br />
              <strong>Address:</strong> 265/1, Agragaram Main Road,
              Ayanambakkam, Chennai, Tamil Nadu – 600095, India.
            </p>
            <p>
              Please include your order number and relevant details when
              contacting us about an existing order.
            </p>
            <hr />
            <p>
              <strong>Important Notice:</strong> These Terms and Conditions
              should be reviewed and approved by the Company before publication.
              The Company should also confirm its official registered address,
              customer support contact details, shipping commitments, and
              cancellation, return, and refund policies.
            </p>
          </>
        )}
        {isPrivacy && (
          <p className="policy-disclaimer">
            Disclaimer: The above content is created at BIOMAN SEWAGE SOLUTIONS
            PRIVATE LIMITED&apos;s sole discretion. Razorpay shall not be liable
            for any content provided here and shall not be responsible for any
            claims and liability that may arise due to merchant’s non-adherence
            to it.
          </p>
        )}
      </article>
    </main>
  );
}
function FormField({
  name,
  placeholder,
  value,
  onChange,
  type = "text",
  required = true,
  wide = false,
}) {
  return (
    <input
      className={`form-field${wide ? " wide" : ""}`}
      name={name}
      placeholder={placeholder}
      aria-label={placeholder.replace(/\s*\*$/, "")}
      type={type}
      value={value}
      required={required}
      onChange={onChange}
    />
  );
}
function CheckoutModal({ product, onClose }) {
  const [form, setForm] = useState({
    customer_name: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
  });
  const [submitting, setSubmitting] = useState(false);
  function update(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }
  async function continueToPay(event) {
    event.preventDefault();
    const values = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim()]),
    );
    if (
      !values.customer_name ||
      !values.phone ||
      !values.address ||
      !values.city ||
      !values.pincode
    ) {
      alert("Please fill all required fields");
      return;
    }
    if (submitting) return;
    setSubmitting(true);
    try {
      const data = await createBioCultureOrder({
        ...values,
        pack: product.pack,
        amount: product.price,
      });
      if (data.message) {
        const result = data.message;

        if (result.payment_link) {
          alert(
            "Order created successfully!\nRedirecting to Razorpay payment...",
          );
          onClose();
          window.location.href = result.payment_link;
          return;
        }

        if (result.sales_order) {
          alert(
            `Sales Order Created : ${result.sales_order}\n\nPayment link could not be generated.`,
          );
          onClose();
        }
      }
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="checkout-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Checkout"
      >
        <div className="checkout-steps">
          <div className="step active">
            <span>1</span>
            <div>
              Account<small>Your Details</small>
            </div>
          </div>
          <div className="step">
            <span>2</span>
            <div>
              Checkout<small>Payment details</small>
            </div>
          </div>
        </div>
        <form className="checkout-form" onSubmit={continueToPay}>
          <button
            className="close-button"
            type="button"
            aria-label="Close checkout"
            onClick={onClose}
          >
            {"\u00D7"}
          </button>
          <h3>Your Details</h3>
          <div className="form-grid">
            <FormField
              name="customer_name"
              placeholder="Full Name *"
              value={form.customer_name}
              onChange={update}
              wide
            />
            <FormField
              name="phone"
              placeholder="Phone Number *"
              type="tel"
              value={form.phone}
              onChange={update}
              wide
            />
            <h3 className="address-heading">Shipping Address</h3>
            <FormField
              name="address"
              placeholder="Address *"
              value={form.address}
              onChange={update}
              wide
            />
            <FormField
              name="city"
              placeholder="City *"
              value={form.city}
              onChange={update}
            />
            <FormField
              name="pincode"
              placeholder="Pincode *"
              value={form.pincode}
              onChange={update}
            />
            <FormField
              name="state"
              placeholder="State"
              value={form.state}
              onChange={update}
              required={false}
              wide
            />
          </div>
          <div className="checkout-actions">
            <button
              className="continue-button"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Please wait\u2026" : "Continue To Pay"}
            </button>
            <p>by clicking you accept the terms and conditions</p>
          </div>
          <p className="privacy-note">
            We Respect Your Privacy &amp; Information
          </p>
        </form>
      </section>
    </div>
  );
}
function SupportModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    customer_name: "",
    customer_number: "",
    subject: "",
    issue_type: "",
  });
  const [submitting, setSubmitting] = useState(false);
  function update(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }
  async function submitIssue(event) {
    event.preventDefault();
    if (!/^[A-Za-z ]+$/.test(form.customer_name)) {
      alert(
        "Customer Name should contain only alphabets and spaces.\nNumbers and special characters are not allowed.",
      );
      return;
    }
    if (
      !form.customer_name ||
      !form.customer_number ||
      !form.subject ||
      !form.issue_type
    ) {
      alert("Please fill all fields");
      return;
    }
    if (submitting) return;
    setSubmitting(true);
    try {
      const data = await createSupportIssue(form);
      if (data.message) {
        onClose();
        onSuccess(
          `Your issue has been submitted successfully. Issue ID: ${data.message.issue}. Our support team will contact you shortly and resolve the issue at the earliest.`,
        );
      } else {
        alert("Issue creation failed");
      }
    } catch (error) {
      console.error(error);
      alert(`API Error : ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="support-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Contact Support"
      >
        <form className="support-form" onSubmit={submitIssue}>
          <button
            className="close-button"
            type="button"
            aria-label="Close support form"
            onClick={onClose}
          >
            {"\u00D7"}
          </button>
          <h3>Contact Support</h3>
          <FormField
            name="customer_name"
            placeholder="Customer Name"
            value={form.customer_name}
            onChange={update}
          />
          <FormField
            name="customer_number"
            placeholder="Customer Number"
            value={form.customer_number}
            onChange={update}
          />
          <FormField
            name="subject"
            placeholder="Subject"
            value={form.subject}
            onChange={update}
          />
          <select
            className="form-field"
            name="issue_type"
            aria-label="Issue type"
            value={form.issue_type}
            onChange={update}
            required
          >
            <option value="">Select Issue Type</option>
            <option value="Bad Smell">Bad Smell</option>
            <option value="Delivery Issue">Delivery Issue</option>
            <option value="Installation Issue">Installation Issue</option>
            <option value="Others">Others</option>
          </select>
          <button
            className="continue-button"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Please wait\u2026" : "Submit"}
          </button>
        </form>
      </section>
    </div>
  );
}
function SuccessDialog({ message, onClose }) {
  return (
    <div className="modal-backdrop success-backdrop">
      <section className="success-dialog" role="alertdialog" aria-modal="true">
        <div className="success-icon">{"\u2705"}</div>
        <p>{message}</p>
        <button className="continue-button" onClick={onClose}>
          OK
        </button>
      </section>
    </div>
  );
}
export default function App() {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showSupport, setShowSupport] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [policyPage, setPolicyPage] = useState(() =>
    window.location.hash.slice(1),
  );

  useEffect(() => {
    const updatePolicyPage = () => setPolicyPage(window.location.hash.slice(1));
    window.addEventListener("hashchange", updatePolicyPage);
    return () => window.removeEventListener("hashchange", updatePolicyPage);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [policyPage]);

  const isModalOpen = Boolean(selectedProduct || showSupport || successMessage);
  useEffect(() => {
    if (!isModalOpen) return;

    const body = document.body;
    const scrollY = window.scrollY;
    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;
    const originalStyles = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
      paddingRight: body.style.paddingRight,
    };

    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      const paddingRight = Number.parseFloat(
        window.getComputedStyle(body).paddingRight,
      );
      body.style.paddingRight = `${paddingRight + scrollbarWidth}px`;
    }

    return () => {
      body.style.position = originalStyles.position;
      body.style.top = originalStyles.top;
      body.style.left = originalStyles.left;
      body.style.right = originalStyles.right;
      body.style.width = originalStyles.width;
      body.style.overflow = originalStyles.overflow;
      body.style.paddingRight = originalStyles.paddingRight;
      window.scrollTo(0, scrollY);
    };
  }, [isModalOpen]);

  if (policyPage === "privacy" || policyPage === "terms") {
    return <PolicyPage type={policyPage} />;
  }

  return (
    <>
      <OfferBar />
      <Hero />
      <FeatureStrip />
      <ProductGrid onBuy={setSelectedProduct} />
      <HowToUse />
      <ProductNote />
      <FAQ />
      <SiteFooter onContact={() => setShowSupport(true)} />
      {selectedProduct && (
        <CheckoutModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}
      {showSupport && (
        <SupportModal
          onClose={() => setShowSupport(false)}
          onSuccess={setSuccessMessage}
        />
      )}
      {successMessage && (
        <SuccessDialog
          message={successMessage}
          onClose={() => setSuccessMessage("")}
        />
      )}
    </>
  );
}
