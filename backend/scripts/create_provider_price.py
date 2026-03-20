"""Create the $99/month Stripe price for Parity Provider.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python3 backend/scripts/create_provider_price.py

Prints the price ID to set as STRIPE_PRICE_PROVIDER_MONTHLY in Render.
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe.api_key:
    print("ERROR: Set STRIPE_SECRET_KEY environment variable")
    exit(1)

# Check if a Parity Provider product already exists
products = stripe.Product.list(limit=100)
provider_product = None
for p in products.data:
    if "Parity Provider" in (p.name or ""):
        provider_product = p
        print(f"Found existing product: {p.id} — {p.name}")
        break

if not provider_product:
    provider_product = stripe.Product.create(
        name="Parity Provider",
        description="Contract integrity and coding intelligence for medical practices. $99/month.",
    )
    print(f"Created product: {provider_product.id}")

# Check existing prices on this product
prices = stripe.Price.list(product=provider_product.id, active=True, limit=20)
for price in prices.data:
    amt = price.unit_amount
    interval = price.recurring.interval if price.recurring else "one-time"
    print(f"  Existing price: {price.id} — ${amt/100:.2f}/{interval}")
    if amt == 9900 and interval == "month":
        print(f"\n$99/month price already exists: {price.id}")
        print(f"Set STRIPE_PRICE_PROVIDER_MONTHLY={price.id} in Render")
        exit(0)

# Create $99/month price
price = stripe.Price.create(
    product=provider_product.id,
    unit_amount=9900,  # $99.00
    currency="usd",
    recurring={"interval": "month"},
)

print(f"\nCreated $99/month price: {price.id}")
print(f"Set STRIPE_PRICE_PROVIDER_MONTHLY={price.id} in Render")
