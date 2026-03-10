import requests
from bs4 import BeautifulSoup
import os
import json
from unidecode import unidecode

url = "https://www.cdg90.fr/le-cdg-90/administration/deliberations-pv/"
page = requests.get(url)
soup = BeautifulSoup(page.text, "html.parser")
    
documents = []
current_date= None


for element in soup.find_all("a"):
    text = element.get_text(strip=True)
    normal_text= unidecode(text).lower()
    # todo regex .*?(\d{1,2}(?:er|)\s[A-zéèû]+\s\d{4})
    

    if "seance du" in normal_text:
        current_date = normal_text.replace("seance du", "").strip()
    
    if element.name == "a" and element.get("href") and ".pdf" in element.get("href"):
        doc_url = element["href"]  
        if doc_url.startswith("/"):
            doc_url= "https:www.cdg90.fr" +doc_url

    
        title = normal_text
        if "pv" in doc_url.lower():
            doc_type = "PV"
        else:
            doc_type = "CR"
        open("pdf_urls.txt", "a+").write(doc_url+"\n")
            
            
        doc_id = os.path.basename(doc_url).replace(".pdf", "")
        
        document= {
            "title": title,
            "date":current_date,
            "url":doc_url,
            "type":doc_type,
            "id":doc_id
        }
        documents.append(document)   

print(json.dumps(documents, indent=4, ensure_ascii=False))

print(normal_text)
pass
