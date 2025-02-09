from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.userprofile.is_admin():
            messages.error(request, 'Du har inte behörighet att komma åt denna sida.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view 