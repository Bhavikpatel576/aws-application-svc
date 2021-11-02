"""
Application add admin registrations.
"""
from django.conf.urls import url
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from application.models.acknowledgement import Acknowledgement
from application.models.customer import Customer
from application.models.disclosure import Disclosure
from application.models.floor_price import FloorPrice
from application.models.loan import Loan
from application.models.models import (Address, CurrentHome, Application)
from application.models.new_home_purchase import NewHomePurchase
from application.models.notification import Notification
from application.models.offer import Offer
from application.models.preapproval import PreApproval
from application.models.pricing import Pricing
from application.models.real_estate_agent import RealEstateAgent
from application.models.rent import Rent
from application.models.task import Task
from application.models.task_dependency import TaskDependency
from application.models.task_status import TaskStatus


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer')


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    readonly_fields = [
        'push_to_salesforce_button'
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<offer_id>.+)/push-to-salesforce/$',
                self.admin_site.admin_view(self.push_to_salesforce),
                name='push-to-salesforce',
            ),
        ]
        return custom_urls + urls

    def push_to_salesforce(self, request, offer_id, *args, **kwargs):
        Offer.objects.get(pk=offer_id).attempt_push_to_salesforce()
        url = reverse(
            'admin:application_offer_change',
            args=[offer_id],
            current_app=self.admin_site.name,
        )
        return HttpResponseRedirect(url)

    def push_to_salesforce_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Push to Salesforce</a>&nbsp;',
            reverse('admin:push-to-salesforce', args=[obj.pk]),
        )


@admin.register(Disclosure)
class DisclosureAdmin(admin.ModelAdmin):
    list_filter = ("disclosure_type", "buying_state", "selling_state")
    list_display = ("name", "disclosure_type", "buying_state", "selling_state", "product_offering", "active")
    fieldsets = (
        (None, {"fields": ("name", "disclosure_type", "document_url", "buying_state", "selling_state",
                           "buying_agent_brokerage", "product_offering", "active")}),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_filter = ("category", "active", "state")
    list_display = ("name", "category", "active", "state")


admin.site.register(Customer)
admin.site.register(Address)
admin.site.register(FloorPrice)
admin.site.register(CurrentHome)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Acknowledgement)
admin.site.register(RealEstateAgent)
admin.site.register(Loan)
admin.site.register(NewHomePurchase)
admin.site.register(Notification)
admin.site.register(PreApproval)
admin.site.register(Pricing)
admin.site.register(Rent)
admin.site.register(TaskDependency)
admin.site.register(TaskStatus)
