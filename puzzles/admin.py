from django.contrib import admin
from .models import Puzzle, UserProfile, PuzzleOwnership, Friendship, PuzzleCompletion
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Användarprofil'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role')
    
    def get_role(self, obj):
        return obj.userprofile.get_role_display()
    get_role.short_description = 'Roll'

# Ta bort den separata registreringen av UserProfile
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Puzzle)
class PuzzleAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'product_number', 'pieces', 'manufacturer')
    search_fields = ('name_en', 'name_nl', 'product_number')
    list_filter = ('manufacturer', 'series')
    change_list_template = 'admin/puzzles/puzzle/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('puzzles/import/', self.import_puzzles_view, name='puzzles_puzzle_import-puzzles'),
        ]
        return my_urls + urls

    def import_puzzles_view(self, request):
        if not request.user.userprofile.is_admin():
            messages.error(request, 'Du har inte behörighet att importera pussel.')
            return redirect('admin:puzzles_puzzle_changelist')
            
        try:
            call_command('import_puzzles')
            messages.success(request, 'Pusselimporten har slutförts!')
        except Exception as e:
            messages.error(request, f'Ett fel uppstod under importen: {str(e)}')
        
        return redirect('admin:puzzles_puzzle_changelist')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = request.user.userprofile.is_admin()
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(PuzzleOwnership)
class PuzzleOwnershipAdmin(admin.ModelAdmin):
    list_display = ('puzzle', 'get_owner_name', 'missing_pieces', 'borrowed_by')
    list_filter = ('owner_id',)
    search_fields = ('puzzle__name_en', 'puzzle__product_number', 'borrowed_by')

    def get_owner_name(self, obj):
        return obj.owner.user.username
    get_owner_name.short_description = 'Ägare'
    get_owner_name.admin_order_field = 'owner_id'

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(PuzzleCompletion)
class PuzzleCompletionAdmin(admin.ModelAdmin):
    list_display = ('puzzle', 'get_user', 'completed_at')
    list_filter = ('user_id',)
    search_fields = ('puzzle__name_en',)

    def get_user(self, obj):
        try:
            user = User.objects.using('default').get(userprofile__id=obj.user_id)
            return user.username
        except User.DoesNotExist:
            return f"User ID: {obj.user_id}"
    get_user.short_description = 'Användare' 