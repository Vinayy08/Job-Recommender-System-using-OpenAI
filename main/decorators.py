from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render

def employee_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'employee':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You are not authorized to access this page.")
    return _wrapped_view

def employer_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        print("Request user:", request.user)
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'employer':
            print("User role is not 'employer'")
            return render(request, 'main/error.html', {"error_message": "You are not authorized to access this page."})
        print("User is authorized as employer")
        return view_func(request, *args, **kwargs)
    return _wrapped_view