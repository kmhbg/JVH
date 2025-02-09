from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Puzzle, UserProfile, PuzzleOwnership, Friendship, PuzzleBorrowHistory, PuzzleImage, PuzzleCompletion
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
        puzzle = get_object_or_404(Puzzle.objects.using('puzzles_db'), id=puzzle_id)
        profile = request.user.userprofile
        ownership = PuzzleOwnership.objects.using('puzzles_db').filter(
            puzzle=puzzle, 
            owner_id=profile.id
        ).first()
        
        if ownership:
            ownership.delete()
            is_owned = False
            message = "Pusslet har tagits bort från din samling"
        else:
            PuzzleOwnership.objects.using('puzzles_db').create(
                puzzle=puzzle,
                owner_id=profile.id
            )
            is_owned = True
            message = "Pusslet har lagts till i din samling"
        
        return JsonResponse({
            'status': 'success',
            'is_owned': is_owned,
            'message': message
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def toggle_completed(request, puzzle_id):
    if request.method == 'POST':
        puzzle = get_object_or_404(Puzzle.objects.using('puzzles_db'), id=puzzle_id)
        profile = request.user.userprofile
        completion = PuzzleCompletion.objects.using('puzzles_db').filter(
            puzzle=puzzle,
            user_id=profile.id
        ).first()
        
        if completion:
            completion.delete()
            is_completed = False
            message = "Pusslet har markerats som opusslat"
        else:
            PuzzleCompletion.objects.using('puzzles_db').create(
                puzzle=puzzle,
                user_id=profile.id
            )
            is_completed = True
            message = "Pusslet har markerats som pusslat"
        
        return JsonResponse({
            'status': 'success',
            'is_completed': is_completed,
            'message': message
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
    total_puzzles = Puzzle.objects.using('puzzles_db').count()
    owned_puzzles = profile.owned_puzzles
    owned_count = owned_puzzles.count()
    
    recent_puzzles = owned_puzzles.prefetch_related(
        'puzzleownership_set'
    )[:5]
    
    context = {
        'total_puzzles': total_puzzles,
        'owned_count': owned_count,
        'recent_puzzles': recent_puzzles,
        'owned_percentage': round((owned_count / total_puzzles) * 100 if total_puzzles > 0 else 0, 1),
    }
    return render(request, 'puzzles/dashboard.html', context)

@login_required
def puzzle_detail(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle.objects.using('puzzles_db'), id=puzzle_id)
    ownership = None
    borrow_form = None
    image_form = PuzzleImageUploadForm()
    
    # Kontrollera ägarskap via PuzzleOwnership
    ownership = PuzzleOwnership.objects.using('puzzles_db').filter(
        puzzle=puzzle,
        owner_id=request.user.userprofile.id
    ).first()
    
    if ownership:
        if request.method == 'POST':
            if 'return_puzzle' in request.POST:
                # Hantera återlämning
                if ownership.borrowed_by:
                    PuzzleBorrowHistory.objects.using('puzzles_db').create(
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
                    image.save(using='puzzles_db')
                    messages.success(request, 'Bilden har laddats upp!')
            
            else:
                # Hantera utlåning
                borrow_form = PuzzleBorrowForm(request.POST, instance=ownership)
                if borrow_form.is_valid():
                    ownership = borrow_form.save(commit=False)
                    ownership.puzzle = puzzle
                    ownership.owner_id = request.user.userprofile.id
                    ownership.save(using='puzzles_db')
                    messages.success(request, 'Utlåningsinformation har uppdaterats!')
        else:
            borrow_form = PuzzleBorrowForm(instance=ownership)

    # Hämta lånehistorik och användaruppladdade bilder
    borrow_history = PuzzleBorrowHistory.objects.using('puzzles_db').filter(
        puzzle_ownership=ownership
    ) if ownership else []
    
    user_images = puzzle.user_images.using('puzzles_db').all()

    return render(request, 'puzzles/puzzle_detail.html', {
        'puzzle': puzzle,
        'ownership': ownership,
        'borrow_form': borrow_form,
        'image_form': image_form,
        'borrow_history': borrow_history,
        'user_images': user_images,
        'is_owned': ownership is not None
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