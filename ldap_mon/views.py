from functools import wraps
from django.views.generic.list import ListView
from django.http import HttpResponse
from ldap_mon import models


PER_PAGE = 25


class Log(ListView):

    model = models.Log
    template = 'log_list.html'
    paginate_by = PER_PAGE


def admin_only(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponse("Must be administrator.")
        return view(request, *args, **kwargs)
    return wrapper


@admin_only
def crashme(request):
    raise RuntimeError("Crashing, as requested.")
