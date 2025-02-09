from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Puzzle, UserProfile, PuzzleOwnership, Friendship, PuzzleBorrowHistory, PuzzleImage
from .forms import PuzzleSearchForm, UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, PuzzleOwnershipForm, FriendRequestForm, PuzzleBorrowForm, PuzzleImageUploadForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.management import call_command
from .decorators import admin_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import connections

@login_required
def puzzle_list(request):
    search_query = request.GET.get('search', '')
    puzzles = Puzzle.objects.using('puzzles_db').all()
    
    if search_query:
        puzzles = puzzles.filter(
            Q(name_en__icontains=search_query) |
            Q(product_number__icontains=search_query)
        )
    
    return render(request, 'puzzles/puzzle_list.html', {
        'puzzles': puzzles,
        'search_query': search_query
    })

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Din profil har uppdaterats!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.userprofile)
    
    return render(request, 'puzzles/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
def toggle_owned(request, puzzle_id):
    if request.method == 'POST':
        puzzle = get_object_or_404(Puzzle, id=puzzle_id)
        profile = request.user.userprofile
        is_owned = puzzle in profile.owned_puzzles.all()
        
        if is_owned:
            profile.owned_puzzles.remove(puzzle)
        else:
            profile.owned_puzzles.add(puzzle)
        
        return JsonResponse({
            'status': 'success',
            'is_owned': not is_owned
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def toggle_completed(request, puzzle_id):
    if request.method == 'POST':
        puzzle = get_object_or_404(Puzzle, id=puzzle_id)
        profile = request.user.userprofile
        is_completed = puzzle in profile.completed_puzzles.all()
        
        if is_completed:
            profile.completed_puzzles.remove(puzzle)
        else:
            profile.completed_puzzles.add(puzzle)
        
        return JsonResponse({
            'status': 'success',
            'is_completed': not is_completed
        })
    return JsonResponse({'status': 'error'}, status=400)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('puzzle_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    profile = request.user.userprofile
    total_puzzles = Puzzle.objects.count()
    owned_count = profile.owned_puzzles.count()
    completed_count = profile.completed_puzzles.count()
    
    # Hämta pussel med utlåningsinformation
    recent_puzzles = profile.owned_puzzles.all().prefetch_related(
        'puzzleownership_set'
    )[:5]
    
    context = {
        'total_puzzles': total_puzzles,
        'owned_count': owned_count,
        'completed_count': completed_count,
        'owned_percentage': round((owned_count / total_puzzles) * 100 if total_puzzles > 0 else 0, 1),
        'completed_percentage': round((completed_count / total_puzzles) * 100 if total_puzzles > 0 else 0, 1),
        'recent_puzzles': recent_puzzles
    }
    return render(request, 'puzzles/dashboard.html', context)

@login_required
def puzzle_detail(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle, id=puzzle_id)
    ownership = None
    borrow_form = None
    image_form = PuzzleImageUploadForm()
    
    if puzzle in request.user.userprofile.owned_puzzles.all():
        ownership = PuzzleOwnership.objects.filter(
            puzzle=puzzle, 
            owner=request.user.userprofile
        ).first()
        
        if request.method == 'POST':
            if 'return_puzzle' in request.POST:
                # Hantera återlämning
                if ownership.borrowed_by:
                    PuzzleBorrowHistory.objects.create(
                        puzzle_ownership=ownership,
                        borrowed_by=ownership.borrowed_by,
                        borrowed_date=ownership.borrowed_date,
                        returned_date=timezone.now().date()
                    )
                    ownership.borrowed_by = ''
                    ownership.borrowed_date = None
                    ownership.return_date = None
                    ownership.save()
                    messages.success(request, 'Pusslet har markerats som återlämnat!')
            
            elif 'upload_image' in request.POST:
                # Hantera bilduppladdning
                image_form = PuzzleImageUploadForm(request.POST, request.FILES)
                if image_form.is_valid():
                    image = image_form.save(commit=False)
                    image.puzzle = puzzle
                    image.uploaded_by = request.user.userprofile
                    image.save()
                    messages.success(request, 'Bilden har laddats upp!')
            
            else:
                # Hantera utlåning
                borrow_form = PuzzleBorrowForm(request.POST, instance=ownership)
                if borrow_form.is_valid():
                    ownership = borrow_form.save(commit=False)
                    ownership.puzzle = puzzle
                    ownership.owner = request.user.userprofile
                    ownership.save()
                    messages.success(request, 'Utlåningsinformation har uppdaterats!')
        else:
            borrow_form = PuzzleBorrowForm(instance=ownership)

    # Hämta lånehistorik och användaruppladdade bilder
    borrow_history = PuzzleBorrowHistory.objects.filter(puzzle_ownership=ownership) if ownership else []
    user_images = puzzle.user_images.all()

    return render(request, 'puzzles/puzzle_detail.html', {
        'puzzle': puzzle,
        'ownership': ownership,
        'borrow_form': borrow_form,
        'image_form': image_form,
        'borrow_history': borrow_history,
        'user_images': user_images,
        'is_owned': puzzle in request.user.userprofile.owned_puzzles.all()
    })

@login_required
def friends_list(request):
    user_profile = request.user.userprofile
    friends = Friendship.objects.filter(
        (Q(sender=user_profile) | Q(receiver=user_profile)),
        status='accepted'
    )
    pending_requests = Friendship.objects.filter(
        receiver=user_profile,
        status='pending'
    )
    
    if request.method == 'POST':
        form = FriendRequestForm(request.POST)
        if form.is_valid():
            try:
                friend = User.objects.get(username=form.cleaned_data['username']).userprofile
                if friend != user_profile:
                    Friendship.objects.create(sender=user_profile, receiver=friend)
                    messages.success(request, 'Vänskapsförfrågan skickad!')
                else:
                    messages.error(request, 'Du kan inte skicka en vänskapsförfrågan till dig själv.')
            except User.DoesNotExist:
                messages.error(request, 'Användaren hittades inte.')
    else:
        form = FriendRequestForm()
    
    return render(request, 'puzzles/friends_list.html', {
        'friends': friends,
        'pending_requests': pending_requests,
        'form': form
    })

@login_required
def handle_friend_request(request, friendship_id):
    friendship = get_object_or_404(Friendship, id=friendship_id, receiver=request.user.userprofile)
    action = request.POST.get('action')
    
    if action == 'accept':
        friendship.status = 'accepted'
        friendship.save()
        messages.success(request, 'Vänskapsförfrågan accepterad!')
    elif action == 'reject':
        friendship.status = 'rejected'
        friendship.save()
        messages.success(request, 'Vänskapsförfrågan avvisad.')
    
    return redirect('friends_list')

@login_required
@admin_required
def trigger_import(request):
    if request.method == 'POST':
        try:
            call_command('import_puzzles')
            messages.success(request, 'Pusselimporten har slutförts!')
        except Exception as e:
            messages.error(request, f'Ett fel uppstod under importen: {str(e)}')
    return redirect('admin_dashboard')

@login_required
@admin_required
def admin_dashboard(request):
    return render(request, 'puzzles/admin_dashboard.html') 