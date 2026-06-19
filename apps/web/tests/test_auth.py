from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User


@override_settings(ALLOWED_HOSTS=["testserver"])
class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="auth", name="Auth Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.user = User.objects.create_user(
            username="authuser",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )

    def test_login_success_redirects_dashboard(self):
        response = self.client.post(
            reverse("web:login"),
            {"username": "authuser", "password": "TestPassword123!"},
        )
        self.assertRedirects(response, reverse("web:dashboard"))

    def test_login_invalid_shows_error(self):
        response = self.client.post(
            reverse("web:login"),
            {"username": "authuser", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NIK/ID atau password salah")

    def test_authenticated_login_redirects_dashboard(self):
        self.client.login(username="authuser", password="TestPassword123!")
        response = self.client.get(reverse("web:login"))
        self.assertRedirects(response, reverse("web:dashboard"))

    def test_logout_requires_post(self):
        self.client.login(username="authuser", password="TestPassword123!")
        response = self.client.get(reverse("web:logout"))
        self.assertRedirects(response, reverse("web:dashboard"))

    def test_logout_post_redirects_login(self):
        self.client.login(username="authuser", password="TestPassword123!")
        response = self.client.post(reverse("web:logout"))
        self.assertRedirects(response, reverse("web:login"))
        follow = self.client.get(reverse("web:dashboard"))
        self.assertEqual(follow.status_code, 302)

    def test_login_page_contains_post_logout_form_when_authenticated_in_base(self):
        self.client.login(username="authuser", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertContains(response, 'action="/logout/"')
        self.assertContains(response, "csrfmiddlewaretoken")
