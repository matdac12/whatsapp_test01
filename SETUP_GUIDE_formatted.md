# Guida Implementazione Chatbot WhatsApp con AI

## 📋 Introduzione

Questa è una guida completa per implementare un chatbot WhatsApp intelligente utilizzando le API di Meta e OpenAI.

### ⚠️ Premessa Importante

**ATTENZIONE**: Non è possibile utilizzare contemporaneamente:
- L'app WhatsApp Business tradizionale (mobile/desktop)
- Le API di WhatsApp Business

Se si desidera utilizzare un numero esistente, sarà necessario:
1. Eliminare l'account dall'app WhatsApp Business
2. Collegare il numero alle API di Meta

## 🎯 Soluzione Proposta

La nostra soluzione prevede:

1. **Agente AI Intelligente**: Gestisce automaticamente le fasi iniziali della conversazione
   - Raccolta informazioni cliente
   - Richiesta numero d'ordine
   - Risposte alle domande frequenti

2. **Interfaccia Web di Controllo**: Per monitorare e intervenire manualmente quando necessario
   - Visualizzazione conversazioni in tempo reale
   - Possibilità di risposta manuale
   - Dashboard analytics

---

## 1. 🔧 Configurazione WhatsApp Business API

### 1.1 Creazione App Meta

1. **Accedere a Meta Business**
   - URL: https://business.facebook.com/business/loginpage
   - Utilizzare credenziali Facebook aziendali

2. **Creare una nuova App**
   - Andare su: https://developers.facebook.com/apps
   - Cliccare "Crea un'app"
   - Nome app: [Nome della vostra azienda] Bot
   - Caso d'uso: Selezionare "Altro"
   - Tipo di app: **Azienda**
   - Selezionare portfolio business se presente

3. **Configurare i prodotti**
   - Aggiungere: **WhatsApp**
   - Aggiungere: **Webhooks**

### 1.2 Configurazione Numero di Telefono

1. **Aggiungere numero di telefono**
   - ⚠️ Il numero NON deve essere associato a nessuna app WhatsApp Business
   - Se nuovo numero: procedere direttamente
   - Se numero esistente: eliminare prima da app WhatsApp Business

2. **Configurazioni amministrative**
   - Aggiungere metodo di pagamento (richiesto da Meta)
   - Inserire informazioni fiscali azienda
   - Verifica aziendale in Business Manager (può richiedere 2-3 giorni)
   - Approvazione Display Name del numero

### 1.3 Token di Accesso Permanente

1. **Creare System User**
   - Andare su: https://business.facebook.com/latest/settings/system_users
   - Creare nuovo user con privilegi **Admin**
   - Assegnare permessi totali all'app creata

2. **Generare Token Universale**
   - Selezionare permessi:
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`
   - Salvare il token in luogo sicuro

### 1.4 Recupero Credenziali

Dalla dashboard dell'app (https://developers.facebook.com/apps):
1. Cliccare su WhatsApp
2. Sezione "Invia e ricevi"
3. **Salvare**:
   - ✅ Token d'accesso
   - ✅ ID del numero di telefono
   - ✅ ID dell'account WhatsApp Business

---

## 2. 🤖 Configurazione OpenAI

### 2.1 Setup Progetto

1. **Creare nuovo progetto**
   - Dashboard: https://platform.openai.com/
   - Nome progetto: "Progetto WhatsApp"
   - Separazione per monitoraggio costi dedicato

2. **Generare API Key**
   - Creare nuova chiave API
   - Associarla al progetto WhatsApp
   - Salvare in luogo sicuro

### 2.2 Configurazione Prompt (Responses API)

> **Nota**: Utilizziamo il nuovo sistema **Responses API** che supporta:
> - Variabili dinamiche
> - Tools integration
> - Prompt versioning
> - Maggiore controllo sul comportamento

1. **Creare nuovo Prompt**
   - Modello consigliato: `gpt-4.1` o `gpt-4o`
   - System message iniziale:
     ```
     Sei un agente WhatsApp incaricato all'assistenza clienti 
     e all'acquisizione delle informazioni di base del contatto
     ```

2. **Salvare Prompt ID**
   - Il Prompt ID sarà necessario per il codice Python

### 2.3 Vector Storage (Opzionale)

1. **Creare Vector Store**
   - URL: https://platform.openai.com/storage/vector_stores
   - Nome: "Vector Store Progetto WhatsApp"
   - Qui si possono caricare:
     - Documentazione prodotti
     - FAQ
     - Listini prezzi
     - Manuali

2. **Salvare Vector Store ID**

---

## 3. 🌐 Configurazione ngrok

### Cos'è ngrok?

ngrok è un servizio che permette di esporre un server locale su internet in modo sicuro, perfetto per ricevere webhook di WhatsApp mantenendo il codice in esecuzione locale.

### 3.1 Setup Account

1. **Creare account**
   - Registrazione: https://dashboard.ngrok.com/
   - Sottoscrivere abbonamento **Premium** (per URL fisso e always on functionality, 18 Euro al mese)

2. **Ottenere Access Token**
   - Dal dashboard ngrok
   - Salvare per configurazione

### 3.2 Installazione

1. **Download ngrok**
   - URL: https://ngrok.com/download
   - Scegliere versione per il proprio OS

2. **Configurazione iniziale** (una sola volta)
   ```bash
   ngrok config add-authtoken [IL-TUO-TOKEN-QUI]
   ```

---

## 4. 💻 Sviluppo Python e Interfaccia

### 4.1 File di Configurazione (.env)

Creare file `.env` con tutti i segreti:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_PROMPT_ID=pmpt_xxxxxxxxxxxxx

# WhatsApp
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxx
WHATSAPP_PHONE_ID=xxxxxxxxxxxxx
WHATSAPP_ACCOUNT_ID=xxxxxxxxxxxxx

# Server
PORT=3000
VERIFY_TOKEN=my-verify-token-123
```

### 4.2 Script Python Necessari

1. **Script invio messaggi** (`send_whatsapp.py`)
   - Funzione per inviare messaggi via API

2. **Script ricezione webhook** (`webhook_openai.py`)
   - Server Flask per ricevere messaggi
   - Integrazione con OpenAI

3. **Gestore conversazioni** (`openai_conversation_manager.py`)
   - Mantiene contesto conversazioni
   - Gestisce sessioni utente

4. **Estrattore dati** (`data_extractor.py`)
   - Estrae informazioni strutturate
   - Salva profili clienti

### 4.3 Interfaccia Web - Opzioni

#### 📍 OPZIONE A - Interfaccia Locale (Consigliata)

**Caratteristiche**:
- Accessibile da `localhost:3000/dashboard`
- Visibile da tutti i PC sulla stessa rete locale
- Massima sicurezza (non esposto su internet)
- Zero configurazione autenticazione

**Vantaggi**:
- ✅ Implementazione immediata
- ✅ Nessun rischio sicurezza
- ✅ Accesso da ufficio per tutto il team

#### 🌍 OPZIONE B - Interfaccia Web Pubblica

**Caratteristiche**:
- Accessibile da internet con credenziali
- Username e password per accesso
- Monitoraggio da remoto

**Vantaggi**:
- ✅ Accesso da qualsiasi luogo
- ✅ Controllo da smartphone/tablet
- ⚠️ Richiede configurazione sicurezza aggiuntiva

> **Consiglio**: Partire con Opzione A e aggiungere accesso remoto successivamente se necessario

---

## 5. 🚀 Deployment e Manutenzione

### 5.1 Avvio del Sistema

1. **Terminal 1 - Server Python**
   ```bash
   python3 start_openai_bot.py
   ```

2. **Terminal 2 - ngrok**
   ```bash
   ngrok http 3000
   ```

3. **Configurare Webhook in Meta**
   - Copiare URL ngrok (es: https://abc123.ngrok.io)
   - Inserire in Meta: `https://abc123.ngrok.io/webhook`
   - Verify Token: stesso del file .env

### 5.2 Servizio 24/7

Per mantenere il bot attivo continuamente:

1. **Windows - Task Scheduler**
   - Creare task per avvio automatico
   - Configurare riavvio in caso di crash

2. **Linux - systemd service**
   - Creare file servizio
   - Enable per avvio automatico

3. **Monitoraggio**
   - Health check endpoint: `/health`
   - Log rotation configurato
   - Alert su errori critici

---

## 📊 Dashboard Funzionalità

La dashboard web includerà:

- **Vista Conversazioni**
  - Lista clienti attivi
  - Stato profilo (completo/incompleto)
  - Ultimo messaggio

- **Dettaglio Chat**
  - Cronologia completa messaggi
  - Informazioni cliente estratte
  - Possibilità invio manuale

- **Analytics**
  - Numero conversazioni giornaliere
  - Tasso completamento profili
  - Tempi di risposta medi

---



---

