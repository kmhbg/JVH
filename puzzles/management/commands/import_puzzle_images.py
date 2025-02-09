from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from puzzles.models import Puzzle, PuzzleImage
import re
from django.core.files.base import ContentFile
from urllib.parse import urljoin
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class Command(BaseCommand):
    help = 'Importerar pusselbilder från puzzle-1000-pieces.com'

    def clean_product_number(self, number):
        """Rensa och standardisera produktnummer"""
        if not number:
            return None
        # Ta bort alla mellanslag och gör om till versaler
        number = number.strip().upper()
        # Ta bort eventuella JVH- prefix
        number = number.replace('JVH', '')
        # Ta bort alla icke-alfanumeriska tecken
        number = re.sub(r'[^A-Z0-9]', '', number)
        return number

    def handle(self, *args, **options):
        url = 'https://www.puzzle-1000-pieces.com/jan-van-haasteren/puzzle-list/#Jan%20van%20Haasteren%20puzzels%20overzicht%20-%2010%20stukjes'
        
        try:
            # Chrome-konfiguration
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            service = Service(ChromeDriverManager().install())
            
            # Hämta alla pussel från databasen
            db_puzzles = {
                self.clean_product_number(puzzle.product_number): puzzle 
                for puzzle in Puzzle.objects.using('puzzles_db').all()
            }
            
            self.stdout.write(f"Hittade {len(db_puzzles)} pussel i databasen")
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                driver.get(url)
                
                # Vänta på att innehållet ska laddas
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "info-table"))
                )
                
                # Hitta alla rader i tabellen
                rows = driver.find_elements(By.CSS_SELECTOR, ".info-table tr")
                matches = 0
                
                for row in rows:
                    try:
                        # Hitta produktnummer-cellen
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if not cells or len(cells) < 2:
                            continue
                            
                        # Produktnumret finns i andra cellen
                        product_number = cells[1].text.strip()
                        if not product_number:
                            continue
                            
                        clean_number = self.clean_product_number(product_number)
                        if not clean_number:
                            continue
                        
                        # Hitta matchande pussel
                        puzzle = db_puzzles.get(clean_number)
                        if not puzzle:
                            self.stdout.write(f"Inget matchande pussel hittades för {product_number} (rensat: {clean_number})")
                            continue
                        
                        # Hitta bilden i första cellen
                        img_element = cells[0].find_element(By.TAG_NAME, "img")
                        if not img_element:
                            continue
                            
                        img_url = img_element.get_attribute('src')
                        if not img_url:
                            continue
                            
                        matches += 1
                        
                        # Kontrollera om bilden redan finns
                        if PuzzleImage.objects.using('puzzles_db').filter(
                            puzzle=puzzle,
                            uploaded_by_id=1
                        ).exists():
                            self.stdout.write(f"Bild finns redan för {product_number}")
                            continue
                        
                        # Hämta och spara bilden
                        img_response = requests.get(img_url)
                        img_response.raise_for_status()
                        
                        puzzle_image = PuzzleImage(
                            puzzle=puzzle,
                            uploaded_by_id=1
                        )
                        
                        file_name = f"{clean_number}.jpg"
                        puzzle_image.image.save(
                            file_name,
                            ContentFile(img_response.content),
                            save=False
                        )
                        puzzle_image.save(using='puzzles_db')
                        
                        self.stdout.write(self.style.SUCCESS(
                            f"Bild sparad för {product_number} (rensat: {clean_number})"
                        ))
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Fel vid import av bild: {str(e)}"
                        ))
                        continue
                
                self.stdout.write(self.style.SUCCESS(
                    f'Bildimport klar! Matchade {matches} av {len(rows)} pussel'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Fel vid webbläsarautomation: {str(e)}"))
                raise
            finally:
                driver.quit()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ett fel uppstod: {str(e)}')) 