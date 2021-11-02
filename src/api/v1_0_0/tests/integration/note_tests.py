"""
Note app test cases.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from application.models.models import Note

from api.v1_0_0.tests._utils.data_generators import get_fake_note
from api.v1_0_0.tests.integration.mixins import AuthMixin


def raise_exception(*args, **kwargs):
    raise Exception('Invalid data.')


class NoteTestCase(AuthMixin, APITestCase):

    def create_note(self):
        """
        to create note for testing
        """
        url = "/api/1.0.0/notes/"
        application = self.create_application('fakeapplicant')

        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        note = get_fake_note(application.id)

        _ = self.client.post(url, note, **headers, format='json')
        note = Note.objects.first()
        return headers, note

    def test_list_notes_without_login(self):
        """
        To test if get api supports authentication.
        """
        url = '/api/1.0.0/notes/'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_notes_without_login(self):
        """
        To test if post api supports authentication.
        """
        url = "/api/1.0.0/notes/"
        application = self.create_application('fakeapplicant')

        note = get_fake_note(str(application.id))
        response = self.client.post(url, note, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_notes_without_mandatory_field(self):
        """
        To check if api raise error if mandatory fields are note provided.
        """

        url = "/api/1.0.0/notes/"

        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, {
        }, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['title'][0], 'This field is required.')
        self.assertEqual(response.data['note'][0], 'This field is required.')
        self.assertEqual(response.data['application'][0], 'This field is required.')

    def test_create_notes_with_login(self):
        """
        To test if note is been created correctly with provided data.
        """
        url = "/api/1.0.0/notes/"

        application = self.create_application('fakeapplicant')

        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        note = get_fake_note(application.id)

        response = self.client.post(url, note, **headers, format='json')
        created_note = Note.objects.select_related('application').all()[0]
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created_note.title, note['title'])
        self.assertEqual(created_note.note, note['note'])
        self.assertEqual(created_note.application.id, note['application'])

    def test_create_notes_as_user(self):
        """
        To test if note is been created correctly with provided data.
        """
        url = "/api/1.0.0/notes/"

        application = self.create_application('fakeapplicant')

        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        note = get_fake_note(application.id)

        response = self.client.post(url, note, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_notes_with_login(self):
        """
        To test if list note api is working correctly.
        """
        url = "/api/1.0.0/notes/"
        headers, _ = self.create_note()
        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_notes_as_user(self):
        """
        To test if list note api is working correctly.
        """
        url = "/api/1.0.0/notes/"
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_note_with_author(self):
        """
        To test note is editable to author user
        """
        url = '/api/1.0.0/notes/'
        headers, note = self.create_note()

        response = self.client.patch("{}{}/".format(url, note.id), {"title": "new Fake note title"}, **headers,
                                     format='json')
        note = Note.objects.first()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(note.title, "new Fake note title")

    def test_update_note_with_user(self):
        """
        To test note is editable to author user
        """
        url = '/api/1.0.0/notes/'
        _, note = self.create_note()

        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.patch("{}{}/".format(url, note.id), {"title": "new Fake note title"}, **headers,
                                     format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_note_with_other_than_author(self):
        """
        To test note is note editable to user other than author
        """
        url = '/api/1.0.0/notes/'

        token = self.create_and_login_admin('fakeloginadmin2')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        _, note = self.create_note()

        response = self.client.patch("{}{}/".format(url, note.id), {"title": "new Fake note title"}, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_note_with_author(self):
        """
        To test if author can delete his note
        """
        url = '/api/1.0.0/notes/'
        headers, note = self.create_note()
        response = self.client.delete("{}{}/".format(url, note.id), **headers, format="json")
        note_count = Note.objects.count()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(note_count, 0)

    def test_delete_note_with_user(self):
        """
        To test if author can delete his note
        """
        url = '/api/1.0.0/notes/'
        _, note = self.create_note()

        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.delete("{}{}/".format(url, note.id), **headers, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_note_with_other_than_author(self):
        """
        To test if user other than authan can delete note or not.
        """
        url = '/api/1.0.0/notes/'
        headers, note = self.create_note()

        token = self.create_and_login_admin('fakeloginadmin2')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.delete("{}{}/".format(url, note.id), **headers, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
