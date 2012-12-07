from django.views.generic.list import ListView
from django.http import HttpResponse
from ldap_mon import models


PER_PAGE = 25


class Log(ListView):

    model = models.Log
    template = 'log_list.html'
    paginate_by = PER_PAGE


def crashme(request):
    if request.user.is_superuser:
        raise RuntimeError("Crashing, as requested.")
    else:
        return HttpResponse("Must be administrator.")
