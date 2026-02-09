#!/usr/bin/env python3
"""
Taxami Premium System - Stripe Integration
Gestione pagamenti e sblocco automatico funzionalità premium
"""

import stripe
import json
import logging
from datetime import datetime, timedelta
from stripe_config import STRIPE_SECRET_KEY_TEST, PREMIUM_PRODUCT_INFO, STRIPE_ENV

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurazione Stripe
stripe.api_key = STRIPE_SECRET_KEY_TEST

# Files
PREMIUM_USERS_FILE = "taxami_premium_users.json"

class PremiumManager:
    def __init__(self):
        self.premium_users = self.load_premium_users()
    
    def load_premium_users(self):
        """Carica utenti premium"""
        try:
            with open(PREMIUM_USERS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_premium_users(self):
        """Salva utenti premium"""
        try:
            with open(PREMIUM_USERS_FILE, 'w') as f:
                json.dump(self.premium_users, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Errore salvataggio premium users: {e}")
    
    def is_premium_user(self, user_id):
        """Verifica se utente è premium e attivo"""
        user_str = str(user_id)
        if user_str not in self.premium_users:
            return False
        
        user_data = self.premium_users[user_str]
        expiry_date = datetime.fromisoformat(user_data.get('expires_at', '2000-01-01'))
        
        return datetime.now() < expiry_date
    
    def add_premium_user(self, user_id, subscription_id, duration_months=1):
        """Aggiunge utente premium"""
        user_str = str(user_id)
        expires_at = datetime.now() + timedelta(days=duration_months * 30)
        
        self.premium_users[user_str] = {
            'user_id': user_id,
            'subscription_id': subscription_id,
            'activated_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'status': 'active'
        }
        
        self.save_premium_users()
        logger.info(f"Utente {user_id} attivato premium fino al {expires_at}")
    
    def remove_premium_user(self, user_id):
        """Rimuove utente premium"""
        user_str = str(user_id)
        if user_str in self.premium_users:
            self.premium_users[user_str]['status'] = 'cancelled'
            self.save_premium_users()
            logger.info(f"Utente {user_id} premium cancellato")
    
    def get_premium_stats(self):
        """Statistiche utenti premium"""
        active_count = sum(1 for user in self.premium_users.values() 
                          if user.get('status') == 'active' and 
                          datetime.fromisoformat(user.get('expires_at', '2000-01-01')) > datetime.now())
        
        total_revenue = active_count * PREMIUM_PRODUCT_INFO['price'] / 100
        
        return {
            'active_premium_users': active_count,
            'monthly_revenue': total_revenue,
            'total_users': len(self.premium_users)
        }

class StripePaymentManager:
    def __init__(self):
        self.premium_manager = PremiumManager()
    
    def create_payment_link(self, user_id):
        """Crea link di pagamento Stripe per utente"""
        try:
            # Cerca prodotti esistenti
            products = stripe.Product.list(limit=10)
            product = None
            
            # Trova prodotto Taxami o crealo
            for p in products:
                if p.name == PREMIUM_PRODUCT_INFO['name']:
                    product = p
                    break
            
            if not product:
                product = stripe.Product.create(
                    name=PREMIUM_PRODUCT_INFO['name'],
                    description=PREMIUM_PRODUCT_INFO['description']
                )
            
            # Cerca prezzi esistenti per questo prodotto
            prices = stripe.Price.list(product=product.id, limit=10)
            price = None
            
            # Trova prezzo corrispondente o crealo
            for p in prices:
                if (p.unit_amount == PREMIUM_PRODUCT_INFO['price'] and 
                    p.currency == PREMIUM_PRODUCT_INFO['currency'] and
                    p.recurring and p.recurring.interval == PREMIUM_PRODUCT_INFO['interval']):
                    price = p
                    break
            
            if not price:
                price = stripe.Price.create(
                    unit_amount=PREMIUM_PRODUCT_INFO['price'],
                    currency=PREMIUM_PRODUCT_INFO['currency'],
                    recurring={"interval": PREMIUM_PRODUCT_INFO['interval']},
                    product=product.id
                )
            
            # Crea sessione di checkout
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price.id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f'https://t.me/Taxami_bot?start=premium_success_{user_id}',
                cancel_url=f'https://t.me/Taxami_bot?start=premium_cancel_{user_id}',
                metadata={
                    'user_id': str(user_id),
                    'product': 'taxami_premium'
                }
            )
            
            return session.url
            
        except Exception as e:
            logger.error(f"Errore creazione payment link: {e}")
            return None
    
    def handle_webhook(self, payload, sig_header):
        """Gestisce webhook Stripe per sblocco automatico"""
        try:
            # Per ora senza verifica signature (da implementare in produzione)
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                user_id = int(session['metadata']['user_id'])
                subscription_id = session.get('subscription')
                
                # Attiva utente premium
                self.premium_manager.add_premium_user(user_id, subscription_id)
                logger.info(f"Pagamento completato per user {user_id}")
                
                return True
                
            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                # Trova utente e disattiva premium
                for user_id, user_data in self.premium_manager.premium_users.items():
                    if user_data.get('subscription_id') == subscription['id']:
                        self.premium_manager.remove_premium_user(int(user_id))
                        break
                        
                return True
                
        except Exception as e:
            logger.error(f"Errore webhook: {e}")
            return False
        
        return True

# Istanza globale
payment_manager = StripePaymentManager()
premium_manager = PremiumManager()

def test_stripe_connection():
    """Test connessione Stripe"""
    try:
        balance = stripe.Balance.retrieve()
        print(f"OK - Stripe connesso - Environment: {STRIPE_ENV}")
        return True
    except Exception as e:
        print(f"ERRORE Stripe: {e}")
        return False

if __name__ == "__main__":
    # Test sistema
    print("Testing Stripe Premium System...")
    
    if test_stripe_connection():
        print("Sistema pronto per l'integrazione!")
        
        # Test stats
        stats = premium_manager.get_premium_stats()
        print(f"Stats: {stats}")
    else:
        print("Problemi di connessione Stripe")