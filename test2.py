import requests
from bs4 import BeautifulSoup, Tag, element 
import csv
import re
from urllib.parse import unquote
import cloudscraper
import logging, sys, os
import dateparser
from datetime import date, datetime


logging.basicConfig(
    format="%(asctime)s : %(levelname)-8s {%(filename)s:%(lineno)d} : %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)

try:
    __level = getattr(logging, os.getenv("LOG_LEVEL", "info").upper())
except:
    __level = logging.INFO

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(level=__level)



class Scraper:

    #Scraper pour les délibérations du Conseil Communautaire
    # des Pyrénées Audoises.
    # Pour chaque document on extrait :
    # - COLL_NOM:  nom dela collectivite
    # - DELIB_OBJET: Le nom du fichier
    # - DELIB_DATE: la date (héritée du bloc ) au format A-M_J
    # - DELIB_URL: l'url
    # - type:  ODJ, Délibération, Liste, PV
    # - DELIB_ID: identifiant (DC_YYYY_NNN)


    BASE_URL: str = "https://www.pyreneesaudoises.fr"
    COLL_NOM: str = "Communauté de Communes des Pyrénées Audoises"

    # Regex compilées une fois pour toute la classe
    REGEX_NUMERO: re.Pattern[str] = re.compile(
        r'(DC[_-]\d{4}[_-]\d{3,4}(?:BIS)?)',
        re.IGNORECASE
    )
    REGEX_ANNEE: re.Pattern[str] = re.compile(r'\b(20\d{2})\b')
    REGEX_DATE_FICHIER: re.Pattern[str] = re.compile(
        r'(\d{2})\.(\d{2})\.(\d{4})'
    )



    def __init__(self, url: str):
        # Initialisation du scraper
        self.url: str = url

        # Headers pour éviter le 403
        self.headers: dict[str,str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer": self.BASE_URL,
        }

        # Mémoire du contexte (année/mois courants)
        self._annee: str | None = None
        self._mois:  str | None = None
        self._mois_num: str | None = None
        self._jour: str = "01"

    def scrape(self) -> list[dict]:
        # Méthode pour lancer le scraping

        scraper:cloudscraper.Cloudflare = cloudscraper.create_scraper(browser='chrome')
        page:requests.Response= scraper.get(self.url, headers=self.headers)

        logging.info(f"Status code : {page.status_code}")

        if page.status_code != 200:
            logging.error("Impossible de récupérer la page")
            return []

        soup: BeautifulSoup = BeautifulSoup(page.text, "html.parser")
        documents: list[dict[str,str]] = []

        for element in soup.find_all(True):

            # Mettre à jour l'année et le mois courants
            self.parse_date(element)

            # Traiter uniquement les blocs de fichiers PDF
            classes = element.get("class") or []
            if "cc-m-download-file" not in classes:
                continue

            document: dict[str, str] | None = self.parse_document(element)
            if not document:
                continue

            documents.append(document)

        print(f"{len(documents)} documents trouvés")
        return documents

    def parse_date(self, element) -> None:
        # Met à jour l'année courante quand on trouve un h2
        if element.name == "h2":
            match = self.REGEX_ANNEE.search(element.get_text())
            if not match:
                return
            self._annee    = match.group(1)
            self._mois     = None
            self._mois_num = None
            self._jour = "01"
            return

        # Met à jour le mois courant quand on trouve un h3
        if element.name == "h3":
            texte: str = element.get_text().strip()
            date_parsee: datetime | None = dateparser.parse(texte, languages=["fr"])

            if not date_parsee:
                return
            self._mois = texte.capitalize()
            self._mois_num = date_parsee.strftime("%m")
            self._jour = "01"
            return
        # Cas bloc fichier — on cherche une date exacte dans le nom
        classes = element.get("class") or []
        if "cc-m-download-file" not in classes:
            return

        lien = element.find("a", class_="cc-m-download-link")
        if not lien or not isinstance(lien, Tag):
            return

        nom = unquote(str(lien.get("href", "")).split("/")[-1].split("?")[0])

        # Cas ODJ — date en français dans le nom
        if "odj" in nom.lower():
            texte_propre = nom.replace("+", " ").replace(".pdf", "")
            date_parsee = dateparser.parse(texte_propre, languages=["fr"])
            if date_parsee:
                self._jour = date_parsee.strftime("%d")
            return

        # Cas Liste — date DD.MM.YYYY dans le nom
        match_date = self.REGEX_DATE_FICHIER.search(nom)
        if match_date:
            jour, mois, annee = match_date.groups()
            self._jour = jour
            return

        # Cas général — jour inconnu
        self._jour= "01"

    def parse_document(self, element) -> dict[str, str] | None:
        # Retourne un document structuré depuis un bloc HTML

        lien = element.find("a", class_="cc-m-download-link")
        if not lien:
            return None

        href: str = str(lien.get("href", "")).split("?")[0]
        if ".pdf" not in href:
            return None

        # Nom réel depuis l'URL 
        nom_fichier: str = unquote(href.split("/")[-1].split("?")[0])

        # Identifiant avec regex
        match_num = self.REGEX_NUMERO.search(nom_fichier)
        doc_id: str = match_num.group(1).upper() if match_num else "N/A"

        # Date héritée du contexte h2/h3
        
        # Type détecté par regex
        doc_type: str = self.detecter_type(nom_fichier)

        return {
            "COLL_NOM":    self.COLL_NOM,
            "DELIB_ID":    doc_id,
            "DELIB_DATE":  self.parse_date_bloc(),
            "DELIB_OBJET": nom_fichier,
            "DELIB_URL":   self.BASE_URL + href,
            "type":        self.detecter_type(nom_fichier),
        }

    def parse_date_bloc(self) -> str:
        #Retourne la date complète AAAA-MM-JJ
        if not self._annee or not self._mois_num:
            return "?"

        return f"{self._annee}-{self._mois_num}-{self._jour}"
    
    def detecter_type(self, nom: str) -> str:
        # Détecte le type de document par regex
        n: str = nom.lower().replace("+", " ") 
        if re.search(r'\bodj\b', n):
            return "ODJ"
        if re.search(r'dc[_-]\d{4}', n):
            return "Deliberation"
        if n.startswith("liste"):
            return "Liste"
        if re.search(r'\bpv\b|carence', n):
            return "PV"
        return "Autre"

documents = Scraper(
    url="https://www.pyreneesaudoises.fr/document-publics/d%C3%A9lib%C3%A9rations-ccpa/d%C3%A9lib%C3%A9rations-conseil-communautaire/"
).scrape()

# Sauvegarde CSV
if documents:
    with open("resultats.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=documents[0].keys())
        writer.writeheader()
        writer.writerows(documents)
    print("resultats.csv créé !")

# Aperçu
for doc in documents[:3]:
    print("\n".join(f"  {cle} : {valeur}" for cle, valeur in doc.items()) + "\n")