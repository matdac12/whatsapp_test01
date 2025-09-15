Documentazione per attivare Ngrok

- Riservare un dominio --> arroweld-whatsapp.ngrok.app
- Editare config file -> ngrok config edit

version: 3
agent:
  authtoken: 32Q45jlOadLeRRgReGPeFYf69mM_4LUktLki7otguV3pQPxiZ
endpoints:
  - name: whatsapp-bot
    url: arroweld-whatsapp.ngrok.app
    upstream:
      url: 3000

Ora, copia l'indirizzo esatto del config file e poi (usa chatgpt se serve)

C:\Users\Administrator\AppData\Local\ngrok\ngrok.yml

# 1) Path to your config
$cfg = "$env:LOCALAPPDATA\ngrok\ngrok.yml"

# 2) Validate config
ngrok config check --config $cfg

# 3) Install Windows service
ngrok service install --config $cfg

# 4) Start it (auto-starts on boot)
ngrok service start

DONE
