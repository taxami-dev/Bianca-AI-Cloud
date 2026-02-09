# Stripe Configuration for Taxami Bot Premium
import os

# Keys from Environment Variables (SECURE)
STRIPE_SECRET_KEY_TEST = os.getenv('STRIPE_SECRET_KEY', 'sk_test_fallback')
STRIPE_PUBLISHABLE_KEY_TEST = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_fallback')

# Prodotto Premium
PREMIUM_PRODUCT_INFO = {
    "name": "Taxami Premium",
    "description": "Consulenze fiscali illimitate + funzionalità avanzate",
    "price": 999,  # €9.99 in centesimi
    "currency": "eur",
    "interval": "month"
}

# Webhook per automazione
STRIPE_WEBHOOK_SECRET = ""  # Da configurare

# Environment
STRIPE_ENV = "test"  # "test" o "live"