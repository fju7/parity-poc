"""Create Stripe products and prices for Parity Billing.

Idempotent — checks for existing products before creating.
Prints price IDs for Fred to add as Render environment variables.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python3 backend/scripts/create_billing_stripe_products.py
"""

import os
import sys

stripe_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe_key:
    print("ERROR: Set STRIPE_SECRET_KEY environment variable")
    sys.exit(1)

if not stripe_key.startswith("sk_test_"):
    print("ERROR: STRIPE_SECRET_KEY must be a test key (sk_test_*)")
    print("DO NOT run this with a live key")
    sys.exit(1)

import stripe
stripe.api_key = stripe_key

PRODUCTS = [
    {
        "name": "Parity Billing Starter",
        "description": "Multi-practice billing management — up to 10 practices",
        "price_cents": 29900,
        "interval": "month",
        "env_var": "STRIPE_PRICE_BILLING_STARTER",
        "metadata": {"tier": "starter", "practice_limit": "10"},
    },
    {
        "name": "Parity Billing Growth",
        "description": "Multi-practice billing management — up to 30 practices",
        "price_cents": 69900,
        "interval": "month",
        "env_var": "STRIPE_PRICE_BILLING_GROWTH",
        "metadata": {"tier": "growth", "practice_limit": "30"},
    },
]


def main():
    # List existing products
    existing = stripe.Product.list(limit=100)
    existing_names = {p.name: p for p in existing.data}

    print("=" * 60)
    print("Parity Billing — Stripe Product Setup (TEST MODE)")
    print("=" * 60)

    for spec in PRODUCTS:
        print(f"\n--- {spec['name']} ---")

        # Find or create product
        product = existing_names.get(spec["name"])
        if product:
            print(f"  Product exists: {product.id}")
        else:
            product = stripe.Product.create(
                name=spec["name"],
                description=spec["description"],
                metadata=spec["metadata"],
            )
            print(f"  Product created: {product.id}")

        # Check for existing price
        prices = stripe.Price.list(product=product.id, active=True, limit=10)
        matching_price = None
        for p in prices.data:
            if (p.unit_amount == spec["price_cents"]
                and p.recurring
                and p.recurring.interval == spec["interval"]):
                matching_price = p
                break

        if matching_price:
            print(f"  Price exists: {matching_price.id}")
            price_id = matching_price.id
        else:
            price = stripe.Price.create(
                product=product.id,
                unit_amount=spec["price_cents"],
                currency="usd",
                recurring={"interval": spec["interval"]},
                metadata=spec["metadata"],
            )
            print(f"  Price created: {price.id}")
            price_id = price.id

        print(f"  >> {spec['env_var']}={price_id}")

    print("\n" + "=" * 60)
    print("Add these environment variables to Render:")
    print("=" * 60)
    for spec in PRODUCTS:
        # Re-fetch to get the ID
        product = existing_names.get(spec["name"]) or stripe.Product.list(limit=100).data[0]
        prices = stripe.Price.list(product=product.id, active=True, limit=10)
        for p in prices.data:
            if p.unit_amount == spec["price_cents"]:
                print(f"  {spec['env_var']}={p.id}")
                break
    print()


if __name__ == "__main__":
    main()
