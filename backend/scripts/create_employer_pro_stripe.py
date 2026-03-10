import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

product = stripe.Product.create(
    name="Parity Employer Pro",
    description="Full access to claims analysis, benchmarking, plan grading, and Level 2 analytics. Introductory price locked for 24 months.",
)

price = stripe.Price.create(
    product=product.id,
    unit_amount=9900,  # $99.00
    currency="usd",
    recurring={"interval": "month"},
)

print(f"STRIPE_PRICE_EMPLOYER_PRO={price.id}")
print(f"Product ID: {product.id}")
