from django.conf import settings
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

class HomewardOauthClient:
    def __init__(self):
        homeward_oauth_base_endpoint = settings.HOMEWARD_OAUTH_BASE_URL
        client_id = settings.APPLICATION_SERVICE_CLIENT_ID
        client_secret = settings.APPLICATION_SERVICE_CLIENT_SECRET

        oauth = OAuth2Session(client=BackendApplicationClient(client_id))
        token = oauth.fetch_token(token_url=f"{homeward_oauth_base_endpoint}o/token/", client_id=client_id,
                                  client_secret=client_secret)

        self.client = OAuth2Session(client_id, token=token)
