Lokaal: 
1. Maak een venv met "python -m venv .venv"
2. Activeer de venv met ".venv/Scripts/activate" en install requirements.txt
3. voer dit commando uit: “python chatbot-local.py”
4. Bezoek “http://127.0.0.1:7860/”

Er wordt een lokaal bestand gedownload (2GB) in: 

Windows: C:\Users\<JeGebruikersnaam>\.cache\huggingface\hub

Linux / macOS: ~/.cache/huggingface/hub

Docker:

1. In deze map: "docker build -t openvas-chatbot ."
2. Als de image gedownload is: "docker run -p 7860:7860 openvas-chatbot"
3. Wacht even tot alles gedownload is, en na max 5 minuten zal de chatbot moeten werken.
4. Bezoek: "http://localhost:7860/"




