class PuzzleRouter:
    """
    Router för att dirigera pussel-relaterade modeller till puzzles.db
    """
    puzzle_apps = {'puzzles'}
    puzzle_models = {'puzzle', 'puzzleimage', 'puzzleborrowhistory'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.puzzle_apps and \
           model._meta.model_name in self.puzzle_models:
            return 'puzzles_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.puzzle_apps and \
           model._meta.model_name in self.puzzle_models:
            return 'puzzles_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Tillåt relationer mellan modeller i samma databas
        if obj1._meta.app_label == obj2._meta.app_label:
            return True
        # Tillåt relationer mellan pussel och användarrelaterade modeller
        if obj1._meta.app_label in self.puzzle_apps or \
           obj2._meta.app_label in self.puzzle_apps:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.puzzle_apps and \
           model_name in self.puzzle_models:
            return db == 'puzzles_db'
        return db == 'default' 