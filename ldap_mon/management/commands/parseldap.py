from optparse import make_option
from django.core.management.base import BaseCommand
from ldap_mon.models import fetch_and_parse


class Command(BaseCommand):
    help = "Fetch new log entries from the database."
    option_list = BaseCommand.option_list + (
        make_option('-r', '--remove',
                    action='store_true', dest='remove', default=False,
                    help="Remove old log entries."),
    )

    def handle(self, *args, **options):
        fetch_and_parse(options['remove'])
