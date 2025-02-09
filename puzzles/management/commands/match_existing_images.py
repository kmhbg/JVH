from django.core.management.base import BaseCommand
from puzzles.models import Puzzle, PuzzleImage
import os
from django.conf import settings
from django.core.files import File
import re

class Command(BaseCommand):
    help = 'Matchar befintliga bilder i media-mappen med pussel i databasen'

    def clean_product_number(self, filename):
        """Extrahera och rensa produktnummer från filnamn"""
        # Ta bort filändelse
        name = os.path.splitext(filename)[0]
        # Ta bort alla mellanslag och gör om till versaler
        name = name.strip().upper()
        # Ta bort eventuella JVH- prefix
        name = name.replace('JVH', '')
        # Ta bort alla icke-alfanumeriska tecken
        name = re.sub(r'[^A-Z0-9]', '', name)
        return name

    def handle(self, *args, **options):
        # Sökväg till puzzle_images-mappen
        images_dir = os.path.join(settings.MEDIA_ROOT, 'puzzle_images')
        
        if not os.path.exists(images_dir):
            self.stdout.write(self.style.WARNING(
                f'Mappen {images_dir} existerar inte.'
            ))
            return

        # Hämta alla pussel från databasen och skapa en uppslagstabell
        db_puzzles = {
            self.clean_product_number(puzzle.product_number): puzzle 
            for puzzle in Puzzle.objects.using('puzzles_db').all()
        }
        
        matches = 0
        
        # Gå igenom alla bildfiler i mappen
        for filename in os.listdir(images_dir):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            clean_number = self.clean_product_number(filename)
            if not clean_number:
                continue
            
            puzzle = db_puzzles.get(clean_number)
            if not puzzle:
                self.stdout.write(
                    f"Inget matchande pussel hittades för {filename} (rensat: {clean_number})"
                )
                continue
            
            # Kontrollera om pusslet redan har en bild
            if PuzzleImage.objects.using('puzzles_db').filter(
                puzzle=puzzle,
                uploaded_by_id=1
            ).exists():
                self.stdout.write(f"Bild finns redan för {clean_number}")
                continue
            
            try:
                # Skapa ny PuzzleImage
                image_path = os.path.join(images_dir, filename)
                with open(image_path, 'rb') as img_file:
                    puzzle_image = PuzzleImage(
                        puzzle=puzzle,
                        uploaded_by_id=1  # Admin user ID
                    )
                    puzzle_image.image.save(
                        filename,
                        File(img_file),
                        save=False
                    )
                    puzzle_image.save(using='puzzles_db')
                
                matches += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Bild matchad för {clean_number}"
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Fel vid import av bild {filename}: {str(e)}"
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'Bildmatchning klar! Matchade {matches} bilder'
        )) 