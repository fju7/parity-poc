"""One-shot script to create 3 Parity Employer Stripe products and prices.

Usage:
    STRIPE_SECRET_KEY=sk_test_xxx python scripts/create_employer_stripe_products.py

Outputs the 3 price IDs to set as env vars:
    STRIPE_PRICE_EMPLOYER_SMALL
    STRIPE_PRICE_EMPLOYER_MID
    STRIPE_PRICE_EMPLOYER_LARGE
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
if not stripe.api_key:
    raise SystemExit("Set STRIPE_SECRET_KEY environment variable")

PRODUCTS = [
    {
        "name": "Parity Employer Small",
        "description": "Parity Employer plan for small employers (up to 100 employees)",
        "amount": 29900,  # $299.00 in cents
        "env_var": "STRIPE_PRICE_EMPLOYER_SMALL",
    },
    {
        "name": "Parity Employer Mid-Market",
        "description": "Parity Employer plan for mid-market employers (100-1000 employees)",
        "amount": 79900,  # $799.00 in cents
        "env_var": "STRIPE_PRICE_EMPLOYER_MID",
    },
    {
        "name": "Parity Employer+",
        "description": "Parity Employer+ plan for large employers (1000+ employees)",
        "amount": 199900,  # $1,999.00 in cents
        "env_var": "STRIPE_PRICE_EMPLOYER_LARGE",
    },
]

print("Creating Parity Employer Stripe products...\n")

for p in PRODUCTS:
    product = stripe.Product.create(
        name=p["name"],
        description=p["description"],
        metadata={"platform": "civicscale", "vertical": "employer"},
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=p["amount"],
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"{p['env_var']}={price.id}")

print("\nDone. Add these to your Render environment variables.")
