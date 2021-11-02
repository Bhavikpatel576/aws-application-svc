from django.core.management.base import BaseCommand

from application.models.offer import Offer


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save new home purchase on offer',
        )

    def handle(self, *args, **options):
        """
        Only need to check offers that are won. Rent and earnest deposit percentage are used off the loan
        until the application reaches post option. That only happens when offers are won.
        """

        total_count = 0
        addresses_no_match = 0
        no_nhp_address = 0
        no_offer_property_address = 0
        new_home_purchase_saved = 0

        offers = Offer.objects.filter(status__in=['Won', 'Cancelled', 'Contract Cancelled'])\
            .exclude(application__stage='Trash')\
            .exclude(application__new_home_purchase__isnull=True)\
            .exclude(new_home_purchase__isnull=False)

        for offer in offers:
            total_count += 1
            nhp = offer.application.new_home_purchase

            if nhp.address and nhp.address.street:
                nhp_street = nhp.address.street.lower()
            else:
                nhp_street = None

            if offer.offer_property_address and offer.offer_property_address.street:
                offer_street = offer.offer_property_address.street.lower()
            else:
                offer_street = None

            if nhp_street and offer_street:
                if nhp_street not in offer_street and offer_street not in nhp_street:
                    # mostly cancelled or contract cancelled records
                    addresses_no_match += 1
                    print(f'Addresses dont match. NHP street: {nhp_street} Offer street: {offer_street} Offer ID: {offer.id} Offer status: {offer.status}')
                    continue

            if nhp_street and not offer_street:
                no_offer_property_address += 1
                print(f'No offer property address. Offer id {offer.id} Offer status: {offer.status}')
                continue

            if not nhp_street and offer_street:
                no_nhp_address += 1
                print(f'No new home purchase address. NHP id {nhp.id} Offer status: {offer.status}')
                continue

            new_home_purchase_saved += 1
            print('New home purchase saved')

            if options['save']:
                offer.new_home_purchase = nhp
                offer.save()

        print('--------------------------------------------')
        print(f'Addresses dont match: {addresses_no_match}')
        print(f'No offer property address: {no_offer_property_address}')
        print(f'No new home purchase address: {no_nhp_address}')
        print(f'New home purchase saved: {new_home_purchase_saved}')
        print('--------------------------------------------')
        print(f'Total count: {total_count}')
