from typing import List

COMPANY_POLICY = """
[Company Policy Document]
- All refund requests must be submitted within 30 days of purchase.
- Subscription cancellations take effect at the end of the current billing cycle.
- Account closure requests are processed within 5-7 business days.
- Compensation requests require escalation to a senior support manager.
- ABC Technologies provides 99.9% uptime SLA for all cloud services.
- Data is retained for 90 days after account closure as per our data retention policy.
- Customers may request a full data export before closing their account.
- Support tickets are acknowledged within 2 hours and resolved within 24-48 hours.
"""

PRICING_GUIDE = """
[Pricing Guide]
Starter Plan   : $29/month — Up to 5 users, 10 GB storage, email support
Professional   : $79/month — Up to 25 users, 100 GB storage, priority support, API access
Business       : $199/month — Up to 100 users, 500 GB storage, dedicated manager, SLA guarantee
Enterprise     : Custom pricing — Unlimited users, unlimited storage, on-premise option, 24/7 phone support
Annual Discount: 20% off all plans when billed annually
Free Trial     : 14-day free trial available for Starter and Professional plans
Add-ons        : Additional storage $5/10 GB/month; extra user seats $8/user/month
"""

TECHNICAL_MANUAL = """
[Technical Manual]
Common Issues and Solutions:
1. Application Crash on File Upload:
   - Check file size limit: maximum 100 MB per file (500 MB on Business/Enterprise)
   - Supported formats: PDF, DOCX, XLSX, PNG, JPG, CSV
   - Clear browser cache and cookies, then retry
   - Disable browser extensions that may interfere with uploads
   - Check browser console for JavaScript errors and report to technical support

2. Login Issues / Password Reset:
   - Use the "Forgot Password" link on the login page
   - Password reset email is sent within 2 minutes; check spam folder
   - Passwords must be 8+ characters with at least one uppercase, one number, one symbol
   - After 5 failed attempts, account is locked for 15 minutes

3. Installation Issues:
   - Minimum requirements: Windows 10 / macOS 11 / Ubuntu 20.04
   - RAM: 4 GB minimum, 8 GB recommended
   - Run installer as Administrator (Windows) or with sudo (Linux/macOS)
   - Disable antivirus temporarily during installation if blocked

4. Configuration Issues:
   - API keys can be regenerated from Settings > API > Regenerate Key
   - Webhook URLs must use HTTPS
   - SMTP configuration: use port 587 with TLS

5. Error Codes:
   - ERR_001: Authentication failure — reset password
   - ERR_002: Network timeout — check internet connection
   - ERR_003: File format not supported
   - ERR_500: Server error — contact technical support
"""

FAQ_DOCUMENT = """
[FAQ Document]
Q: How do I upgrade or downgrade my subscription plan?
A: Go to Settings > Billing > Change Plan. Changes take effect immediately; billing is prorated.

Q: Can I export my data?
A: Yes. Go to Settings > Data > Export. Full export is available in CSV and JSON formats.

Q: Is there a mobile app?
A: Yes. ABC Technologies is available on iOS (App Store) and Android (Google Play Store).

Q: How do I add team members?
A: Go to Settings > Team > Invite Member. Enter their email address and assign a role.

Q: What payment methods are accepted?
A: Visa, Mastercard, American Express, PayPal, and bank transfers for Enterprise plans.

Q: How is my data secured?
A: All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We are SOC 2 Type II certified.

Q: What is the cancellation policy?
A: You can cancel anytime. Access continues until the end of the current billing period. No partial refunds.

Q: How do I contact support?
A: Email support@abctech.com, call 1-800-ABC-TECH (Mon-Fri 9AM-6PM EST), or use the in-app chat.
"""

DOCUMENT_CHUNKS = []

for doc_name, doc_text in [
    ("Company Policy", COMPANY_POLICY),
    ("Pricing Guide", PRICING_GUIDE),
    ("Technical Manual", TECHNICAL_MANUAL),
    ("FAQ", FAQ_DOCUMENT),
]:
    paragraphs = [p.strip() for p in doc_text.strip().split("\n") if p.strip()]
    for para in paragraphs:
        if len(para) > 30:
            DOCUMENT_CHUNKS.append((doc_name, para))

INTENT_KEYWORDS = {
    "sales":     ["pricing", "plan", "cost", "price", "subscribe", "subscription",
                  "feature", "trial", "upgrade", "downgrade", "discount", "monthly", "annual"],
    "technical": ["crash", "error", "bug", "fix", "install", "login", "password",
                  "upload", "configuration", "not working", "broken", "slow", "err_"],
    "billing":   ["refund", "invoice", "payment", "charge", "cancel", "billing",
                  "receipt", "overcharge", "money back", "compensation"],
    "account":   ["account", "profile", "reset", "activate", "deactivate", "close",
                  "delete", "update", "username", "email change"],
}


def retrieve_context(query: str, top_k: int = 5) -> str:
    query_lower = query.lower()
    query_words = set(query_lower.split())
    scored_chunks: List[tuple] = []

    for source, chunk in DOCUMENT_CHUNKS:
        chunk_lower = chunk.lower()
        score = 0
        chunk_words = set(chunk_lower.split())
        overlap = len(query_words & chunk_words)
        score += overlap * 2

        for keyword in query_words:
            if keyword in chunk_lower:
                score += 1

        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                if any(kw in chunk_lower for kw in keywords):
                    score += 3

        if score > 0:
            scored_chunks.append((score, source, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:top_k]

    if not top_chunks:
        return "No specific documentation found for this query."

    return "\n\n".join(f"[{source}] {chunk}" for score, source, chunk in top_chunks)