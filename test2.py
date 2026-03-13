from cloudscraper import CloudScraper


from re import Match
import requests
from bs4 import BeautifulSoup
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
    # Scraper pour les délibérations du Conseil Communautaire
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
        r"(DC[_-]\d{4}[_-]\d{3,4}(?:BIS)?)", re.IGNORECASE
    )
    REGEX_ANNEE: re.Pattern[str] = re.compile(r"\b(20\d{2})\b")

    # FIXME Revoir ce pattern pour les dates d'ODJ
    REGEX_DATE_FICHIER = re.compile(r"(\d{1,2})[.\-_](\d{1,2})[.\-_](20\d{2})")
    def __init__(self, url: str):
        # Initialisation du scraper
        self.url: str = url

        # Headers pour éviter le 403
        self.headers: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer": self.BASE_URL,
        }

        self._annee: str | None = None
        self._mois: str | None = None
        self._mois_num: str | None = None
        self._jour: str = "01"

    def scrape(self):
        # Méthode pour lancer le scraping

        scraper= cloudscraper.create_scraper(browser="chrome")
        try:
            page: requests.Response = scraper.get(self.url, headers=self.headers)
        except Exception as e:
            LOGGER.error(f"Erreur requette: {e}")
            return []
        logging.info(f"Status code : {page.status_code}")

        if page.status_code != 200:
            logging.error("Impossible de récupérer la page")
            return []

        soup: BeautifulSoup = BeautifulSoup(page.text, "html.parser")
        
        content = soup.find(id="content_area")
        if not content:
            LOGGER.error("balise introuvable")
            return []
        
        documents: list[dict[str, str]] = []

        for element in content.find_all("div"):
            # Mettre à jour l'année et le mois courants
            classes = element.get("class") or []
            try:

                #  ANNEE 
                if "j-header" in classes and element.find("h2"):
                    annee = element.get_text()
                    match = self.REGEX_ANNEE.search(annee)
                    if match:
                        self._annee = match.group(1)
                        self._mois = None
                        self._mois_num = None
                        self._jour = "01"
                    continue

                #  MOIS 
                if "j-header" in classes and element.find("h3"):
                    mois = element.get_text().strip()

                    date_parsee = dateparser.parse(mois, languages=["fr"])

                    if date_parsee:
                        self._mois = mois
                        self._mois_num = date_parsee.strftime("%m")
                        self._jour = "01"

                    continue

                #  DOCUMENT 
                if "j-downloadDocument" not in classes:
                    continue

                doc: dict[str, str] | None = self.parse_document(element)

                if doc:
                    documents.append(doc)

            except Exception as e:
                LOGGER.warning(f"Erreur de parsing: {e}")

        LOGGER.info(f"{len(documents)} documents trouvés")

        return documents

    # FIXME changer nom de variable
    def parse_document(self, element) -> dict[str, str] | None:  # noqa: F811
        # Retourne un document structuré depuis un bloc HTML
        try:
                
            lien = element.find("a")
            if not lien:
                return None

            href: str = str(lien.get("href", "")).split("?")[0]
            if ".pdf" not in href:
                return None

            # Nom réel depuis l'URL
            nom_fichier: str = unquote(href.split("/")[-1])

            # Identifiant avec regex
            match_id: Match[str] | None = self.REGEX_NUMERO.search(nom_fichier)
            doc_id: str = match_id.group(1).upper() if match_id else "N/A"

            # Type détecté par regex
            n = nom_fichier.lower()

            if "odj" in n:
                doc_type = "ODJ"
            elif "dc" in n:
                doc_type = "Deliberation"
            elif n.startswith("liste"):
                doc_type = "Liste"
            elif "pv" in n or "carence" in n:
                doc_type = "PV"
            else:
                doc_type = "Autre"

            #DATE
            jour = "01"
            match_date = self.REGEX_DATE_FICHIER.search(nom_fichier)
            LOGGER.info(f"match_date sur '{nom_fichier}' → {match_date}")
            if match_date:
                jour = match_date.group(1).zfill(2)

            elif "odj" in n:
                match_odj = re.search(r"(\d{1,2})\+([^\+]+)\+(20\d{2})", nom_fichier)                
                if match_odj:
                    jour = match_odj.group().zfill(2)

            delib_date = f"{self._annee}-{self._mois_num}-{self._jour}"

            return {
                "COLL_NOM": self.COLL_NOM,
                "DELIB_ID": doc_id,
                "type": doc_type,
                "DELIB_DATE": delib_date,
                "DELIB_OBJET": nom_fichier,
                "DELIB_URL": self.BASE_URL + href,
            }
        except Exception as e:

            LOGGER.warning(f"Erreur document : {e}")
            return None

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