from django.core.management.base import BaseCommand

from application.models.application import Application


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save reassigned contract on new home purchase',
        )

    def handle(self, *args, **options):
        apps = Application.objects.filter(new_home_purchase__isnull=False, is_reassigned_contract=True)

        for app in apps:
            app.new_home_purchase.is_reassigned_contract = app.is_reassigned_contract
            if options['save']:
                app.new_home_purchase.save()

        print('--------------------------------------------')
        print(f'Total count: {len(apps)}')
