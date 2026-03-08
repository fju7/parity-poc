"""Create Stripe products and prices for value-tiered employer pricing.

Three tiers based on identified annual excess spend:
  - Starter: $149/mo — under $200K annual excess
  - Growth:  $349/mo — $200K–$750K annual excess
  - Scale:   $699/mo — over $750K annual excess

Run once to create products in Stripe, then store the price IDs as env vars.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python scripts/create_stripe_tiers.py
"""

import os
import sys

def main():
    try:
        import stripe
    except ImportError:
        print("ERROR: stripe package not installed. Run: pip install stripe")
        sys.exit(1)

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        print("ERROR: STRIPE_SECRET_KEY environment variable not set")
        sys.exit(1)

    tiers = [
        {
            "name": "Parity Employer — Starter",
            "description": "Claims benchmarking for employers with under $200K identified annual excess. Includes Claims Check, RBP Calculator, Contract Parser, Scorecard, and monthly monitoring.",
            "price_cents": 14900,
            "tier_key": "starter",
        },
        {
            "name": "Parity Employer — Growth",
            "description": "Claims benchmarking for employers with $200K–$750K identified annual excess. Includes all Starter features plus priority support and quarterly trend reports.",
            "price_cents": 34900,
            "tier_key": "growth",
        },
        {
            "name": "Parity Employer — Scale",
            "description": "Claims benchmarking for employers with over $750K identified annual excess. Includes all Growth features plus dedicated account management and custom analytics.",
            "price_cents": 69900,
            "tier_key": "scale",
        },
    ]

    print("Creating Stripe products and prices...\n")

    env_lines = []
    for tier in tiers:
        # Create product
        product = stripe.Product.create(
            name=tier["name"],
            description=tier["description"],
            metadata={"tier_key": tier["tier_key"], "product_line": "employer"},
        )
        print(f"  Product: {product.name} (id: {product.id})")

        # Create monthly price
        price = stripe.Price.create(
            product=product.id,
            unit_amount=tier["price_cents"],
            currency="usd",
            recurring={"interval": "month"},
            metadata={"tier_key": tier["tier_key"]},
        )
        print(f"  Price:   ${tier['price_cents'] / 100:.0f}/mo (id: {price.id})")

        env_key = f"STRIPE_PRICE_EMPLOYER_{tier['tier_key'].upper()}"
        env_lines.append(f"{env_key}={price.id}")
        print()

    print("=" * 60)
    print("Add these to your .env / environment variables:\n")
    for line in env_lines:
        print(f"  {line}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
