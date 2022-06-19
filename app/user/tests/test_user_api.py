'''
Test for user api
'''

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_RUL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')

def create_user(**kwarg):
    '''create and return new user'''
    return get_user_model().objects.create_user(**kwarg)

class PublicUserApiTest(TestCase):
    '''test public features of user API'''

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        '''Test creating new user is successful'''
        payload = {
            'email':'test@example.com',
            'password':'testpass123',
            'name': 'TestName'
        }
        res = self.client.post(CREATE_USER_RUL,payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password',res.data)

    def test_user_with_email_exits_error(self):
        '''Test error if creating already existed user'''
        payload = {
            'email':'test@example.com',
            'password':'testpass123',
            'name': 'TestName'
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_RUL,payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        '''Test if password is less than 5 characters error'''
        payload = {
            'email':'test@example.com',
            'password':'t123',
            'name': 'TestName'
        }
        res = self.client.post(CREATE_USER_RUL,payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        '''Test generates token for valid credentials'''
        user_details = {
            'email':'test@example.com',
            'password':'test-pass-123',
            'name': 'TestName'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        '''Test invalid credentials errors'''
        user_details = {
            'email':'test@example.com',
            'password':'goodpass123',
            'name': 'TestName'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': 'wrongpass123'
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_pass(self):
        ''' Test blank password error'''
        user_details = {
            'email':'test@example.com',
            'password':'goodpass123',
            'name': 'TestName'
        }
        create_user(**user_details)
        payload = {
            'email': user_details['email'],
            'password': ''
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        '''Test authentication is required for user'''
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateUserApiTest(TestCase):
    '''Test API requests that require authentication'''
    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='test-pass-123',
            name= 'TestName',
        )
        self.client = APIClient()
        self.client.force_authenticate(user = self.user)

    def test_retrieve_profile_success(self):
        '''Test retrieving profile for logged in user'''
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,{
            'name':self.user.name,
            'email': self.user.email,
        }
        )

    def test_post_me_not_allowed(self):
        '''Test POST is not allowed for the me endpoint'''
        res = self.client.post(ME_URL,{})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        '''Test updating the user profile'''
        payload = {
            'name':'New Name',
            'password': 'newpass123',
        }

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)