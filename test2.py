import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import unquote


class Scraper:
    
    #Scraper pour les délibérations du Conseil Communautaire
    # des Pyrénées Audoises.
    # Pour chaque document on extrait :
    # - le nom du fichier
    # - la date (héritée du bloc )
    # - l'url
    # - le type (ODJ, Délibération, Liste, PV)
    # l'identifiant (DC_YYYY_NNN)
    

    BASE_URL = "https://www.pyreneesaudoises.fr"

    # Regex compilées une fois pour toute la classe
    REGEX_NUMERO = re.compile(
        r'(DC[_-]\d{4}[_-]\d{3,4}(?:BIS)?)',
        re.IGNORECASE
    )
    REGEX_ANNEE = re.compile(r'\b(20\d{2})\b')

    MOIS_FR = {
        "janvier":"01", "février":"02", "mars":"03",
        "avril":"04",   "mai":"05",     "juin":"06",
        "juillet":"07", "août":"08",    "septembre":"09",
        "octobre":"10", "novembre":"11","décembre":"12"
    }

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

    def scrape(self) -> list[dict]:
        # Méthode pour lancer le scraping
        page: requests.Response = requests.get(
            self.url,
            headers=self.headers
        )

        print(f"Status code : {page.status_code}")

        if page.status_code != 200:
            print("Impossible de récupérer la page")
            return []

        soup: BeautifulSoup = BeautifulSoup(page.text, "html.parser")
        documents: list[dict[str,str]] = []

        for element in soup.find_all(True):

            # Mettre à jour l'année et le mois courants
            self._mettre_a_jour_contexte(element)

            # Traiter uniquement les blocs de fichiers PDF
            classes = element.get("class") or []
            if "cc-m-download-file" not in classes:
                continue

            document: dict | None = self.parse_document(element)
            if not document:
                continue

            documents.append(document)

        print(f"{len(documents)} documents trouvés")
        return documents

    def _mettre_a_jour_contexte(self, element) -> None:
        # Met à jour l'année courante quand on trouve un h2
        if element.name == "h2":
            match = self.REGEX_ANNEE.search(element.text)
            if match:
                self._annee    = match.group(1)
                self._mois     = None
                self._mois_num = None

        # Met à jour le mois courant quand on trouve un h3
        elif element.name == "h3":
            texte          = element.text.strip().lower()
            self._mois     = texte.capitalize()
            self._mois_num = self.MOIS_FR.get(texte, "??")

    def parse_document(self, element) -> dict[str, str] | None:
        # Retourne un document structuré depuis un bloc HTML
        lien = element.find("a", class_="cc-m-download-link")
        if not lien:
            return None

        href: str = str(lien.get("href", ""))
        if ".pdf" not in href:
            return None

        # Nom réel depuis l'URL 
        nom_fichier: str = unquote(
            href.split("/")[-1].split("?")[0]
        )

        # Taille du fichier
        taille_span = element.find("span", class_="cc-m-download-file-size")
        taille: str = taille_span.text.strip() if taille_span else "?"

        # Identifiant avec regex
        match_num = self.REGEX_NUMERO.search(nom_fichier)
        doc_id: str = match_num.group(1).upper() if match_num else "N/A"

        # Date héritée du contexte h2/h3
        date: str = (
            f"{self._annee}-{self._mois_num}"
            if self._annee and self._mois_num
            else "?"
        )

        # Type détecté par regex
        doc_type: str = self._detecter_type(nom_fichier)

        return {
            "title":   nom_fichier,
            "date":    date,
            "url":     self.BASE_URL + href,
            "type":    doc_type,
            "id":      doc_id,
            "taille":  taille,
        }

    def _detecter_type(self, nom: str) -> str:
        # Détecte le type de document par regex
        n = nom.lower()
        if re.search(r'\bodj\b', n):           
            return "ODJ"
        if re.search(r'dc[_-]\d{4}', n):       
            return "Deliberation"
        if re.search(r'liste.{0,10}delib', n):  
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
    print(doc)
