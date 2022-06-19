'''
Tests for ingredients API
'''
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe
    )

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')

def create_user(email='test@example.com', password='testpass123'):
    '''create and return new user'''
    return get_user_model().objects.create_user(email=email, password=password)

def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])

def create_recipe(user,**kwargs):
    '''Create and return a new recipe'''
    defaults = {
        'title':'Sample recipe',
        'time_minutes': 5,
        'price': Decimal('5.50'),
        'description': 'sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(kwargs)
    recipe = Recipe.objects.create(user=user,**defaults)
    return recipe

class PublicIngredientApiTest(TestCase):
    '''Test unauthenticated API requests'''
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientApiTest(TestCase):
    '''Test authenticated API requests'''
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        '''Test retrieving list of ingredient'''
        Ingredient.objects.create(user=self.user, name='Potato')
        Ingredient.objects.create(user=self.user, name='Tomato')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients,many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,serializer.data)

    def test_ingredient_limited_to_user(self):
        '''Test tags list limited to authenticated user'''
        other_user = create_user(
            email = 'user1@example.com',
            password = 'user1pass',
        )
        Ingredient.objects.create(user=other_user, name='Carrot')

        ingredient = Ingredient.objects.create(user=self.user, name= 'Lettuce')

        res = self.client.get(INGREDIENTS_URL)


        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data),1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'],ingredient.id)

    def test_update_ingredient(self):
        '''Test updating an ingredient'''
        ingredient = Ingredient.objects.create(user=self.user, name='Scallion')

        payload ={'name':'Onion'}
        url= detail_url(ingredient.id)
        res = self.client.patch(url,payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name='Quickmeal')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user= self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        '''Test listing ingredients by those assigned to recipes'''
        i1= Ingredient.objects.create(user=self.user,name='Chicken')
        i2 = Ingredient.objects.create(user=self.user,name='Basil')
        recipe = create_recipe(user=self.user,title="Thai Curry")
        recipe.ingredients.add(i1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(i1)
        s2 = IngredientSerializer(i2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        '''Test filtered ingredients return a unique list'''
        ing = Ingredient.objects.create(user=self.user,name='Chicken')
        Ingredient.objects.create(user=self.user,name='Basil')
        r1 = create_recipe(user=self.user, title="Thai Curry")
        r2 = create_recipe(user=self.user, title='Pad Thai')

        r1.ingredients.add(ing)
        r2.ingredients.add(ing)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data),1)



