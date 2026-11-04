"""Local Bioman knowledge seed; replace this source with an approved live connector later."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BiomanKnowledgeEntry:
    record_id: str
    topic: str
    questions: tuple[str, ...]
    answer: str


# Answers are grounded in the copied website's product catalog, usage steps,
# FAQ, support form, and visible policy pages. Policy answers explicitly note
# where the website itself does not publish a confirmed detail.
BIOMAN_KNOWLEDGE: tuple[BiomanKnowledgeEntry, ...] = (
    BiomanKnowledgeEntry(
        "product-overview", "Product information",
        (
            "What is Bio-Culture?",
            "What does Bio-Culture do in a septic tank?",
            "What kind of product is this Bio-Culture cleaner?",
            "Tell me about the Bio-Culture product.",
        ),
        "The Bioman website describes Bio-Culture as a septic-tank cleaner containing a consortium of highly enzymatic bacteria. Its FAQ says the microbes break down sludge and use it as a food source.",
    ),
    BiomanKnowledgeEntry(
        "sludge-benefits", "Product benefits",
        (
            "Can Bio-Culture help reduce septic tank sludge?",
            "Will using Bio-Culture reduce how often I pump out my septic tank?",
            "How can Bio-Culture affect sludge buildup?",
            "Does this product help with frequent septic tank pump-outs?",
            "Can Bio-Culture slow solid waste accumulation in a septic tank?",
        ),
        "The website FAQ says the microbes break down sludge and that Bio-Culture may reduce the need for frequent pump-outs. It says pump-out intervals depend on tank design, construction and volume, the number of users, and usage habits. The site mentions an average recommended interval of 2 to 3 years, but does not guarantee a result for an individual tank.",
    ),
    BiomanKnowledgeEntry(
        "chemical-cleaners", "Product care",
        (
            "Do toilet-cleaning chemicals affect septic tank microbes?",
            "Can strong toilet cleaners harm microbial activity in my tank?",
            "What does Bioman recommend about chemical toilet cleaners?",
            "Are eco-friendly cleaners better for a septic tank?",
            "I live in an apartment and cannot control everyone's cleaners; what does the FAQ say?",
        ),
        "The website FAQ says chemical toilet cleaners can contain harmful or corrosive ingredients with extreme pH and recommends eco-friendly, nature-powered cleaners to protect the septic tank. It also says Bio-Culture may help minimize damage where apartment residents cannot all switch cleaners; it does not promise that it will prevent all effects.",
    ),
    BiomanKnowledgeEntry(
        "usage-mixing", "Usage instructions",
        (
            "How do I prepare one Bio-Culture packet?",
            "How much water should I mix with each packet?",
            "Should I dissolve the packet before using it?",
            "What is the mixing instruction for Bio-Culture?",
            "How do I get the Bio-Culture mixture ready?",
        ),
        "The website instructions say to mix each packet of Bio-Culture in half a bucket of water.",
    ),
    BiomanKnowledgeEntry(
        "usage-application", "Usage instructions",
        (
            "Where should I pour the Bio-Culture mixture?",
            "After mixing it, what should I do next?",
            "Do I pour the mixture into the toilet and flush?",
            "How do I apply the prepared Bio-Culture?",
            "Can you explain the pour-and-flush steps?",
        ),
        "After mixing one packet with half a bucket of water, the website instructions say to pour the mixture into the toilet or closet and flush.",
    ),
    BiomanKnowledgeEntry(
        "packet-size", "Product size",
        (
            "How much does one Bio-Culture packet contain?",
            "What is the weight of each packet?",
            "Is each packet 500 grams?",
            "What size are the individual Bio-Culture sachets or packets?",
        ),
        "The Bioman website catalog describes each Bio-Culture packet as 500 gm.",
    ),
    BiomanKnowledgeEntry(
        "pack-options", "Product options",
        (
            "Which Bio-Culture pack sizes can I choose from?",
            "What packet quantities are available?",
            "Can I buy a 1, 2, 3, 5, or 10 packet pack?",
            "Show me the available Bio-Culture pack options.",
        ),
        "The current website catalog lists Bio-Culture packs containing 1, 2, 3, 5, or 10 packets. Each packet is listed as 500 gm. I can show the current catalog cards so you can choose a pack.",
    ),
    BiomanKnowledgeEntry(
        "price-help", "Catalog prices",
        (
            "How do I find the current Bio-Culture price?",
            "What do the different Bio-Culture packs cost?",
            "Can you show me the current pack prices?",
            "Where can I see the price for each packet quantity?",
            "How much is the Bio-Culture pack I want?",
        ),
        "The website catalog has current listed prices for each pack. Tell me the packet quantity you want, or ask to see the pack options, and I can show the matching catalog price. The catalog's separate original-price reference is not confirmed as an official MRP.",
    ),
    BiomanKnowledgeEntry(
        "offers-and-mrp", "Prices and offers",
        (
            "Is the original price shown on the website the official MRP?",
            "What is the verified MRP for Bio-Culture?",
            "Is there a discount or special offer right now?",
            "Are the crossed-out catalog amounts confirmed retail prices?",
            "Can you confirm today's promotion or savings?",
        ),
        "The website catalog provides current listed prices, but the separate original-price reference has not been verified as official MRP. I do not have verified information confirming a current promotion, discount, or offer beyond the catalog display.",
    ),
    BiomanKnowledgeEntry(
        "buying-process", "Buying and checkout",
        (
            "How can I buy Bio-Culture from this website?",
            "What do I do after choosing a packet size?",
            "Can I place an order online?",
            "Where do I enter my details to purchase a pack?",
            "How do I continue from a Buy Now button?",
        ),
        "Choose the pack you want and use its Buy Now button to open the website's existing checkout form. The form asks for customer and delivery details, then offers the existing continue-to-payment step. Please review the pack and displayed price before continuing.",
    ),
    BiomanKnowledgeEntry(
        "payment-options", "Payments",
        (
            "Which payment methods can I use?",
            "Can I pay online for my Bio-Culture order?",
            "Are card or UPI payments available?",
            "Where do I see the payment options?",
        ),
        "The website's checkout hands online payment to its payment provider, including Razorpay. The exact payment methods available for your order are the ones shown in the checkout or payment step; I cannot confirm a specific method before it is displayed.",
    ),
    BiomanKnowledgeEntry(
        "payment-problem", "Payment support",
        (
            "My payment failed; what should I do?",
            "The payment is pending or delayed—how do I check it?",
            "Money was debited but my order is not updated. Who can help?",
            "What if Razorpay does not confirm my payment?",
            "Should I retry after a declined payment?",
        ),
        "The website's terms page advises checking the transaction status with your bank or payment provider if a payment fails before trying again. If money was debited but the order status did not update, contact website support with the relevant order and transaction reference. Do not share full card details in chat.",
    ),
    BiomanKnowledgeEntry(
        "delivery-estimates", "Delivery information",
        (
            "How long will delivery take?",
            "Can you give me an exact delivery date?",
            "When will my Bio-Culture order arrive?",
            "Is there a confirmed delivery timeline?",
        ),
        "I do not have a verified delivery date or fixed timeline for your order. Please contact website support through Contact Us for an order-specific update.",
    ),
    BiomanKnowledgeEntry(
        "delivery-coverage-cost", "Delivery information",
        (
            "Do you deliver to my area or PIN code?",
            "How much are the shipping charges?",
            "Is delivery free for my location?",
            "Can you check whether my address is serviceable?",
            "Are there any delivery restrictions or extra charges?",
        ),
        "I cannot verify serviceability or delivery charges for an address from the available approved information. Please contact website support to confirm them before ordering.",
    ),
    BiomanKnowledgeEntry(
        "order-status", "Orders",
        (
            "Can you check my order status?",
            "How do I track an order I already placed?",
            "Where can I find my order confirmation?",
            "My order has not been updated; what should I do?",
            "Can you look up my existing Bio-Culture order?",
        ),
        "I cannot access live order records from this chat. Please contact the website's support team through Contact Us and include your order number and relevant details so they can check the order.",
    ),
    BiomanKnowledgeEntry(
        "cancellation-refunds", "Cancellations and refunds",
        (
            "Can I cancel an order after placing it?",
            "What is the refund eligibility and timeline?",
            "How do I request a refund for Bio-Culture?",
            "Will I get my money back if an order is cancelled?",
            "How long does a refund take to reach my account?",
        ),
        "The website's Terms page says the company should publish a clear cancellation and refund policy, including eligibility and time limits. Those details are not confirmed in the available approved information, so I cannot promise eligibility or timing. Please contact website support with your order number.",
    ),
    BiomanKnowledgeEntry(
        "returns-replacements", "Returns and replacements",
        (
            "Can I return or exchange a Bio-Culture pack?",
            "What is the replacement policy for a damaged product?",
            "Can I request a return after delivery?",
            "How do I report a missing or incorrect item?",
            "What are the return conditions and time limit?",
        ),
        "I do not have verified return, replacement, eligibility, or time-limit details. The website's Terms page says a clear policy should be published; please contact website support with your order number and explain the issue.",
    ),
    BiomanKnowledgeEntry(
        "privacy-data", "Privacy information",
        (
            "What personal information does the website say it may collect?",
            "Does the privacy page mention names and contact details?",
            "What customer data is listed in the posted Privacy Policy?",
            "Does the site collect postcode or preference information?",
            "Where can I read how my information is used?",
        ),
        "The posted Privacy Policy lists name and job title, contact information such as email, demographic details such as postcode and preferences, and information relevant to surveys or offers. The page is dated January 9, 2024; please review it directly for its full wording and current status.",
    ),
    BiomanKnowledgeEntry(
        "privacy-cookies-sharing", "Privacy information",
        (
            "Does the website use cookies?",
            "What does the privacy page say about cookies and traffic logs?",
            "Does the posted policy say my information is sold?",
            "How does the privacy page describe use of personal information?",
            "How do I ask about or correct my information?",
        ),
        "The posted Privacy Policy describes traffic-log cookies for statistical website-use analysis and says users can change browser cookie settings. It also states that personal information will not be sold, distributed, or leased without permission or a legal requirement, and lists an email contact for correction requests. Please check the policy page directly for the complete text.",
    ),
    BiomanKnowledgeEntry(
        "terms-status", "Terms and conditions",
        (
            "Where can I read the website terms and conditions?",
            "Are the posted Terms and Conditions final and approved?",
            "Which terms apply to a Bio-Culture purchase?",
            "Can you confirm the company's official order terms?",
            "Where should I ask about a term that is unclear?",
        ),
        "The website has a Terms and Conditions page, but its own notice says the company should review and approve the terms and confirm details such as shipping, support, cancellation, returns, and refunds. I cannot represent those items as confirmed policy; please contact website support for current terms.",
    ),
    BiomanKnowledgeEntry(
        "contact-complaints", "Customer support",
        (
            "How do I contact Bioman customer support?",
            "Where can I submit a complaint about my order?",
            "Can I report a delivery or installation issue?",
            "What kinds of issues can I select in the Contact Support form?",
            "Who should I contact about a product concern or bad smell?",
        ),
        "Use the website's Contact Us or Contact Support form. The form lists Bad Smell, Delivery Issue, Installation Issue, and Others as issue types. Please include the details needed to explain your concern, but avoid sharing full payment-card information in chat.",
    ),
)


QUESTION_VARIATION_COUNT = sum(len(entry.questions) for entry in BIOMAN_KNOWLEDGE)
