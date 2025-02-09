from django.core.management.base import BaseCommand
from puzzles.models import Puzzle

class Command(BaseCommand):
    help = 'Laddar exempel-pussel i databasen'

    def handle(self, *args, **kwargs):
        puzzles = [
            {
                'name_en': 'Food Festival',
                'name_nl': 'Foodfestival',
                'product_number': '19199',
                'series': 'JvH',
                'pieces': '1000',
                'illustrator': 'Jan van Haasteren',
                'publisher': 'Jumbo',
                'release_date': '2023',
                'manufacturer': 'Jumbo'
            },
            {
                'name_en': 'The Zoo',
                'name_nl': 'De Dierentuin',
                'product_number': '19198',
                'series': 'JvH',
                'pieces': '1000',
                'illustrator': 'Jan van Haasteren',
                'publisher': 'Jumbo',
                'release_date': '2023',
                'manufacturer': 'Jumbo'
            }
        ]

        for puzzle_data in puzzles:
            Puzzle.objects.get_or_create(**puzzle_data)
        
        self.stdout.write(self.style.SUCCESS('Exempel-pussel har lagts till i databasen')) 