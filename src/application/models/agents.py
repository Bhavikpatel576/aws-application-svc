from django.db import models
from application.models.real_estate_agent import RealEstateAgent


class Agents():
    def __init__(self, needs_buying_agent, needs_listing_agent, buying_agent, listing_agent):
        self.needs_buying_agent = needs_buying_agent
        self.needs_listing_agent = needs_listing_agent
        self.buying_agent = buying_agent
        self.listing_agent = listing_agent
    needs_buying_agent = models.BooleanField()
    needs_listing_agent = models.BooleanField()
    listing_agent = RealEstateAgent()
    buying_agent = RealEstateAgent()
