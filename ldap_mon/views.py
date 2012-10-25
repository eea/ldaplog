from django.views.generic.list import ListView
from ldap_mon import models


PER_PAGE = 25


class Log(ListView):

    model = models.Log
    template = 'log_list.html'
    paginate_by = PER_PAGE