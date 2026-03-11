import requests
from bs4 import BeautifulSoup
import os
import json
from unidecode import unidecode
import re


class Scraper:
    # pour recuperer les docpdf des deliberations disponibles sur le site de cdg90
    # pour chaque document on extrait :
    # le titre, la date,l 'url,le type(PV ou CR), un identifiant

    def __init__(self, url: str):
        # Initialisation du scraper
        self.url: str = url

    def scrape(self):
        # Méthode pour lancer le scraping de la page et afficher les documents

        page: requests.Response = requests.get(self.url)
        soup: BeautifulSoup = BeautifulSoup(page.text, "html.parser")

        documents:list[dict] = []
        for element in soup.find_all("a"):
            document: dict | None = self.parse_document(element=element)
            if not document:
                continue
            documents.append(document)

    def parse_document(self, element: BeautifulSoup) -> dict:
        # Retourne la liste des documents touves par le scraper
        # avancer si c'est pas un lien d'un pdf
        if not element.get("href") or ".pdf" not in element.get("href"):
            return None

        doc_url: str = element.get("href")

        # corriger les urls relatives
        if element.get("href").startswith("/"):
            doc_url: str = "https:www.cdg90.fr" + doc_url

        text: str = element.get_text(strip=True)

        # normalisation du texte(mettre tout en minuscule et sans accents)
        normal_text = unidecode(text).lower()

        # trier pour garder que liens ayant "seance du"
        if "seance du" not in normal_text:
            return None

        # utilisation de regex pour reconnaitre un patern et extraire la date
        current_date_rgx = re.match(
            r".*?(\d{1,2}(?:er|)\s[A-zéèû]+\s\d{4})", normal_text
        )
        if not current_date_rgx:
            return None
        current_date = current_date_rgx.group(1)

        if "pv" in doc_url.lower():
            doc_type = "PV"
        else:
            doc_type = "CR"

        doc_id = os.path.basename(doc_url).replace(".pdf", "")

        document = {
            "title": normal_text,
            "date": current_date,
            "url": doc_url,
            "type": doc_type,
            "id": doc_id,
        }
        return document

# Que seul la méthode instancié me permet d'avoir les logs des documents.
scraper = (
    Scraper(url="https://www.cdg90.fr/le-cdg-90/administration/deliberations-pv/")
    .scrape()
)