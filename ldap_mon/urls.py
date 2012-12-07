from django.conf.urls import patterns, include, url
from . import views

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'ldap_mon.views.home', name='home'),
    # url(r'^ldap_mon/', include('ldap_mon.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^crashme$', views.crashme),
    url(r'^fetch_and_parse$', views.fetch_and_parse),
)
