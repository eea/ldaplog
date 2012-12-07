from functools import wraps
from django.views.generic.list import ListView
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
def fetch_and_parse(request):
    if not request.POST:
        return HttpResponse("Call me with POST.")
    if request.POST.get('key') != settings.CRON_KEY:
        return HttpResponse("Invalid key.")
    remove = bool(request.POST.get('remove') == 'on')
    models.fetch_and_parse(remove)
    return HttpResponse("Done.")
