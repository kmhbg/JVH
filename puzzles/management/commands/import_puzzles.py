from django.core.management.base import BaseCommand
from puzzles.models import Puzzle, PuzzleImage
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
                        
                        # Försök hitta bild-URL
                        link = cols[9].find('a') if len(cols) > 9 else None
                        if link and 'href' in link.attrs:
                            detail_url = urljoin(self.BASE_URL, link['href'])
                            image_urls = self.get_puzzle_image(detail_url)
                            if image_urls:
                                puzzle_data['image_url'] = image_urls
                        
                        # Skapa eller uppdatera pussel
                        puzzle, created = Puzzle.objects.update_or_create(
                            product_number=puzzle_data['product_number'],
                            defaults=puzzle_data
                        )

                        # Hämta och spara alla bilder
                        if link and 'href' in link.attrs:
                            detail_url = urljoin(self.BASE_URL, link['href'])
                            self.save_puzzle_images(puzzle, detail_url)
                
                self.stdout.write(self.style.SUCCESS('Import slutförd'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ett fel uppstod: {str(e)}'))

    def get_puzzle_image(self, detail_url):
        try:
            self.stdout.write(f"Hämtar bild från: {detail_url}")
            response = requests.get(detail_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Hitta alla bilder i detaljlänkarna
            detail_links = soup.find_all('a', {'class': 'detail-link'})
            image_urls = []
            
            for link in detail_links:
                img = link.find('img')
                if img and 'src' in img.attrs:
                    image_url = urljoin(self.BASE_URL, img['src'])
                    image_urls.append(image_url)
                    self.stdout.write(f"Hittade bild: {image_url}")
            
            # Returnera första bilden eller None om ingen hittades
            if image_urls:
                return image_urls[0]
                
            self.stdout.write(self.style.WARNING(f'Ingen bild hittades på {detail_url}'))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Kunde inte hämta bild: {str(e)}'))
        return None

    def save_puzzle_images(self, puzzle, detail_url):
        try:
            response = requests.get(detail_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Hitta alla bilder i detaljlänkarna
            detail_links = soup.find_all('a', {'class': 'detail-link'})
            
            # Ta bort gamla bilder
            PuzzleImage.objects.filter(puzzle=puzzle).delete()
            
            # Spara nya bilder
            for i, link in enumerate(detail_links):
                img = link.find('img')
                if img and 'src' in img.attrs:
                    image_url = urljoin(self.BASE_URL, img['src'])
                    PuzzleImage.objects.create(
                        puzzle=puzzle,
                        image_url=image_url,
                        order=i
                    )
                    self.stdout.write(f"Sparade bild {i+1} för {puzzle.name_en}")
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Kunde inte spara bilder för {puzzle.name_en}: {str(e)}')) 