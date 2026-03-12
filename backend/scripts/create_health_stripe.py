"""Create Stripe products and prices for Parity Health.

Run once with: STRIPE_SECRET_KEY=sk_test_... python3 backend/scripts/create_health_stripe.py

Outputs price IDs to add as Render env vars:
  STRIPE_PRICE_HEALTH_MONTHLY
  STRIPE_PRICE_HEALTH_YEARLY
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
if not stripe.api_key:
    print("ERROR: Set STRIPE_SECRET_KEY environment variable first.")
    exit(1)

# Create or find the Parity Health product
products = stripe.Product.list(limit=100)
health_product = None
for p in products.data:
    if p.name == "Parity Health":
        health_product = p
        break

if not health_product:
    health_product = stripe.Product.create(
        name="Parity Health",
        description="AI-powered medical bill analysis for consumers",
    )
    print(f"Created product: {health_product.id}")
else:
    print(f"Found existing product: {health_product.id}")

# Create monthly price: $9.95/mo
monthly_price = stripe.Price.create(
    product=health_product.id,
    unit_amount=995,  # $9.95 in cents
    currency="usd",
    recurring={"interval": "month"},
    metadata={"plan": "health_monthly"},
)
print(f"\nSTRIPE_PRICE_HEALTH_MONTHLY={monthly_price.id}")

# Create yearly price: $29/yr
yearly_price = stripe.Price.create(
    product=health_product.id,
    unit_amount=2900,  # $29.00 in cents
    currency="usd",
    recurring={"interval": "year"},
    metadata={"plan": "health_yearly"},
)
print(f"STRIPE_PRICE_HEALTH_YEARLY={yearly_price.id}")

print("\n--- Add these two env vars to Render ---")
print(f"STRIPE_PRICE_HEALTH_MONTHLY = {monthly_price.id}")
print(f"STRIPE_PRICE_HEALTH_YEARLY  = {yearly_price.id}")
