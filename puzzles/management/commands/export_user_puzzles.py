from django.core.management.base import BaseCommand
import pandas as pd
from puzzles.models import PuzzleOwnership
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Exporterar en lista på alla pussel en användare äger till Excel'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Användarnamnet vars pussel ska exporteras')
        parser.add_argument('output', type=str, help='Sökväg till Excel-filen som ska skapas')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
            puzzles = PuzzleOwnership.objects.using('puzzles_db').filter(owner_id=user.id)
            
            data = []
            for ownership in puzzles:
                puzzle = ownership.puzzle
                data.append({
                    'Namn (EN)': puzzle.name_en,
                    'Namn (NL)': puzzle.name_nl,
                    'Artikelnummer': puzzle.product_number,
                    'Serie': puzzle.series,
                    'Antal bitar': puzzle.pieces,
                    'Illustratör': puzzle.illustrator,
                    'Ägd sedan': ownership.owned_since.strftime('%Y-%m-%d') if ownership.owned_since else ''
                })
            
            df = pd.DataFrame(data)
            df.to_excel(options['output'], index=False)
            
            self.stdout.write(self.style.SUCCESS(
                f'Exporterade {len(data)} pussel till {options["output"]}'
            ))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Användaren {options["username"]} hittades inte'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ett fel uppstod: {str(e)}')) 