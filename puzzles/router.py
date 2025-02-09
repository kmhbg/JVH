class PuzzleRouter:
    """
    Router för att dirigera pussel-relaterade modeller till puzzles.db
    """
    puzzle_apps = {'puzzles'}
    puzzle_models = {
        'puzzle',
        'puzzleimage',
        'puzzleborrowhistory',
        'puzzleownership',
        'puzzlecompletion'
    }

    def db_for_read(self, model, **hints):
        model_name = model._meta.model_name.lower()
        if model_name in self.puzzle_models:
            return 'puzzles_db'
        return 'default'

    def db_for_write(self, model, **hints):
        model_name = model._meta.model_name.lower()
        if model_name in self.puzzle_models:
            return 'puzzles_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Tillåt relationer mellan databaserna
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name and model_name.lower() in self.puzzle_models:
            return db == 'puzzles_db'
        return db == 'default' 