#!/usr/bin/env python3
"""
Taxami Bot - Premium con Robust Error Handling
Versione migliorata con gestione crash avanzata
"""

import json
import logging
import requests
import time
import os
import traceback
import sys
from datetime import datetime, date, timedelta
from openai import OpenAI
from premium_system import payment_manager, premium_manager

# Configurazione
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('taxami_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global error counter for circuit breaker
error_count = 0
MAX_ERRORS_BEFORE_PAUSE = 10
ERROR_RESET_TIME = 300  # 5 minutes

# Setup OpenAI with retry
def initialize_openai_client():
    """Initialize OpenAI client with error handling"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # Test connection
        client.models.list()
        logger.info("OpenAI client inizializzato correttamente")
        return client
    except Exception as e:
        logger.error(f"Errore inizializzazione OpenAI: {e}")
        return None

client = initialize_openai_client()
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Marco admin ID
ADMIN_USER_ID = 1606066237

# Files con error handling
LEADS_FILE = "taxami_leads.json"
ANALYTICS_FILE = "taxami_analytics.json"
USER_LIMITS_FILE = "taxami_user_limits.json"
ERROR_LOG_FILE = "taxami_errors.json"
FISCAL_KB_PATH = "./skills/eutekne/knowledge"

# Freemium limits
FREE_QUESTIONS_PER_DAY = 3

# Domande fiscali GRATUITE (Strategia Freemium)
DOMANDE_FREE = {
    "1": {
        "titolo": "🆕 Come aprire partita IVA",
        "keywords": ["aprire", "partita", "iva", "nuova", "iniziare", "attivare"],
        "categoria": "base",
        "prompt": "Spiega come aprire partita IVA in Italia nel 2026: documenti necessari, costi, tempistiche e primi passi. Fornisci una guida pratica step-by-step."
    },
    "2": {
        "titolo": "💰 Regime Forfettario vs Ordinario",
        "keywords": ["forfettario", "ordinario", "regime", "conviene", "confronto"],
        "categoria": "base",
        "prompt": "Confronta regime forfettario e ordinario nel 2026: vantaggi, svantaggi, limiti di ricavo, tassazione. Quale conviene scegliere?"
    },
    "3": {
        "titolo": "📋 Detrazioni fiscali 2026",
        "keywords": ["detrazioni", "deducibili", "spese", "recupero", "rimborso"],
        "categoria": "base",
        "prompt": "Elenca le principali detrazioni fiscali 2026 per persone fisiche: spese sanitarie, istruzione, ristrutturazioni, bonus. Include percentuali e limiti."
    },
    "4": {
        "titolo": "🏢 SRL vs Ditta Individuale",
        "keywords": ["srl", "ditta", "individuale", "società", "responsabilità", "limitata"],
        "categoria": "base",
        "prompt": "Confronta SRL e Ditta Individuale: vantaggi fiscali, responsabilità, costi gestione, tassazione. Quando conviene una forma o l'altra?"
    },
    "5": {
        "titolo": "📅 Scadenze fiscali 2026",
        "keywords": ["scadenze", "calendario", "fiscal", "quando", "pagare", "dichiarazione"],
        "categoria": "base",
        "prompt": "Calendario delle principali scadenze fiscali 2026: dichiarazioni, versamenti, comunicazioni obbligatorie. Date e adempimenti."
    },
    "6": {
        "titolo": "🤝 Società di persone - SNC/SAS",
        "keywords": ["snc", "sas", "società", "persone", "accomandita", "collettiva"],
        "categoria": "base", 
        "prompt": "Caratteristiche delle società di persone (SNC/SAS): costituzione, tassazione, responsabilità soci, gestione. Pro e contro."
    },
    "7": {
        "titolo": "ℹ️ Informazioni e Contatti",
        "keywords": ["contatti", "informazioni", "chi", "siamo", "telefono", "email"],
        "categoria": "info",
        "prompt": "Mostra le informazioni di contatto dello Studio Di Sabato e Partners e i servizi offerti."
    }
}

# Domande PREMIUM (€9.99/mese)
DOMANDE_PREMIUM = {
    "101": {
        "titolo": "⚖️ Decreto Legislativo 231/2001 - Compliance",
        "keywords": ["231", "compliance", "responsabilità", "amministrativa", "decreto", "controllo"],
        "categoria": "avanzata",
        "prompt": "Analizza adempimenti D.Lgs 231/2001: modello organizzativo, sistema controllo, responsabilità amministrativa enti. Come implementare compliance efficace?"
    },
    "102": {
        "titolo": "🔍 Controlli fiscali e verifiche",
        "keywords": ["controlli", "verifiche", "guardia", "finanza", "accertamento", "difesa"],
        "categoria": "avanzata", 
        "prompt": "Gestione controlli fiscali 2026: diritti del contribuente, strategie difensive, documentazione richiesta, tempi e modalità verifiche."
    },
    "103": {
        "titolo": "🏗️ Operazioni straordinarie - M&A",
        "keywords": ["fusioni", "acquisizioni", "ma", "operazioni", "straordinarie", "conferimenti"],
        "categoria": "avanzata",
        "prompt": "Aspetti fiscali delle operazioni straordinarie: fusioni, scissioni, conferimenti, trasformazioni. Regimi fiscali agevolati e adempimenti."
    },
    "104": {
        "titolo": "📈 ISA - Indici Sintetici Affidabilità",
        "keywords": ["isa", "indici", "sintetici", "affidabilità", "studi", "settore"],
        "categoria": "avanzata",
        "prompt": "Sistema ISA 2026: funzionamento, calcolo affidabilità fiscale, strategie ottimizzazione, vantaggi compliance e controlli preventivi."
    },
    "105": {
        "titolo": "🌍 Transfer Pricing - Fiscalità Internazionale",
        "keywords": ["transfer", "pricing", "prezzi", "trasferimento", "internazionale", "multinazionali"],
        "categoria": "avanzata",
        "prompt": "Transfer pricing e fiscalità internazionale: documentazione, metodologie OCSE, controlli automatici, strategie compliance multinazionali."
    },
    "106": {
        "titolo": "🔍 Due Diligence Fiscali M&A",
        "keywords": ["due", "diligence", "fiscale", "acquisizioni", "rischi", "analisi"],
        "categoria": "avanzata",
        "prompt": "Due diligence fiscale per M&A: checklist verifiche, analisi rischi tributari, strategie mitigazione, documentazione acquisizioni."
    },
    "107": {
        "titolo": "💼 Crisi d'Impresa e Concordati",
        "keywords": ["crisi", "impresa", "concordato", "ristrutturazione", "procedure", "insolvenza"],
        "categoria": "avanzata",
        "prompt": "Gestione fiscale crisi d'impresa: concordato preventivo, accordi ristrutturazione, aspetti tributari procedure insolvenza."
    },
    "108": {
        "titolo": "🛡️ GDPR e Compliance Privacy",
        "keywords": ["gdpr", "privacy", "compliance", "dati", "personali", "sanzioni"],
        "categoria": "avanzata",
        "prompt": "GDPR e compliance privacy aziendale: adeguamenti normativi, registro trattamenti, analisi impatto, strategie protezione dati."
    }
}

# Robust utility functions
def safe_file_operation(file_path, operation, default_value=None, retries=3):
    """Esegue operazioni su file in modo sicuro con retry"""
    for attempt in range(retries):
        try:
            if operation == 'read':
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    return default_value if default_value is not None else {}
            
            elif operation == 'write':
                data = default_value  # In questo caso default_value è il data da scrivere
                # Backup del file esistente
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.backup"
                    try:
                        with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                            dst.write(src.read())
                    except Exception:
                        pass  # Ignora errori backup
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
                
        except Exception as e:
            logger.warning(f"Tentativo {attempt + 1}/{retries} fallito per {file_path}: {e}")
            if attempt == retries - 1:
                logger.error(f"Operazione {operation} fallita dopo {retries} tentativi su {file_path}: {e}")
                return default_value if operation == 'read' else False
            time.sleep(0.5)  # Breve pausa tra i retry
    return False

def log_error(error_type, error_message, context=None):
    """Log degli errori in file separato per analisi"""
    try:
        errors = safe_file_operation(ERROR_LOG_FILE, 'read', [])
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": str(error_message),
            "context": context,
            "traceback": traceback.format_exc() if sys.exc_info()[0] else None
        }
        errors.append(error_entry)
        
        # Mantieni solo gli ultimi 100 errori
        if len(errors) > 100:
            errors = errors[-100:]
            
        safe_file_operation(ERROR_LOG_FILE, 'write', errors)
    except Exception as e:
        logger.error(f"Impossibile loggare errore: {e}")

def circuit_breaker_check():
    """Circuit breaker pattern per prevenire cascade failures"""
    global error_count, ERROR_RESET_TIME
    current_time = time.time()
    
    # Reset error count dopo timeout
    if hasattr(circuit_breaker_check, 'last_reset'):
        if current_time - circuit_breaker_check.last_reset > ERROR_RESET_TIME:
            error_count = 0
            circuit_breaker_check.last_reset = current_time
    else:
        circuit_breaker_check.last_reset = current_time
    
    if error_count >= MAX_ERRORS_BEFORE_PAUSE:
        logger.warning(f"Circuit breaker attivato: troppi errori ({error_count}). Pausa 30 secondi...")
        time.sleep(30)
        error_count = 0
        return False
    return True

def robust_api_call(func, *args, max_retries=3, **kwargs):
    """Wrapper per chiamate API con retry e error handling"""
    global error_count
    
    for attempt in range(max_retries):
        try:
            if not circuit_breaker_check():
                continue
                
            result = func(*args, **kwargs)
            error_count = max(0, error_count - 1)  # Decrementa su successo
            return result
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout su {func.__name__}, tentativo {attempt + 1}/{max_retries}")
            time.sleep(2 ** attempt)  # Exponential backoff
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Errore connessione su {func.__name__}: {e}")
            time.sleep(5)
            
        except Exception as e:
            error_count += 1
            log_error(f"API_CALL_{func.__name__}", str(e), {"attempt": attempt + 1})
            logger.error(f"Errore {func.__name__} (tentativo {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                return None
            time.sleep(1)
    
    return None

# API Telegram robuste
def send_message_robust(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Invio messaggi robusto con fallback"""
    def _send():
        data = {
            "chat_id": chat_id,
            "text": text[:4096],  # Truncate se troppo lungo
            "parse_mode": parse_mode
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        response = requests.post(f"{BASE_URL}/sendMessage", data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    # Prova prima con Markdown
    result = robust_api_call(_send)
    
    # Fallback senza Markdown se fallisce
    if not result and parse_mode == "Markdown":
        logger.warning(f"Markdown fallito per chat {chat_id}, retry senza formatting")
        def _send_plain():
            data = {
                "chat_id": chat_id,
                "text": text[:4096],
                "parse_mode": None
            }
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            
            response = requests.post(f"{BASE_URL}/sendMessage", data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        
        result = robust_api_call(_send_plain)
    
    return result

def get_updates_robust(offset=None):
    """Get updates robusto"""
    def _get_updates():
        params = {"timeout": 10, "limit": 100}
        if offset:
            params["offset"] = offset
            
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    
    return robust_api_call(_get_updates)

def answer_callback_robust(callback_query_id):
    """Answer callback query robusto"""
    def _answer():
        data = {"callback_query_id": callback_query_id}
        response = requests.post(f"{BASE_URL}/answerCallbackQuery", data=data, timeout=5)
        response.raise_for_status()
        return response.json()
    
    return robust_api_call(_answer)

# OpenAI robusto
def generate_ai_response_robust(prompt, is_premium=False, max_tokens=400):
    """Genera risposta AI con fallback models"""
    if not client:
        return "⚠️ Servizio AI temporaneamente non disponibile. Riprova tra qualche minuto."
    
    # Model selection basato su premium status
    primary_model = "gpt-4" if is_premium else "gpt-3.5-turbo"
    fallback_model = "gpt-3.5-turbo" if primary_model == "gpt-4" else "gpt-3.5-turbo"
    
    def _generate(model):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.6,
            timeout=30
        )
        return response.choices[0].message.content
    
    # Prova primary model
    result = robust_api_call(_generate, primary_model)
    
    # Fallback se primary fallisce
    if not result and primary_model != fallback_model:
        logger.warning(f"Fallback da {primary_model} a {fallback_model}")
        result = robust_api_call(_generate, fallback_model)
    
    # Ultima risorsa: messaggio di fallback
    if not result:
        return "⚠️ Servizio AI temporaneamente sovraccarico. Riprova tra qualche minuto o contatta il supporto."
    
    return result

# Business logic functions (stessa logica, ma più robuste)
def save_lead_robust(user):
    """Salva lead in modo robusto"""
    try:
        leads = safe_file_operation(LEADS_FILE, 'read', [])
        
        user_id = str(user.get('id'))
        existing_lead = next((l for l in leads if l.get('id') == user_id), None)
        
        if not existing_lead:
            lead = {
                "id": user_id,
                "username": user.get('username', ''),
                "first_name": user.get('first_name', ''),
                "last_name": user.get('last_name', ''),
                "timestamp": datetime.now().isoformat(),
                "interactions": 1
            }
            leads.append(lead)
        else:
            existing_lead['interactions'] = existing_lead.get('interactions', 0) + 1
            existing_lead['last_interaction'] = datetime.now().isoformat()
        
        safe_file_operation(LEADS_FILE, 'write', leads)
        logger.info(f"Lead salvato: {user.get('first_name')} ({user_id})")
        
    except Exception as e:
        log_error("SAVE_LEAD", str(e), {"user": user})

def check_user_limits_robust(user_id):
    """Controllo limiti utente robusto"""
    try:
        limits = safe_file_operation(USER_LIMITS_FILE, 'read', {})
        today = date.today().isoformat()
        user_data = limits.get(str(user_id), {})
        return user_data.get(today, 0)
    except Exception as e:
        log_error("CHECK_USER_LIMITS", str(e), {"user_id": user_id})
        return 0  # Fallback sicuro

def increment_user_usage_robust(user_id):
    """Incrementa usage utente in modo robusto"""
    try:
        limits = safe_file_operation(USER_LIMITS_FILE, 'read', {})
        today = date.today().isoformat()
        user_key = str(user_id)
        
        if user_key not in limits:
            limits[user_key] = {}
        
        limits[user_key][today] = limits[user_key].get(today, 0) + 1
        
        # Cleanup vecchie date (oltre 7 giorni)
        cutoff_date = (date.today() - timedelta(days=7)).isoformat()
        for user in limits.values():
            old_dates = [d for d in user.keys() if d < cutoff_date]
            for old_date in old_dates:
                del user[old_date]
        
        safe_file_operation(USER_LIMITS_FILE, 'write', limits)
        
    except Exception as e:
        log_error("INCREMENT_USER_USAGE", str(e), {"user_id": user_id})

def load_fiscal_knowledge_robust():
    """Carica knowledge base in modo robusto"""
    try:
        if not os.path.exists(FISCAL_KB_PATH):
            logger.warning("Database fiscale non trovato")
            return {}
        
        knowledge = {}
        for filename in os.listdir(FISCAL_KB_PATH):
            if filename.endswith('.json'):
                file_path = os.path.join(FISCAL_KB_PATH, filename)
                data = safe_file_operation(file_path, 'read', [])
                if data:
                    knowledge[filename.replace('.json', '')] = data
        
        return knowledge
    except Exception as e:
        log_error("LOAD_FISCAL_KNOWLEDGE", str(e))
        return {}

def search_fiscal_content_robust(query, knowledge):
    """Ricerca contenuti fiscali robusta"""
    try:
        if not knowledge:
            return ""
        
        query_words = query.lower().split()
        relevant_content = []
        
        for section, articles in knowledge.items():
            for article in articles[:3]:  # Limita per performance
                title = article.get('title', '').lower()
                if any(word in title for word in query_words):
                    relevant_content.append(f"• {article.get('title', 'N/A')}")
        
        return "\n".join(relevant_content[:5]) if relevant_content else ""
    except Exception as e:
        log_error("SEARCH_FISCAL_CONTENT", str(e), {"query": query})
        return ""

# Menu creation (stesso codice ma con error handling)
def create_main_menu_robust(is_premium=False):
    """Crea menu principale in modo robusto"""
    try:
        keyboard = {"inline_keyboard": []}
        
        # Domande gratuite
        for q_id, question in DOMANDE_FREE.items():
            keyboard["inline_keyboard"].append([{
                "text": f"{q_id}. {question['titolo']}",
                "callback_data": f"question_{q_id}"
            }])
        
        # Domande premium
        if is_premium:
            keyboard["inline_keyboard"].append([{
                "text": "--- 💎 SEZIONE PREMIUM ---",
                "callback_data": "noop"
            }])
            
            for q_id, question in DOMANDE_PREMIUM.items():
                keyboard["inline_keyboard"].append([{
                    "text": f"{q_id}. {question['titolo']} 💎",
                    "callback_data": f"question_{q_id}"
                }])
        
        # Bottoni finali
        if not is_premium:
            keyboard["inline_keyboard"].append([
                {"text": "💎 UPGRADE PREMIUM", "callback_data": "premium"},
                {"text": "ℹ️ Contatti", "callback_data": "contacts"}
            ])
        else:
            keyboard["inline_keyboard"].append([
                {"text": "👑 STATUS PREMIUM", "callback_data": "premium_status"},
                {"text": "ℹ️ Contatti", "callback_data": "contacts"}
            ])
        
        return keyboard
        
    except Exception as e:
        log_error("CREATE_MAIN_MENU", str(e), {"is_premium": is_premium})
        # Fallback menu minimale
        return {
            "inline_keyboard": [
                [{"text": "ℹ️ Contatti", "callback_data": "contacts"}],
                [{"text": "🔄 Riprova", "callback_data": "main_menu"}]
            ]
        }

# Handler functions robuste
def handle_start_robust(chat_id, user):
    """Gestisce /start in modo robusto"""
    try:
        save_lead_robust(user)
        
        user_id = user.get('id')
        is_premium = premium_manager.is_premium_user(user_id) if premium_manager else False
        
        if is_premium:
            welcome_text = f"""👑 **Benvenuto su TAXAMI PREMIUM!** 

Ciao {user.get('first_name', 'utente')}, hai accesso completo a tutte le funzionalità premium!

💎 **PREMIUM ATTIVO:**
• Consulenze fiscali illimitate
• Domande specialistiche avanzate  
• Database normativo sempre aggiornato
• Risposte approfondite senza limiti

Scegli una domanda dal menu o scrivi liberamente!

👇 **SELEZIONA UNA DOMANDA:**"""
        else:
            usage_today = check_user_limits_robust(user_id)
            remaining = max(0, FREE_QUESTIONS_PER_DAY - usage_today)
            
            welcome_text = f"""🏛️ **Benvenuto su TAXAMI SMART!** 

Ciao {user.get('first_name', 'utente')}, sono il tuo assistente fiscale intelligente con database normativo sempre aggiornato!

🆓 **VERSIONE GRATUITA:**
• 7 domande fiscali essenziali  
• Risposte AI con fonti autorevoli
• {remaining} domande rimaste oggi

💎 **UPGRADE PREMIUM:**
• Consulenze illimitate + 8 domande specialistiche avanzate

Scegli una domanda dal menu o scrivi liberamente!

👇 **SELEZIONA UNA DOMANDA:**"""
        
        send_message_robust(chat_id, welcome_text, create_main_menu_robust(is_premium))
        
    except Exception as e:
        log_error("HANDLE_START", str(e), {"chat_id": chat_id, "user": user})
        send_message_robust(
            chat_id, 
            "🏛️ **Benvenuto su TAXAMI!**\n\nSto avendo un piccolo problema tecnico. Riprova tra qualche secondo!",
            {"inline_keyboard": [[{"text": "🔄 Riprova", "callback_data": "start_retry"}]]}
        )

def handle_callback_robust(callback_data, chat_id, message_id, user):
    """Gestisce callback in modo robusto"""
    try:
        # Answer callback sempre
        answer_callback_robust(callback_data.get("id"))
        
        data = callback_data.get("data")
        user_id = user.get('id')
        is_premium = premium_manager.is_premium_user(user_id) if premium_manager else False
        
        if data == "start_retry":
            handle_start_robust(chat_id, user)
            return
        
        if data == "main_menu":
            send_message_robust(
                chat_id,
                f"🏛️ **MENU PRINCIPALE**\n\nScegli una domanda o scrivi liberamente!",
                create_main_menu_robust(is_premium)
            )
            return
        
        if data.startswith("question_"):
            question_id = data.split("_")[1]
            
            # Check premium required
            if question_id in DOMANDE_PREMIUM and not is_premium:
                if payment_manager:
                    payment_link = payment_manager.create_payment_link(user_id)
                    upgrade_text = f"""💎 **FUNZIONALITÀ PREMIUM RICHIESTA**

Questa domanda è disponibile solo nella versione Premium.

🚀 **TAXAMI PREMIUM - €9.99/mese:**
• Consulenze fiscali illimitate
• 8 domande specialistiche avanzate
• Database normativo completo

👇 **ATTIVA SUBITO:**
[💳 PAGA CON STRIPE]({payment_link})"""
                else:
                    upgrade_text = "💎 **FUNZIONALITÀ PREMIUM RICHIESTA**\n\nServizio premium temporaneamente non disponibile."
                
                send_message_robust(
                    chat_id, 
                    upgrade_text,
                    {"inline_keyboard": [[{"text": "📋 Menu Principale", "callback_data": "main_menu"}]]}
                )
                return
            
            # Check limits per utenti free
            if not is_premium:
                usage_today = check_user_limits_robust(user_id)
                if usage_today >= FREE_QUESTIONS_PER_DAY:
                    send_message_robust(
                        chat_id,
                        f"⏰ **Limite raggiunto!**\n\nHai esaurito le {FREE_QUESTIONS_PER_DAY} domande gratuite oggi.",
                        {"inline_keyboard": [
                            [{"text": "💎 Upgrade Premium", "callback_data": "premium"}],
                            [{"text": "📋 Menu Principale", "callback_data": "main_menu"}]
                        ]}
                    )
                    return
            
            # Process question
            all_questions = {**DOMANDE_FREE, **DOMANDE_PREMIUM}
            question = all_questions.get(question_id)
            
            if question:
                if not is_premium and question_id in DOMANDE_FREE:
                    increment_user_usage_robust(user_id)
                
                # Load knowledge and generate response
                knowledge = load_fiscal_knowledge_robust()
                fiscal_context = search_fiscal_content_robust(question['prompt'], knowledge)
                
                enhanced_prompt = f"{question['prompt']}\n\nContesto normativo:\n{fiscal_context}" if fiscal_context else question['prompt']
                
                ai_response = generate_ai_response_robust(
                    enhanced_prompt, 
                    is_premium,
                    600 if is_premium else 400
                )
                
                # Footer
                if is_premium:
                    footer = "\n\n👑 Premium: Domande illimitate attive"
                else:
                    remaining = max(0, FREE_QUESTIONS_PER_DAY - check_user_limits_robust(user_id))
                    footer = f"\n\n🆓 Ti rimangono {remaining} domande gratuite oggi"
                    if remaining <= 1:
                        footer += "\n💎 Upgrade Premium per domande illimitate!"
                
                # Contatti
                contacts = "\n\n📞 **Studio Di Sabato e Partners**\n🏢 Borgomanero (NO) | ☎️ 0322.340513 | 📱 338.457.2198"
                
                final_response = ai_response + footer + contacts
                
                send_message_robust(
                    chat_id, 
                    final_response,
                    {"inline_keyboard": [[{"text": "📋 Menu Domande", "callback_data": "main_menu"}]]}
                )
            else:
                send_message_robust(
                    chat_id,
                    "❌ Domanda non trovata. Torna al menu principale.",
                    {"inline_keyboard": [[{"text": "📋 Menu Principale", "callback_data": "main_menu"}]]}
                )
        
        elif data == "contacts":
            contacts_text = """📞 **STUDIO DI SABATO E PARTNERS**

👨‍💼 **Commercialisti e Revisori Contabili**
📍 **Sede:** Borgomanero (NO)
☎️ **Telefono:** 0322.340513
📱 **Mobile:** 338.457.2198

💼 **Servizi:**
• Consulenza fiscale e tributaria
• Tenuta contabilità
• Costituzione società  
• Assistenza controlli fiscali
• Pianificazione fiscale

🤖 **Bot sviluppato da Marco Di Sabato**
Partner dello Studio specializzato in innovazione digitale"""

            send_message_robust(
                chat_id,
                contacts_text,
                {"inline_keyboard": [[{"text": "📋 Menu Principale", "callback_data": "main_menu"}]]}
            )
        
        # Altri callback handlers...
        
    except Exception as e:
        log_error("HANDLE_CALLBACK", str(e), {
            "callback_data": callback_data, 
            "chat_id": chat_id, 
            "user": user
        })
        send_message_robust(
            chat_id,
            "⚠️ Si è verificato un errore. Riprova dal menu principale.",
            {"inline_keyboard": [[{"text": "📋 Menu Principale", "callback_data": "main_menu"}]]}
        )

def handle_text_robust(chat_id, text, user):
    """Gestisce messaggi di testo in modo robusto"""
    try:
        # Stats admin
        if text.startswith("/stats") and user.get("id") == ADMIN_USER_ID:
            try:
                leads = safe_file_operation(LEADS_FILE, 'read', [])
                premium_stats = premium_manager.get_premium_stats() if premium_manager else {
                    "active_premium_users": 0, "monthly_revenue": 0, "total_users": 0
                }
                
                limits = safe_file_operation(USER_LIMITS_FILE, 'read', {})
                today = date.today().isoformat()
                active_users = sum(1 for user_data in limits.values() if today in user_data and user_data[today] > 0)
                
                stats_text = f"""📊 **STATISTICHE TAXAMI BOT**

👥 **Lead totali:** {len(leads)}
💎 **Utenti Premium attivi:** {premium_stats['active_premium_users']}
💰 **Revenue mensile:** €{premium_stats['monthly_revenue']:.2f}
👤 **Utenti Premium totali:** {premium_stats['total_users']}
📈 **Utenti attivi oggi:** {active_users}
🔧 **Errori totali:** {error_count}"""
                    
            except Exception as e:
                stats_text = f"📊 **STATISTICHE TAXAMI BOT**\n\n❌ Errore: {e}"
            
            send_message_robust(chat_id, stats_text)
            return
        
        user_id = user.get('id')
        is_premium = premium_manager.is_premium_user(user_id) if premium_manager else False
        
        # Check limits per free users
        if not is_premium:
            usage_today = check_user_limits_robust(user_id)
            
            if usage_today >= FREE_QUESTIONS_PER_DAY:
                send_message_robust(
                    chat_id,
                    f"""⏰ **Limite giornaliero raggiunto!**

Hai esaurito le {FREE_QUESTIONS_PER_DAY} domande gratuite.

💎 **UPGRADE PREMIUM per domande illimitate!**""",
                    {"inline_keyboard": [
                        [{"text": "💎 Upgrade Premium", "callback_data": "premium"}],
                        [{"text": "📋 Menu Principale", "callback_data": "main_menu"}]
                    ]}
                )
                return
            
            increment_user_usage_robust(user_id)
        
        # Trova domanda correlata
        user_words = text.lower().split()
        best_match = None
        max_matches = 0
        
        all_questions = {**DOMANDE_FREE}
        if is_premium:
            all_questions.update(DOMANDE_PREMIUM)
        
        for q_id, question in all_questions.items():
            keywords = question["keywords"]
            matches = sum(1 for keyword in keywords if any(keyword in word for word in user_words))
            
            if matches > max_matches:
                max_matches = matches
                best_match = q_id
        
        # Genera risposta AI
        knowledge = load_fiscal_knowledge_robust()
        fiscal_context = search_fiscal_content_robust(text, knowledge)
        
        enhanced_prompt = f"Domanda fiscale: {text}\n\nContesto normativo:\n{fiscal_context}" if fiscal_context else f"Domanda fiscale: {text}"
        
        ai_response = generate_ai_response_robust(
            enhanced_prompt,
            is_premium,
            600 if is_premium else 400
        )
        
        # Footer e contatti
        if is_premium:
            footer = "\n\n👑 Premium: Domande illimitate attive"
        else:
            remaining = max(0, FREE_QUESTIONS_PER_DAY - check_user_limits_robust(user_id))
            footer = f"\n\n🆓 Ti rimangono {remaining} domande gratuite oggi"
            if remaining <= 1:
                footer += "\n💎 Upgrade Premium per domande illimitate!"
        
        contacts = "\n\n📞 **Studio Di Sabato e Partners**\n🏢 Borgomanero (NO) | ☎️ 0322.340513 | 📱 338.457.2198"
        
        final_response = ai_response + footer + contacts
        
        send_message_robust(
            chat_id,
            final_response,
            {"inline_keyboard": [[{"text": "📋 Menu Domande", "callback_data": "main_menu"}]]}
        )
        
    except Exception as e:
        log_error("HANDLE_TEXT", str(e), {"chat_id": chat_id, "text": text, "user": user})
        send_message_robust(
            chat_id,
            "⚠️ Si è verificato un errore nell'elaborazione. Riprova o contatta il supporto.",
            {"inline_keyboard": [[{"text": "📋 Menu Principale", "callback_data": "main_menu"}]]}
        )

# Main loop super robusta
def main_loop():
    """Loop principale con gestione crash avanzata"""
    logger.info("🚀 Taxami Bot Premium Robust - Avvio...")
    
    # Health checks
    try:
        knowledge = load_fiscal_knowledge_robust()
        if knowledge:
            logger.info(f"✅ Database fiscale caricato: {len(knowledge)} sezioni")
        else:
            logger.warning("⚠️ Database fiscale non trovato - funziona solo con AI base")
    except Exception as e:
        logger.error(f"❌ Errore caricamento database: {e}")
    
    # Test Stripe
    try:
        if premium_manager:
            premium_stats = premium_manager.get_premium_stats()
            logger.info(f"✅ Stripe connesso: {premium_stats['active_premium_users']} utenti premium attivi")
        else:
            logger.warning("⚠️ Premium manager non disponibile")
    except Exception as e:
        logger.warning(f"⚠️ Stripe warning: {e}")
    
    # Test OpenAI
    if client:
        logger.info("✅ OpenAI client inizializzato")
    else:
        logger.error("❌ OpenAI client fallito")
    
    offset = None
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    logger.info("✅ Taxami Bot Premium Robust AVVIATO! Premi Ctrl+C per fermare.")
    
    while True:
        try:
            updates = get_updates_robust(offset)
            
            if not updates or not updates.get("ok"):
                time.sleep(1)
                continue
            
            # Reset consecutive errors su successo
            consecutive_errors = 0
            
            for update in updates.get("result", []):
                try:
                    offset = update["update_id"] + 1
                    
                    # Messaggio testo
                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        user = message["from"]
                        
                        if message.get("text"):
                            if message["text"] == "/start":
                                handle_start_robust(chat_id, user)
                            else:
                                handle_text_robust(chat_id, message["text"], user)
                    
                    # Callback query
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        chat_id = callback["message"]["chat"]["id"]
                        message_id = callback["message"]["message_id"]
                        user = callback["from"]
                        
                        handle_callback_robust(callback, chat_id, message_id, user)
                
                except Exception as e:
                    log_error("UPDATE_PROCESSING", str(e), {"update": update})
                    logger.error(f"Errore processamento update: {e}")
                    # Continua con prossimo update invece di crashare
                    continue
                    
        except KeyboardInterrupt:
            logger.info("🛑 Bot fermato dall'utente.")
            break
            
        except Exception as e:
            consecutive_errors += 1
            log_error("MAIN_LOOP", str(e), {"consecutive_errors": consecutive_errors})
            logger.error(f"Errore principale (#{consecutive_errors}): {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.critical(f"💥 Troppi errori consecutivi ({consecutive_errors}). Pausa 60 secondi...")
                time.sleep(60)
                consecutive_errors = 0
            else:
                time.sleep(5)  # Breve pausa prima del retry

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        logger.critical(f"💥 CRASH CRITICO: {e}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        log_error("CRITICAL_CRASH", str(e))
        sys.exit(1)