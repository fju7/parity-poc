"""Create Stripe products and prices for Broker Pro plan.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python3 backend/scripts/create_broker_stripe_products.py

After running, add the printed env vars to Render.
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe.api_key:
    raise SystemExit("Set STRIPE_SECRET_KEY environment variable first.")

# Broker Pro — $99/mo
broker_pro = stripe.Product.create(
    name="Parity Employer — Broker Pro",
    description="Unlimited clients, renewal prep reports, Level 2 insights, bulk onboarding",
)
broker_pro_price = stripe.Price.create(
    product=broker_pro.id,
    unit_amount=9900,
    currency="usd",
    recurring={"interval": "month"},
)
print(f"STRIPE_PRICE_BROKER_PRO={broker_pro_price.id}")
print(f"\nAdd this to Render environment variables.")
