'''
Tests for tag API
'''
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag , Recipe
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def create_user(email='test@example.com', password='testpass123'):
    '''create and return new user'''
    return get_user_model().objects.create_user(email=email, password=password)

def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])

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

class PublicTagsApiTests(TestCase):
    '''Test unauthenticated API requests'''
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivatetagsApiTest(TestCase):
    '''Test authenticated API requests'''
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        '''Test retrieving tags list'''
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Spicy')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags,many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,serializer.data)

    def test_tags_limited_to_user(self):
        '''Test tags list limited to authenticated user'''
        other_user = create_user(
            email = 'user1@example.com',
            password = 'user1pass',
        )
        Tag.objects.create(user=other_user, name='Soup')

        tag = Tag.objects.create(user=self.user, name= 'Fried')

        res = self.client.get(TAGS_URL)


        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data),1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'],tag.id)

    def test_update_tag(self):
        '''Test updating a tag'''
        tag = Tag.objects.create(user=self.user, name='Spicy')

        payload ={'name':'Soup'}
        url= detail_url(tag.id)
        res = self.client.patch(url,payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='Quickmeal')
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user= self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        '''Test listing tags by those assigned to recipes'''
        t1= Tag.objects.create(user=self.user,name='Thai')
        t2 = Tag.objects.create(user=self.user,name='Mexican')
        recipe = create_recipe(user=self.user,title="Thai Curry")
        recipe.tags.add(t1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(t1)
        s2 = TagSerializer(t2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        '''Test filtered tags return a unique list'''
        tag = Tag.objects.create(user=self.user,name='Soup')
        Tag.objects.create(user=self.user,name='Fried')
        r1 = create_recipe(user=self.user, title="Thai Curry")
        r2 = create_recipe(user=self.user, title='Pad Thai')

        r1.tags.add(tag)
        r2.tags.add(tag)
        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data),1)



