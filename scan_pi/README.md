1. Installatie van Docker

Installeer Docker en zorg ervoor dat de dienst automatisch wordt gestart bij het opstarten van het systeem:

sudo apt install docker.io -y
sudo systemctl enable docker
sudo systemctl start docker

2. Starten van Greenbone

Ga naar de map waarin alle Greenbone-bestanden zich bevinden:

cd ~/greenbone


Start vervolgens de Docker containers:

docker compose up -d


Wacht totdat alle services volledig zijn opgestart.

3. Toegang tot de webinterface

Wanneer GVM is gestart, is de webinterface bereikbaar via:

<pi-ip>:9392


Log in met de standaardgegevens:

UN: admin
PW: admin


Het standaardwachtwoord moet direct worden gewijzigd om veiligheidsredenen.

4. Opslaan van inloggegevens voor automatische scripts

Maak in de map /greenbone een configuratiebestand aan:

nano gvm.env


Voeg de volgende inhoud toe:

GVM_USER=admin
GVM_PASS="JOUW_WACHWTOORD"


Vervang JOUW_WACHWTOORD door het nieuwe admin-wachtwoord en sla het bestand op.

Beperk vervolgens de toegangsrechten tot dit bestand:

chmod 600 gvm.env

5. Docker-containers correct configureren

Om een correcte opstartvolgorde en stabiele werking te garanderen, moeten de automatische herstartinstellingen van de containers worden aangepast:

docker update --restart=no greenbone-community-edition-gvm-tools-1
docker update --restart=no greenbone-community-edition-gsa-1
docker update --restart=no greenbone-community-edition-gvmd-1
docker update --restart=no greenbone-community-edition-openvas-1
docker update --restart=no greenbone-community-edition-openvasd-1
docker update --restart=no greenbone-community-edition-redis-server-1
docker update --restart=no greenbone-community-edition-pg-gvm-1

6. Installeren en activeren van systeemservices

Kopieer de benodigde service- en scriptbestanden:

cp ~/greenbone/greenbone-cleanstart.service /etc/systemd/system/
cp ~/greenbone/gvm-autoscan.service /etc/systemd/system/
cp ~/greenbone/gvm-autoscan.sh /usr/local/bin/


Activeer de services:

sudo systemctl daemon-reload
sudo systemctl enable greenbone-cleanstart.service
sudo systemctl enable gvm-autoscan.service

7. Herstart van het systeem

Start de Raspberry Pi opnieuw op:

sudo reboot


Na de herstart worden Docker, Greenbone en de automatische scans correct geïnitialiseerd en uitgevoerd.