from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Puzzle, UserProfile, PuzzleOwnership, Friendship, PuzzleBorrowHistory, PuzzleImage, PuzzleCompletion, PuzzleBorrowRequest
from .forms import PuzzleSearchForm, UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, PuzzleOwnershipForm, FriendRequestForm, PuzzleBorrowForm, PuzzleImageUploadForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.management import call_command
from .decorators import admin_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import connections
import pandas as pd
from io import BytesIO
from datetime import datetime

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
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'is_completed': is_completed,
                'message': message
            })
        else:
            messages.success(request, message)
            return redirect('puzzle_detail', puzzle_id=puzzle_id)
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
    previously_owned_puzzles = profile.previously_owned_puzzles
    owned_count = owned_puzzles.count()
    completed_puzzles = profile.completed_puzzles
    completed_count = completed_puzzles.count()
    
    # Räkna ut procent av alla pussel
    total_owned_ever = owned_count + previously_owned_puzzles.count()
    owned_percentage = round((owned_count / total_puzzles) * 100 if total_puzzles > 0 else 0, 1)
    completed_percentage = round((completed_count / total_puzzles) * 100 if total_puzzles > 0 else 0, 1)
    
    context = {
        'total_puzzles': total_puzzles,
        'owned_count': owned_count,
        'owned_puzzles': owned_puzzles,
        'previously_owned_puzzles': previously_owned_puzzles,
        'completed_count': completed_count,
        'completed_puzzles': completed_puzzles,
        'owned_percentage': owned_percentage,
        'completed_percentage': completed_percentage,
        'total_owned_ever': total_owned_ever
    }
    return render(request, 'puzzles/dashboard.html', context)

@login_required
def puzzle_detail(request, puzzle_id):
    puzzle = get_object_or_404(Puzzle.objects.using('puzzles_db'), id=puzzle_id)
    ownership = None
    borrow_form = None
    image_form = PuzzleImageUploadForm()
    borrow_history = []
    
    try:
        ownership = PuzzleOwnership.objects.using('puzzles_db').filter(
            puzzle=puzzle,
            owner_id=request.user.userprofile.id
        ).first()
        
        if ownership:
            if request.method == 'POST':
                if 'return_puzzle' in request.POST:
                    if ownership.borrowed_by:
                        # Skapa lånehistorik
                        PuzzleBorrowHistory.objects.using('puzzles_db').create(
                            puzzle_ownership=ownership,
                            borrowed_by=ownership.borrowed_by,
                            borrowed_date=ownership.borrowed_date,
                            returned_date=timezone.now().date()
                        )
                        
                        # Återställ utlåningsinformation
                        ownership.borrowed_by = ''
                        ownership.borrowed_date = None
                        ownership.save(using='puzzles_db')
                        
                        messages.success(request, 'Pusslet har markerats som återlämnat!')
                        return redirect('puzzle_detail', puzzle_id=puzzle_id)
                
                elif 'upload_image' in request.POST:
                    image_form = PuzzleImageUploadForm(request.POST, request.FILES)
                    if image_form.is_valid():
                        image = image_form.save(commit=False)
                        image.puzzle = puzzle
                        image.uploaded_by_id = request.user.userprofile.id
                        image.save(using='puzzles_db')
                        messages.success(request, 'Bilden har laddats upp!')
                        return redirect('puzzle_detail', puzzle_id=puzzle_id)
                
                else:
                    # Hantera utlåning
                    borrow_form = PuzzleBorrowForm(request.POST, instance=ownership)
                    if borrow_form.is_valid():
                        ownership = borrow_form.save(commit=False)
                        ownership.puzzle = puzzle
                        ownership.owner_id = request.user.userprofile.id
                        ownership.save(using='puzzles_db')
                        messages.success(request, 'Utlåningsinformation har uppdaterats!')

            # Hämta lånehistorik för ägaren
            if request.user.userprofile.id == ownership.owner_id:
                borrow_history = PuzzleBorrowHistory.objects.using('puzzles_db').filter(
                    puzzle_ownership=ownership
                ).order_by('-borrowed_date')

    except Exception as e:
        messages.error(request, f'Ett fel uppstod: {str(e)}')
    
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
            messages.success(request, 'Pusselimport genomförd!')
        except Exception as e:
            messages.error(request, f'Ett fel uppstod: {str(e)}')
        return redirect('admin_dashboard')
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def trigger_match_images(request):
    if request.method == 'POST':
        try:
            call_command('match_existing_images')
            messages.success(request, 'Bildmatchning genomförd!')
        except Exception as e:
            messages.error(request, f'Ett fel uppstod: {str(e)}')
        return redirect('admin_dashboard')
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def admin_dashboard(request):
    return render(request, 'puzzles/admin_dashboard.html')

@login_required
def friend_puzzles(request, friend_id):
    friend = get_object_or_404(UserProfile, id=friend_id)
    
    # Kontrollera att användarna är vänner
    if not Friendship.objects.filter(
        (Q(sender=request.user.userprofile, receiver=friend) | 
         Q(sender=friend, receiver=request.user.userprofile)),
        status='accepted'
    ).exists():
        messages.error(request, 'Du måste vara vän med användaren för att se deras pussel.')
        return redirect('friends_list')
    
    owned_puzzles = friend.owned_puzzles  # Använder den uppdaterade property:n som filtrerar på status='owned'
    return render(request, 'puzzles/friend_puzzles.html', {
        'friend': friend,
        'owned_puzzles': owned_puzzles
    })

@login_required
def request_borrow(request, puzzle_id):
    if request.method == 'POST':
        puzzle = get_object_or_404(Puzzle.objects.using('puzzles_db'), id=puzzle_id)
        
        # Hämta ägarskap för den specifika ägaren från URL:en eller request data
        owner_id = request.GET.get('owner_id') or request.POST.get('owner_id')
        if not owner_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Ingen ägare specificerad.'
            })
            
        ownership = get_object_or_404(
            PuzzleOwnership.objects.using('puzzles_db'), 
            puzzle=puzzle,
            owner_id=owner_id
        )
        
        # Kontrollera att pusslet inte redan är utlånat
        if ownership.borrowed_by:
            return JsonResponse({
                'status': 'error',
                'message': 'Pusslet är redan utlånat.'
            })
        
        # Skapa låneförfrågan och spara i puzzles_db
        borrow_request = PuzzleBorrowRequest(
            puzzle=puzzle,
            requester_id=request.user.userprofile.id,  # Använd ID istället för objekt
            owner_id=int(owner_id),                    # Konvertera till int för säkerhets skull
            status='pending'
        )
        borrow_request.save(using='puzzles_db')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Låneförfrågan har skickats!'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Ogiltig förfrågan'})

def get_context_data(request):
    if request.user.is_authenticated:
        pending_requests = Friendship.objects.filter(
            receiver=request.user.userprofile,
            status='pending'
        )
        return {
            'pending_requests_count': pending_requests.count(),
            'pending_friend_requests': pending_requests
        }
    return {}

@login_required
def handle_borrow_request(request, request_id):
    # Använd owner_id istället för owner
    borrow_request = get_object_or_404(
        PuzzleBorrowRequest.objects.using('puzzles_db'), 
        id=request_id, 
        owner_id=request.user.userprofile.id
    )
    
    action = request.POST.get('action')
    
    if action == 'accept':
        borrow_request.status = 'accepted'
        borrow_request.save(using='puzzles_db')
        
        # Uppdatera PuzzleOwnership
        ownership = PuzzleOwnership.objects.using('puzzles_db').get(
            puzzle=borrow_request.puzzle,
            owner_id=request.user.userprofile.id
        )
        ownership.borrowed_by = borrow_request.requester.user.username
        ownership.borrowed_date = timezone.now().date()
        ownership.save(using='puzzles_db')
        
        messages.success(request, f'Du har lånat ut pusslet till {borrow_request.requester.get_full_name()}')
    elif action == 'reject':
        borrow_request.status = 'rejected'
        borrow_request.save(using='puzzles_db')
        messages.success(request, 'Låneförfrågan har avvisats')
    
    return redirect('dashboard')

@login_required
def delete_puzzle_image(request, image_id):
    image = get_object_or_404(PuzzleImage.objects.using('puzzles_db'), id=image_id)
    
    # Kontrollera att användaren äger bilden
    if image.uploaded_by_id == request.user.userprofile.id:
        puzzle_id = image.puzzle.id
        image.delete()
        messages.success(request, 'Bilden har raderats!')
        return redirect('puzzle_detail', puzzle_id=puzzle_id)
    else:
        messages.error(request, 'Du har inte behörighet att radera denna bild.')
        return redirect('puzzle_detail', puzzle_id=image.puzzle.id)

@login_required
def mark_puzzle_sold(request, puzzle_id):
    if request.method == 'POST':
        ownership = get_object_or_404(
            PuzzleOwnership.objects.using('puzzles_db'),
            puzzle_id=puzzle_id,
            owner_id=request.user.userprofile.id
        )
        ownership.status = 'previously_owned' if ownership.status == 'owned' else 'owned'
        ownership.save(using='puzzles_db')
        
        status_text = 'sålt' if ownership.status == 'previously_owned' else 'ägt igen'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'Pusslet har markerats som {status_text}'
            })
        else:
            messages.success(request, f'Pusslet har markerats som {status_text}')
            return redirect('puzzle_detail', puzzle_id=puzzle_id)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def remove_puzzle(request, puzzle_id):
    if request.method == 'POST':
        ownership = get_object_or_404(
            PuzzleOwnership.objects.using('puzzles_db'),
            puzzle_id=puzzle_id,
            owner_id=request.user.userprofile.id
        )
        ownership.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Pusslet har tagits bort från din samling'
            })
        else:
            messages.success(request, 'Pusslet har tagits bort från din samling')
            return redirect('dashboard')
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def export_puzzles(request):
    puzzles = PuzzleOwnership.objects.using('puzzles_db').filter(owner_id=request.user.id)
    
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
    
    # Skapa Excel-fil i minnet
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    # Skapa filnamn med användarnamn och datum
    filename = f'pussel_{request.user.username}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    # Skapa HTTP-response med Excel-filen
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response 