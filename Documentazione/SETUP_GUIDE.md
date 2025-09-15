Questa è una guida per implementare un chatbot Whatsapp da zero. 

Premessa. Attualmente NON è possibile utilizzare l'app Whatsapp Business (quella a cui siamo abituati) e gli API di whatsapp contemporaneamente. 
Questo vuol dire che se vogliamo utilizare lo stesso numero di adesso, bisognerà prima eliminare l'account tramite l'app e poi collegarlo agli API di Meta. 

La seguente è l'opzione che proponiamo. 

Implementare l'API di whatsapp e far gestire le fasi iniziali della conversazione ad un Agente AI, progettato da noi con instruzioni specifiche (es: richiesta info personali, richiesta numero d'ordine).

Costruire un interfaccia web dove possiamo monitorare le conversazioni con i clienti e, se necessario, intervenire e rispondere manualmente. 

Processo, da zero. 

INIZIO SET UP WHATSAPP

-Accedere a Meta Business: https://business.facebook.com/business/loginpage (login facebook)
-Andare su https://developers.facebook.com/apps e cliccare 'Crea un'app'
-Dare un nome, quando chiede caso d'uso selezionare 'Altro'
-Selezionare tipo di app: Azienda
-Crea APP (selezionare portfolio business se pesente)
-Aggiungere prodotti all'app -> Whatsapp e Webhooks
-Aggiungere Numero di telefono, assicurarsi sia un numero NON associato a nessun app Whatsapp Business
-Aggiungere metodo di pagamento (arriva un avviso)
-Aggiungere informazioni fiscali azienda 
-Abilitare token d'accesso senza scadenza -> guida:  https://developers.facebook.com/blog/post/2022/12/05/auth-tokens/?utm_source=chatgpt.com
   - Andare su system users: https://business.facebook.com/latest/settings/system_users
   - Creare un user con privilegi admin, dare permessi totali all'app creata in precedenza
   - Crea token universale, scegliere whatsapp_business_messaging + whatsapp_business_management

-Dalla dashboard dell'app (che si raggiunge da qui e cliccando sul nome dell'app: https://developers.facebook.com/apps) cliccare su whatsapp. Nella sezione "Invia e ricevi" selezionare un numero di telefono. Quello dell'azienda se è gia stato convalidato, sennò generare un numero di prova. 
-Salvare il token d'accesso, l'ID del numero di telefono, l'ID dell'account. Serviranno per le chiamate da Python. 
-Implementare servizio webhook fornendo il link e Verify Token. (questi verranno generati da NGrok, sezione 3)
- Altre cose, se non già presenti: Verifica aziendale in Business Manager e approvazione Display Name del numero. Possono volerci un paio di giorni. 

FINE SET UP WHATSAPP

INIZIO SET UP OPENAI

Abbiamo già un account OpenAI dai progetti precedenti.
-Creare nuovo progetto nella dashboard (https://platform.openai.com/chat) e chiamarlo Progetto Whatsapp
-Creare una nuova chiave API ed associarla al progetto. Facciamo cosi per monitorare l'utilizzo e costi del progetto PIVA e progetto Whatsapp separatamente. 
-Creare nuovo Prompt. Useremo il nuovo sistema 'Responses API' che permette l'utilizzo di variabili, tools, e prompt dinamici. OpenAI deprecherà i vecchi sistemi di Assistenti e Chat Completions. Cosi facendo non avremo bisogno di cambiare codice fra qualche mese. 
-Scegliere titolo, modello, system message. Per adesso usare: "Sei un agente Whatsapp incaricato all'assistenza clienti e all'acquisizione delle informazioni di base del contatto". Implementeremo in seguito. 
-Salvarsi il prompt ID, servirà per il codice. 
-Creare vector storage per l'assistente (https://platform.openai.com/storage/vector_stores). Qui possiamo (manualmente o tramite codice) aggiungere qualunque tipo di file e info che vogliamo l'assistente abbia. Chiamare il vector store "Vector Store Progetto Whatsapp" e salvarsi l'ID. 
-A questo punto possiamo iniziare a creare un file protetto (.env) nella nostra directory. Avrà all'interno questi 'segreti':
     - OPEN_AI_KEY
     - OPEN_AI_PROMPT_ID
     - WHATSAPP_ACCESS_TOKEN
     - WHATSAPP_PHONE_ID
     - WHATSAPP_ACCOUNT_ID

FINE SET UP OPENAI

INIZIO SET UP NGROK
NGrok è un servizio che permette ad uno script locale di collegarsi al web e ricevere dei webhooks (in questo caso i messaggi in entrata di WA). Risulta essere una soluzione ottimale per noi perchè ci permette di eseguire tutto in locale ed esporci al web solo per i mesaggi di entrata/uscita. 

-Creare account: https://dashboard.ngrok.com/
-Sottoscrivere abbonamento Premium
-Ottenere Access Token
-Download Grok: https://ngrok.com/download
-Un volta sola, eseguire questo comando: ngrok config add-authtoken incollare-access-token-qui

FINE SET UP NGROK

INIZIO SET UP PYTHON

A questo punto dovremmo avere già un nostro file .env con tutti i segreti
-Scrivere script per invio messaggi Whatsapp
-Scrivere script per ricezione messaggi Whatsapp
-Scrivere script per interagire con l'API di OpenAI (creazione risposte, analisi messaggi utente, analisi stato raccolta dati)
-Scrivere altri script con funzioni helper. 

-Programmare una dasboard di visualizzazione messaggi. Qui si può andare da un'interfaccia minimale, ad una il più simile possibile a Whatsapp. Da decidere. 
Abbiamo Due Opzioni per l'Interfaccia di Gestione:

  OPZIONE A - Interfaccia Locale (Consigliata per iniziare):
  Un pannello di controllo accessibile solo dal computer dove gira il server, perfetto per gestione diretta in ufficio - massima sicurezza, zero configurazione, accesso        
  immediato aprendo il browser su localhost:3000/dashboard.
  Questo significa che in ufficio tutti i colleghi collegati alla stessa rete aziendale possono vedere e usare la dashboard, ma rimane inaccessibile da internet esterno.

  OPZIONE B - Interfaccia Web Pubblica:
  Un pannello accessibile da qualsiasi dispositivo via internet (smartphone, tablet, PC) con username e password, ideale per monitorare e rispondere alle conversazioni
  anche fuori ufficio - richiede configurazione di sicurezza aggiuntiva ma offre massima flessibilità di accesso.

  Possiamo partire con la versione locale e aggiungere l'accesso remoto in seguito se necessario.


-Impostare dei file di servizio che mantenghino lo script attivo 24/7 e che si riattivino in caso di crash, netwrok down etc. 
-Utilizzare le Unità di Pianificazione di Windows per attivare gli script e server. 








