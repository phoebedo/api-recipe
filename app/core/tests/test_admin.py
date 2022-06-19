'''Test Django admin customization'''

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class AdminSiteTests(TestCase):
    '''Test Django admin'''
    def setUp(self):
        ''' Create user and client'''
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password = 'adminsample123'
        )
        self.client.force_login(self.admin_user)

        self.user = get_user_model().objects.create_user(
            email = "user@example.com",
            password = "usersample123",
            name = "Test User"
        )

    def test_users_list(self):
        '''Test if users listed on page'''
        url = reverse('admin:core_user_changelist')
        res = self.client.get(url)

        self.assertContains(res,self.user.name)
        self.assertContains(res,self.user.email)

    def test_edit_user_page(self):
        '''Test customized user page'''
        url = reverse('admin:core_user_change', args=[self.user.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code,200)

    def test_create_user_page(self):
        '''Test create user page'''
        url = reverse('admin:core_user_add')
        res=self.client.get(url)

        self.assertEqual(res.status_code,200)

