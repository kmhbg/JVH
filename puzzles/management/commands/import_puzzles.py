from django.core.management.base import BaseCommand
from puzzles.models import Puzzle
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.db import connections

class Command(BaseCommand):
    help = 'Importerar pussel från JVH webbsida'
    
    BASE_URL = "https://www.jvh-puzzels.com"

    def handle(self, *args, **options):
        # Använd puzzles_db connection
        with connections['puzzles_db'].cursor() as cursor:
            try:
                url = urljoin(self.BASE_URL, "/digital-museum/list-of-all-puzzles/list-of-all-puzzles.html")
                
                self.stdout.write("Hämtar data från JVH...")
                response = requests.get(url)
                self.stdout.write(f"Status kod: {response.status_code}")
                
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table')
                
                if not table:
                    self.stdout.write(self.style.ERROR('Kunde inte hitta tabellen med pussel'))
                    return
                    
                rows = table.find_all('tr')[1:]
                self.stdout.write(f"Hittade {len(rows)} pussel")
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 9:
                        puzzle_data = {
                            'name_en': cols[0].text.strip(),
                            'name_nl': cols[1].text.strip(),
                            'product_number': cols[2].text.strip(),
                            'series': cols[3].text.strip(),
                            'pieces': cols[4].text.strip(),
                            'illustrator': cols[5].text.strip(),
                            'publisher': cols[6].text.strip(),
                            'release_date': cols[7].text.strip(),
                            'manufacturer': cols[8].text.strip(),
                        }
                        
                        self.stdout.write(f"Importerar: {puzzle_data['name_en']}")
                        
                        # Skapa eller uppdatera pussel
                        puzzle, created = Puzzle.objects.update_or_create(
                            product_number=puzzle_data['product_number'],
                            defaults=puzzle_data
                        )
                
                self.stdout.write(self.style.SUCCESS('Import slutförd'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ett fel uppstod: {str(e)}')) 