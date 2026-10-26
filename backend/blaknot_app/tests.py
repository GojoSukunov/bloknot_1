import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .models import Deal, Note, Tasks, User

PASSWORD = "Str0ng-pass-123!"


def make_user(name):
    return User.objects.create_user(username=name, email=f"{name}@example.com", password=PASSWORD)


def png_bytes(fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, fmt)
    return buf.getvalue()


class BaseCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.deal_a = Deal.objects.create(owner=self.alice, title_deal="A deal", description="secret A")
        self.deal_b = Deal.objects.create(owner=self.bob, title_deal="B deal", description="secret B")
        self.note_b = Note.objects.create(deal=self.deal_b, title_note="B note")
        self.task_b = Tasks.objects.create(owner=self.bob, deal=self.deal_b, title_task="B task")
        self.client.force_authenticate(self.alice)


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_anonymous_has_no_access(self):
        for url in ("/api/me/", "/api/deals/", "/api/tasks/", "/api/notes/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)
        self.assertEqual(self.client.post("/api/deals/", {"title_deal": "x"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": "x"}).status_code, 401)

    def test_register_and_login_flow(self):
        payload = {"username": "newbie", "email": "New@Example.com", "password": PASSWORD,
                   "age": 20, "phone_number": "+996555123456"}
        r = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotIn("password", r.json())
        self.assertEqual(User.objects.get(username="newbie").email, "new@example.com")

        r = self.client.post("/api/auth/login/", {"username": "newbie", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["user"]["username"], "newbie")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

        # refresh работает, logout отзывает токен
        self.client.credentials()
        r = self.client.post("/api/auth/refresh/", {"refresh": data["refresh"]}, format="json")
        self.assertEqual(r.status_code, 200)
        new_refresh, new_access = r.json()["refresh"], r.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": new_refresh}, format="json").status_code, 205)
        self.client.credentials()
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": new_refresh}, format="json").status_code, 401)

    def test_weak_and_duplicate_registration_rejected(self):
        base = {"username": "weak", "email": "weak@example.com", "age": 20}
        self.assertEqual(self.client.post("/api/auth/register/", {**base, "password": "1"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/auth/register/", {**base, "password": "password"}, format="json").status_code, 400)
        make_user("dup")
        r = self.client.post("/api/auth/register/", {**base, "username": "dup2", "email": "DUP@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_login_failure_is_generic(self):
        make_user("carol")
        r1 = self.client.post("/api/auth/login/", {"username": "carol", "password": "wrong"}, format="json")
        r2 = self.client.post("/api/auth/login/", {"username": "nobody", "password": "wrong"}, format="json")
        self.assertEqual((r1.status_code, r2.status_code), (401, 401))
        self.assertEqual(r1.json(), r2.json())

    def test_bruteforce_lockout(self):
        make_user("dave")
        codes = [self.client.post("/api/auth/login/", {"username": "dave", "password": "bad"}, format="json").status_code
                 for _ in range(7)]
        self.assertIn(429, codes)
        # даже верный пароль заблокирован на время блокировки
        r = self.client.post("/api/auth/login/", {"username": "dave", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 429)

    def test_logout_rejects_foreign_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        alice, bob = make_user("a1"), make_user("b1")
        bob_refresh = str(RefreshToken.for_user(bob))
        self.client.force_authenticate(alice)
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": bob_refresh}, format="json").status_code, 400)


class ProfileTests(BaseCase):
    def test_me_returns_only_safe_fields(self):
        data = self.client.get("/api/me/").json()
        self.assertEqual(data["username"], "alice")
        for forbidden in ("password", "is_superuser", "is_staff", "groups", "user_permissions", "last_login"):
            self.assertNotIn(forbidden, data)

    def test_cannot_escalate_privileges(self):
        r = self.client.patch("/api/me/", {"is_superuser": True, "is_staff": True, "is_active": False,
                                           "password": "hacked"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_superuser)
        self.assertFalse(self.alice.is_staff)
        self.assertTrue(self.alice.is_active)
        self.assertTrue(self.alice.check_password(PASSWORD))

    def test_user_endpoints_for_others_do_not_exist(self):
        for url in ("/api/User/", f"/api/User/{self.bob.pk}/", f"/api/users/{self.bob.pk}/", f"/api/me/{self.bob.pk}/"):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.delete("/api/me/").status_code, 405)

    def test_email_must_stay_unique(self):
        r = self.client.patch("/api/me/", {"email": "BOB@example.com"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_change_password(self):
        self.assertEqual(self.client.post("/api/auth/password/", {"old_password": "nope", "new_password": "An0ther-Str0ng-1"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/auth/password/", {"old_password": PASSWORD, "new_password": "123"}, format="json").status_code, 400)
        r = self.client.post("/api/auth/password/", {"old_password": PASSWORD, "new_password": "An0ther-Str0ng-1"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.check_password("An0ther-Str0ng-1"))

    def test_image_upload_validation(self):
        good = SimpleUploadedFile("a.png", png_bytes("PNG"), content_type="image/png")
        with override_settings(MEDIA_ROOT="/tmp/bloknot-test-media"):
            r = self.client.patch("/api/me/", {"profile_image": good}, format="multipart")
            self.assertEqual(r.status_code, 200, r.content)
            self.assertRegex(r.json()["profile_image"], r"/profile_image/[0-9a-f]{32}\.png$")
            bad = SimpleUploadedFile("a.png", b"<script>alert(1)</script>", content_type="image/png")
            self.assertEqual(self.client.patch("/api/me/", {"profile_image": bad}, format="multipart").status_code, 400)
            gif = SimpleUploadedFile("a.gif", png_bytes("GIF"), content_type="image/gif")
            self.assertEqual(self.client.patch("/api/me/", {"profile_image": gif}, format="multipart").status_code, 400)
            with override_settings(PROFILE_IMAGE_MAX_BYTES=10):
                big = SimpleUploadedFile("b.png", png_bytes("PNG"), content_type="image/png")
                self.assertEqual(self.client.patch("/api/me/", {"profile_image": big}, format="multipart").status_code, 400)


class IsolationTests(BaseCase):
    """Пользователь A не видит и не меняет данные пользователя B."""

    def test_deal_list_and_detail_isolated(self):
        data = self.client.get("/api/deals/").json()
        self.assertEqual([d["id"] for d in data["results"]], [self.deal_a.pk])
        self.assertEqual(self.client.get(f"/api/deals/{self.deal_b.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/deals/{self.deal_b.pk}/", {"title_deal": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/deals/{self.deal_b.pk}/").status_code, 404)
        self.assertTrue(Deal.objects.filter(pk=self.deal_b.pk).exists())

    def test_create_deal_with_all_fields_owner_forced(self):
        r = self.client.post("/api/deals/", {"title_deal": "N", "description": "d", "cash": 500,
                                              "owner": self.bob.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Deal.objects.get(pk=r.json()["id"]).owner, self.alice)
        self.assertEqual(r.json()["cash"], 500)

    def test_cannot_add_task_to_foreign_deal(self):
        r = self.client.post("/api/tasks/", {"deal": self.deal_b.pk, "title_task": "t"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("secret B", r.content.decode())

    def test_cannot_move_task_to_foreign_deal_or_owner(self):
        t = Tasks.objects.create(owner=self.alice, deal=self.deal_a, title_task="mine")
        r = self.client.patch(f"/api/tasks/{t.pk}/", {"deal": self.deal_b.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f"/api/tasks/{t.pk}/", {"owner": self.bob.pk, "status": True}, format="json")
        self.assertEqual(r.status_code, 200)
        t.refresh_from_db()
        self.assertEqual(t.owner, self.alice)
        self.assertTrue(t.status)

    def test_tasks_isolated(self):
        self.assertEqual(self.client.get("/api/tasks/").json()["count"], 0)
        self.assertEqual(self.client.get(f"/api/tasks/{self.task_b.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/tasks/{self.task_b.pk}/").status_code, 404)

    def test_notes_isolated_on_create_and_update(self):
        self.assertEqual(self.client.post("/api/notes/", {"deal": self.deal_b.pk, "title_note": "x"}, format="json").status_code, 400)
        mine = Note.objects.create(deal=self.deal_a, title_note="mine")
        self.assertEqual(self.client.patch(f"/api/notes/{mine.pk}/", {"deal": self.deal_b.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.get(f"/api/notes/{self.note_b.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/notes/{self.note_b.pk}/").status_code, 404)
        r = self.client.post("/api/notes/", {"deal": self.deal_a.pk, "title_note": "ok"}, format="json")
        self.assertEqual(r.status_code, 201)

    def test_deal_detail_includes_notes_and_pagination(self):
        Note.objects.create(deal=self.deal_a, title_note="n1")
        data = self.client.get("/api/deals/").json()
        self.assertIn("next", data)
        self.assertEqual(len(data["results"][0]["note_detail"]), 1)
        # description/cash теперь отдаются списком — N+1 на фронте не нужен
        self.assertIn("cash", data["results"][0])

    def test_filters(self):
        Deal.objects.create(owner=self.alice, title_deal="Done", status="completed")
        r = self.client.get("/api/deals/?status=completed").json()
        self.assertEqual([d["title_deal"] for d in r["results"]], ["Done"])
        r = self.client.get("/api/deals/?search=A deal").json()
        self.assertEqual(r["count"], 1)


class MiscTests(APITestCase):
    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz/").status_code, 200)

    def test_swagger_and_allauth_removed(self):
        for url in ("/docs/", "/accounts/login/", "/api/", "/"):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_json_only_renderer_in_error(self):
        r = self.client.get("/api/me/")
        self.assertEqual(r["Content-Type"], "application/json")


class ClientIpTests(APITestCase):
    def test_lockout_is_per_client_ip(self):
        cache.clear()
        make_user("erin")
        hdr = lambda ip: {"HTTP_X_FORWARDED_FOR": ip}
        for _ in range(6):
            self.client.post("/api/auth/login/", {"username": "erin", "password": "bad"}, format="json", **hdr("198.51.100.1"))
        r = self.client.post("/api/auth/login/", {"username": "erin", "password": PASSWORD}, format="json", **hdr("198.51.100.1"))
        self.assertEqual(r.status_code, 429)
        # тот же логин с другого IP не заблокирован
        r = self.client.post("/api/auth/login/", {"username": "erin", "password": PASSWORD}, format="json", **hdr("198.51.100.2"))
        self.assertEqual(r.status_code, 200)
