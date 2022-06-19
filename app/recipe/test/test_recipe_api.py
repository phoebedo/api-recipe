'''
Tests for recipe Api
'''
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    )

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    '''Create and return detail url'''
    return reverse('recipe:recipe-detail', args=[recipe_id])
def image_upload_url(recipe_id):
    '''Create and return an URL to upload to'''
    return reverse("recipe:recipe-upload-image", args=[recipe_id])

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

def create_user(**kwarg):
    '''create and return new user'''
    return get_user_model().objects.create_user(**kwarg)


class PublicRecipeAPITest(TestCase):
    '''Test unauthenticated API requests'''
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeAPITest(TestCase):
    '''Test authenticated API requests'''
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='test-pass-123',
        )
        self.client.force_authenticate(self.user)


    def test_retrieve_recipes(self):
        create_recipe(user = self.user)
        create_recipe(user = self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes,many = True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,serializer.data)

    def test_recipe_list_limited_to_user(self):
        '''Test list of recipes limited to authenticated user'''
        other_user = create_user(
            email = 'user1@example.com',
            password = 'user1pass',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes,many = True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,serializer.data)

    def test_get_recipe_detail(self):
        '''Test detail recipe'''
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        '''Test creating recipe'''
        payload = {
            'title':'Sample recipe',
            'time_minutes': 5,
            'price': Decimal('5.50'),
            'description': 'sample description',
            'link': 'http://example.com/recipe.pdf',
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k,v in payload.items():
            self.assertEqual(getattr(recipe,k), v)
        self.assertEqual(recipe.user, self.user)

    #Tags
    def test_create_recipe_with_new_tags(self):
        '''Test creating a recipe with new tags'''
        payload ={
            'title': 'Beef Stew',
            'time_minutes':'40',
            'price': Decimal('10.50'),
            'tags':[{'name': 'Viet'},{'name': 'Stew'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(),2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name= tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        '''Test creating recipe with existing tags'''
        tag_existed = Tag.objects.create(user=self.user,name='Viet')
        payload ={
            'title': 'Beef Stew',
            'time_minutes':'40',
            'price': Decimal('10.50'),
            'tags':[{'name': 'Viet'},{'name': 'Stew'}]
        }
        res=self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(),2)
        self.assertIn(tag_existed,recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name= tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        '''Test creating tag when updating a recipe'''
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name':'NewTag'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag= Tag.objects.get(user=self.user,name='NewTag')
        self.assertIn(new_tag,recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        '''Test assigning an existing taf when updating a recipe'''
        tag_breakfast = Tag.objects.create(user=self.user,name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user,name="Lunch")
        payload = {'tags':[{'name':'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch,recipe.tags.all())
        self.assertNotIn(tag_breakfast,recipe.tags.all())

    def test_clear_recipe_tags(self):
        '''Testing deleting tags on a recipe'''
        tag = Tag.objects.create(user=self.user,name="Dessert")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags':[]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(),0)

    #Ingredient
    def create_recipe_with_new_ingredient(self):
        '''Test creating a new recipe with new ingredient'''
        payload = {
            'title':'Beef Stew',
            'time_minutes':'40',
            'price': Decimal('10.50'),
            'tags':[{'name': 'Viet'}],
            'ingredients':[{'name':'Beef brisket'},{'name':'Fish sauce'}]
        }
        res=self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(),2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name= ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        '''Test creating recipe with existing ingredients'''
        ingredient_existed = Ingredient.objects.create(user=self.user,name='Beef brisket')
        payload ={
            'title': 'Beef Stew',
            'time_minutes':'40',
            'price': Decimal('10.50'),
            'tags':[{'name': 'Viet'},{'name': 'Stew'}],
            'ingredients':[{'name':'Beef brisket'},{'name':'Fish sauce'}]

        }
        res=self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(),2)
        self.assertIn(ingredient_existed,recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name= ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        '''Test creating ingredient when updating a recipe'''
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name':'Lemon'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient= Ingredient.objects.get(user=self.user,name='Lemon')
        self.assertIn(new_ingredient,recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        '''Test assigning an existing ingredient when updating a recipe'''
        ingredient_lemon = Ingredient.objects.create(user=self.user,name="Lemon")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_lemon)

        ingredient_lime = Ingredient.objects.create(user=self.user,name="Lime")
        payload = {'ingredients':[{'name':'Lime'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_lime,recipe.ingredients.all())
        self.assertNotIn(ingredient_lemon,recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        '''Testing deleting ingredients on a recipe'''
        ingredient = Ingredient.objects.create(user=self.user,name="Lemon")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients':[]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(),0)

    #Filtering
    def test_filter_by_tags(self):
        '''Test filtering recipe by tags'''
        r1 = create_recipe(user=self.user, title="Thai Curry")
        r2 = create_recipe(user=self.user, title='Pad Thai')
        tag1 = Tag.objects.create(user=self.user, name='Soup')
        tag2 = Tag.objects.create(user=self.user, name="Fried")
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Pho')


        params = {'tags':f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1= RecipeSerializer(r1)
        s2= RecipeSerializer(r2)
        s3= RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)
    def test_filter_by_ingredient(self):
        '''Test filter recipe by ingredient'''
        r1 = create_recipe(user=self.user, title="Thai Curry")
        r2 = create_recipe(user=self.user, title='Pad Thai')
        i1= Ingredient.objects.create(user=self.user,name='Chicken')
        i2 = Ingredient.objects.create(user=self.user,name='Basil')
        r1.ingredients.add(i1)
        r2.ingredients.add(i2)
        r3 = create_recipe(user=self.user, title='Pho')

        params = {'ingredients':f'{i1.id},{i2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1= RecipeSerializer(r1)
        s2= RecipeSerializer(r2)
        s3= RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


#Image
class ImageUploadTests(TestCase):
    '''Tests for uploading images'''
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='test-pass-123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self) -> None:
        return self.recipe.image.delete()

    def test_upload_image(self):
        '''Test uploading image to recipe'''
        url = image_upload_url(self.recipe.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def tets_upload_image_bad_request(self):
        '''Test uploading a invalid image'''
        url = image_upload_url(self.recipe.id)
        payload = {'image':"this string is an invalid image"}
        res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)




















