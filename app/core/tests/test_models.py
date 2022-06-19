'''
Test for models
'''

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch

from core import models

def create_user(email='test@example.com',password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)

class ModelTests(TestCase):
    ''' Test Models '''
    def test_create_user_with_email(self):
        ''' Test if user created successfully with email'''
        email ="test@example.com"
        password = "password123"
        user = create_user(
            email = email,
            password = password
        )

        self.assertEqual(user.email,email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        ''' Test if email normalized for new user'''
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com']
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_email_required(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('','sample123')

    def test_create_superuser(self):
        '''Test creating new superuser'''
        user = get_user_model().objects.create_superuser(
            email= 'test@example.com',
            password = 'sample123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        '''Test creating a recipe is successful'''
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123'
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title = 'Sample Recipe',
            time_minutes=5,
            price=Decimal('5.50'),
            description = 'Sample description',
        )
        self.assertEqual(str(recipe),recipe.title)

    def test_create_tag(self):
        '''Test if tag is created'''
        user = create_user()
        tag = models.Tag.objects.create(user=user,name='TestTag')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        '''Test creating ingredient successful'''
        user = create_user()
        ingredient = models.Ingredient.objects.create(user=user,name='TestIngredient')

        self.assertEqual(str(ingredient), ingredient.name)

    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        '''Test generating image path'''
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')