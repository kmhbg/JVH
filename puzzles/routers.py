from django.conf import settings

class PuzzleRouter:
    def db_for_read(self, model, **hints):
        if model._meta.model_name == 'userprofile' or model._meta.model_name == 'friendship':
            return 'default'
        if model._meta.app_label == 'puzzles':
            return 'puzzles_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.model_name == 'userprofile' or model._meta.model_name == 'friendship':
            return 'default'
        if model._meta.app_label == 'puzzles':
            return 'puzzles_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in ['userprofile', 'friendship']:
            return db == 'default'
        if app_label == 'puzzles':
            return db == 'puzzles_db'
        return db == 'default' 