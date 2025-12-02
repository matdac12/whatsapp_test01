# WhatsApp AI Assistant

Assistente virtuale intelligente per WhatsApp Business, basato su OpenAI GPT-4.

## Panoramica

Questo sistema permette di gestire conversazioni automatizzate su WhatsApp utilizzando l'intelligenza artificiale di OpenAI. L'assistente e in grado di:

- Rispondere in modo naturale alle domande dei clienti
- Raccogliere automaticamente i dati di contatto (nome, cognome, azienda, email)
- Gestire lo storico delle conversazioni
- Interrogare il database ordini per fornire informazioni sulle spedizioni

## Funzionalita Principali

### Conversazioni Intelligenti
L'assistente utilizza OpenAI GPT-4 per generare risposte contestuali e naturali, mantenendo il contesto della conversazione.

### Raccolta Dati Automatica
Il sistema estrae automaticamente le informazioni del cliente durante la conversazione:
- Nome e Cognome
- Ragione Sociale
- Email

### Dashboard Web
Interfaccia web per monitorare e gestire le conversazioni:
- Visualizzazione di tutte le conversazioni attive
- Storico messaggi in stile WhatsApp
- Modifica manuale dei profili cliente
- Modalita manuale per intervento dell'operatore

### Modalita Manuale
Possibilita di passare in modalita manuale per singolo contatto:
- L'AI genera bozze di risposta senza inviarle
- L'operatore puo modificare, approvare o rigenerare le risposte
- Note persistenti per ogni contatto

### Integrazione Ordini
Query automatiche sul database ordini per rispondere a domande come:
- "Quando arriva il mio ordine?"
- "Qual e lo stato della mia spedizione?"

## Requisiti

- Python 3.10+
- Account WhatsApp Business API
- Chiave API OpenAI
- ngrok (per sviluppo locale)

## Installazione

1. Clonare il repository
2. Creare ambiente virtuale:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```
3. Installare le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Configurare il file `.env` (vedere `.env.example`)

## Configurazione

Creare un file `.env` con le seguenti variabili:

```ini
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_ID=your_phone_id

# OpenAI
OPENAI_API_KEY=your_api_key
OPENAI_PROMPT_ID=your_prompt_id
OPENAI_MODEL=gpt-4.1

# Server
PORT=3000
VERIFY_TOKEN=your_verify_token
```

## Avvio

```bash
python start_openai_bot.py
```

La dashboard sara disponibile su `http://localhost:3000/dashboard`

## Struttura del Progetto

```
├── webhook_openai.py          # Server Flask principale
├── openai_conversation_manager.py  # Gestione conversazioni OpenAI
├── data_extractor.py          # Estrazione dati cliente
├── database.py                # Gestione database SQLite
├── order_tools.py             # Strumenti query ordini
├── webhook_notifier.py        # Notifiche webhook (Make/Zapier)
├── templates/
│   └── dashboard.html         # Interfaccia web
├── static/
│   └── style.css              # Stili dashboard
└── tests/                     # Script di test
```

## Sicurezza

- Le credenziali sono gestite tramite variabili d'ambiente
- Il database SQLite contiene dati sensibili e non deve essere condiviso
- L'accesso alla dashboard dovrebbe essere protetto in produzione

## Supporto

Per assistenza tecnica, contattare il team di sviluppo.
