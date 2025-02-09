from .models import Friendship, PuzzleBorrowRequest

def notifications(request):
    if request.user.is_authenticated:
        try:
            # Hämta väntande vänskapsförfrågningar
            pending_friend_requests = Friendship.objects.filter(
                receiver=request.user.userprofile,
                status='pending'
            )

            # Hämta väntande låneförfrågningar
            pending_borrow_requests = PuzzleBorrowRequest.objects.using('puzzles_db').filter(
                owner_id=request.user.userprofile.id,
                status='pending'
            )

            # Räkna totalt antal väntande förfrågningar
            total_pending = pending_friend_requests.count() + pending_borrow_requests.count()

            return {
                'pending_requests_count': total_pending,
                'pending_friend_requests': pending_friend_requests,
                'pending_borrow_requests': pending_borrow_requests
            }
        except Exception as e:
            # Om något går fel, returnera tomma värden
            return {
                'pending_requests_count': 0,
                'pending_friend_requests': [],
                'pending_borrow_requests': []
            }

    return {
        'pending_requests_count': 0,
        'pending_friend_requests': [],
        'pending_borrow_requests': []
    } 