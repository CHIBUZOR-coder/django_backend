from django.test import TestCase
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal
import io

from .models import User, Category, Product, Cart, Product_cart, Order, OrderedProduct, Receipt


def make_image(name="test.jpg"):
    from PIL import Image as PILImage
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


class BaseTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_verified_user(self, email="user@example.com", password="testpass123", is_staff=False):
        user = User.objects.create(
            name="Test User",
            email=email,
            phone="08012345678",
            is_verified=True,
            is_active=True,
            is_staff=is_staff,
        )
        user.set_password(password)
        user.save()
        return user

    def create_unverified_user(self, email="unverified@example.com", password="testpass123"):
        user = User.objects.create(
            name="Unverified User",
            email=email,
            phone="08012345678",
            is_verified=False,
            is_active=True,
        )
        user.set_password(password)
        user.save()
        return user

    def create_category(self, name="Clothing"):
        return Category.objects.create(name=name)

    def create_product(self, name="Test Shirt", price=5000, quantity=10, category=None):
        if category is None:
            category = self.create_category()
        return Product.objects.create(
            name=name,
            price=Decimal(str(price)),
            category=category,
            defaultSize="M",
            image="product_image/placeholder.jpg",
            quantity=quantity,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


# =====================================================================
# REGISTRATION TESTS
# =====================================================================

class RegistrationTests(BaseTestCase):

    @patch("store.serializers.send_verification_email")
    def test_register_success(self, mock_email):
        data = {"name": "John Doe", "email": "john@example.com", "phone": "08012345678", "password": "securepass123"}
        response = self.client.post("/store/register/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["email"], "john@example.com")
        mock_email.assert_called_once()

    @patch("store.serializers.send_verification_email")
    def test_register_user_is_unverified_by_default(self, mock_email):
        self.client.post("/store/register/", {"name": "Jane", "email": "jane@example.com", "phone": "08012345678", "password": "pass123"})
        user = User.objects.get(email="jane@example.com")
        self.assertFalse(user.is_verified)
        self.assertTrue(user.is_active)

    @patch("store.serializers.send_verification_email")
    def test_register_duplicate_email_rejected(self, mock_email):
        self.create_verified_user(email="dupe@example.com")
        response = self.client.post("/store/register/", {"name": "Copy", "email": "dupe@example.com", "phone": "080", "password": "pass"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("store.serializers.send_verification_email")
    def test_register_missing_required_fields(self, mock_email):
        response = self.client.post("/store/register/", {"name": "John"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# LOGIN TESTS
# =====================================================================

class LoginTests(BaseTestCase):

    def test_login_verified_user_returns_tokens(self):
        self.create_verified_user(email="login@example.com", password="mypass123")
        response = self.client.post("/store/login/", {"username": "login@example.com", "password": "mypass123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["email"], "login@example.com")

    def test_login_wrong_password(self):
        self.create_verified_user(email="login@example.com", password="mypass123")
        response = self.client.post("/store/login/", {"username": "login@example.com", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post("/store/login/", {"username": "nobody@example.com", "password": "pass"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("store.serializers.send_verification_email")
    def test_login_unverified_user_blocked_and_email_resent(self, mock_email):
        user = self.create_unverified_user(email="unv@example.com", password="pass123")
        response = self.client.post("/store/login/", {"username": "unv@example.com", "password": "pass123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_email.assert_called_once_with(user)

    def test_login_missing_fields(self):
        response = self.client.post("/store/login/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# ACCOUNT VERIFICATION TESTS
# =====================================================================

class AccountVerificationTests(BaseTestCase):

    def test_verify_success_activates_account(self):
        user = self.create_unverified_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post("/store/verify/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)

    def test_verify_already_verified_returns_200(self):
        user = self.create_verified_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post("/store/verify/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already verified", response.data["message"])

    def test_verify_invalid_token(self):
        user = self.create_unverified_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.post("/store/verify/", {"uid": uid, "token": "bad-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_missing_fields(self):
        response = self.client.post("/store/verify/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# PASSWORD RESET TESTS
# =====================================================================

class PasswordResetTests(BaseTestCase):

    @patch("store.views.send_password_reset_email")
    def test_reset_request_existing_email_sends_email(self, mock_email):
        user = self.create_verified_user(email="reset@example.com")
        response = self.client.post("/store/password-reset/", {"email": "reset@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email.assert_called_once_with(user)

    @patch("store.views.send_password_reset_email")
    def test_reset_request_nonexistent_email_still_returns_200(self, mock_email):
        response = self.client.post("/store/password-reset/", {"email": "ghost@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email.assert_not_called()

    def test_reset_request_missing_email(self):
        response = self.client.post("/store/password-reset/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_confirm_success_changes_password(self):
        user = self.create_verified_user(email="reset@example.com", password="oldpass123")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            "/store/password-reset-confirm/",
            {"uid": uid, "token": token, "new_password": "newpass456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass456"))
        self.assertFalse(user.check_password("oldpass123"))

    def test_reset_confirm_invalid_token(self):
        user = self.create_verified_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.post(
            "/store/password-reset-confirm/",
            {"uid": uid, "token": "invalid", "new_password": "newpass456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_confirm_missing_fields(self):
        response = self.client.post("/store/password-reset-confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# USER UPDATE TESTS
# =====================================================================

class UserUpdateTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_verified_user(email="update@example.com", password="oldpass")
        self.authenticate(self.user)

    def test_update_name(self):
        response = self.client.put("/store/updateuser/", {"name": "New Name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["name"], "New Name")

    def test_update_phone(self):
        response = self.client.put("/store/updateuser/", {"phone": "09099999999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["phone"], "09099999999")

    def test_update_password_is_hashed(self):
        response = self.client.put("/store/updateuser/", {"password": "brandnewpass"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brandnewpass"))
        self.assertFalse(self.user.check_password("oldpass"))

    def test_update_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.put("/store/updateuser/", {"name": "Hacker"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =====================================================================
# PRODUCT TESTS
# =====================================================================

class ProductTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.category = self.create_category()
        self.product = self.create_product(category=self.category)

    def test_list_products_is_public(self):
        response = self.client.get("/store/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_products_empty(self):
        Product.objects.all().delete()
        response = self.client.get("/store/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_product_detail_is_public(self):
        response = self.client.get(f"/store/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.product.name)

    def test_product_detail_not_found(self):
        response = self.client.get("/store/products/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_product_as_admin(self):
        admin = self.create_verified_user(email="admin@example.com", is_staff=True)
        self.authenticate(admin)
        data = {
            "name": "New Shirt",
            "price": "3500.00",
            "category": self.category.id,
            "defaultSize": "M",
            "quantity": 20,
            "new_hit": False,
            "image": make_image(),
        }
        response = self.client.post("/store/createproduct/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["product"]["name"], "New Shirt")
        self.assertEqual(response.data["product"]["quantity"], 20)

    def test_create_product_as_regular_user_forbidden(self):
        user = self.create_verified_user()
        self.authenticate(user)
        response = self.client.post("/store/createproduct/", {"name": "Shirt", "price": "100"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_unauthenticated(self):
        response = self.client.post("/store/createproduct/", {"name": "Shirt", "price": "100"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_product_zero_price_rejected(self):
        admin = self.create_verified_user(email="admin@example.com", is_staff=True)
        self.authenticate(admin)
        data = {"name": "Free Shirt", "price": "0", "category": self.category.id, "defaultSize": "M", "quantity": 5, "image": make_image()}
        response = self.client.post("/store/createproduct/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_negative_price_rejected(self):
        admin = self.create_verified_user(email="admin@example.com", is_staff=True)
        self.authenticate(admin)
        data = {"name": "Bad Shirt", "price": "-100", "category": self.category.id, "defaultSize": "M", "quantity": 5, "image": make_image()}
        response = self.client.post("/store/createproduct/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product_as_admin(self):
        admin = self.create_verified_user(email="admin@example.com", is_staff=True)
        self.authenticate(admin)
        response = self.client.put(f"/store/updateproduct/{self.product.id}/", {"name": "Updated Shirt", "quantity": 50}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["product"]["name"], "Updated Shirt")
        self.assertEqual(response.data["product"]["quantity"], 50)

    def test_update_product_as_regular_user_forbidden(self):
        user = self.create_verified_user()
        self.authenticate(user)
        response = self.client.put(f"/store/updateproduct/{self.product.id}/", {"name": "Hacked"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_not_found(self):
        admin = self.create_verified_user(email="admin@example.com", is_staff=True)
        self.authenticate(admin)
        response = self.client.put("/store/updateproduct/99999/", {"name": "Ghost"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =====================================================================
# CART TESTS
# =====================================================================

class CartTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_verified_user()
        self.product = self.create_product(quantity=10)
        self.authenticate(self.user)

    def test_get_cart_auto_creates_if_not_exists(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        response = self.client.get("/store/getcart/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertEqual(response.data["items"], [])

    def test_get_cart_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/store/getcart/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_item_to_cart(self):
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 2, "size": "M"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["cart"]["items"]), 1)
        self.assertEqual(response.data["cart"]["items"][0]["quantity"], 2)

    def test_add_item_uses_product_default_size_when_omitted(self):
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = response.data["cart"]["items"][0]
        self.assertEqual(item["size"], self.product.defaultSize)

    def test_add_same_product_and_size_increments_quantity(self):
        self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 2, "size": "M"}, format="json")
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 3, "size": "M"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["cart"]["items"]), 1)
        self.assertEqual(response.data["cart"]["items"][0]["quantity"], 5)

    def test_add_same_product_different_sizes_creates_separate_entries(self):
        self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 1, "size": "M"}, format="json")
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 1, "size": "L"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["cart"]["items"]), 2)

    def test_add_item_exceeds_stock_rejected(self):
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 11, "size": "M"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_item_cumulative_total_exceeds_stock_rejected(self):
        self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 8, "size": "M"}, format="json")
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 5, "size": "M"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_item_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/store/addCartItem/", {"product": self.product.id, "quantity": 1, "size": "M"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_decrement_item_reduces_quantity_by_one(self):
        cart = Cart.objects.create(user=self.user)
        item = Product_cart.objects.create(cart=cart, product=self.product, quantity=3, size="M")

        response = self.client.patch(f"/store/decrementCartItem/{item.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_decrement_item_at_quantity_one_deletes_it(self):
        cart = Cart.objects.create(user=self.user)
        item = Product_cart.objects.create(cart=cart, product=self.product, quantity=1, size="M")

        response = self.client.patch(f"/store/decrementCartItem/{item.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Product_cart.objects.filter(id=item.id).exists())

    def test_decrement_other_users_item_blocked(self):
        other = self.create_verified_user(email="other@example.com")
        cart = Cart.objects.create(user=other)
        item = Product_cart.objects.create(cart=cart, product=self.product, quantity=3, size="M")

        response = self.client.patch(f"/store/decrementCartItem/{item.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_item_deletes_entire_line(self):
        cart = Cart.objects.create(user=self.user)
        item = Product_cart.objects.create(cart=cart, product=self.product, quantity=3, size="M")

        response = self.client.delete(f"/store/removeCartItem/{item.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Product_cart.objects.filter(id=item.id).exists())

    def test_remove_other_users_item_blocked(self):
        other = self.create_verified_user(email="other@example.com")
        cart = Cart.objects.create(user=other)
        item = Product_cart.objects.create(cart=cart, product=self.product, quantity=1, size="M")

        response = self.client.delete(f"/store/removeCartItem/{item.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =====================================================================
# ORDER TESTS
# =====================================================================

class OrderTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_verified_user()
        self.product = self.create_product(price=5000, quantity=10)
        self.authenticate(self.user)
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = Product_cart.objects.create(cart=self.cart, product=self.product, quantity=2, size="M")

    @patch("store.views.requests.post")
    def test_checkout_success_returns_payment_link(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com/xxx"}})

        response = self.client.post("/store/checkout/", format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["link"], "https://pay.flw.com/xxx")

    @patch("store.views.requests.post")
    def test_checkout_deducts_stock(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})

        self.client.post("/store/checkout/", format="json")

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)

    @patch("store.views.requests.post")
    def test_checkout_clears_cart(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})

        self.client.post("/store/checkout/", format="json")

        self.assertFalse(Product_cart.objects.filter(cart=self.cart).exists())

    @patch("store.views.requests.post")
    def test_checkout_calculates_total_price_correctly(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})

        response = self.client.post("/store/checkout/", format="json")
        order = Order.objects.get(id=response.data["order_id"])
        self.assertEqual(order.total_price, Decimal("10000.00"))

    @patch("store.views.requests.post")
    def test_checkout_order_starts_as_pending(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})

        response = self.client.post("/store/checkout/", format="json")
        order = Order.objects.get(id=response.data["order_id"])
        self.assertEqual(order.status, Order.StatusChoices.PENDING)

    @patch("store.views.requests.post")
    def test_checkout_flutterwave_failure_cancels_order(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "error"})

        response = self.client.post("/store/checkout/", format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])

        order = Order.objects.filter(user=self.user).first()
        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

    def test_checkout_empty_cart_rejected(self):
        self.cart_item.delete()
        response = self.client.post("/store/checkout/", format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/store/checkout/", format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("store.views.requests.post")
    def test_order_history_returns_users_orders(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})
        self.client.post("/store/checkout/", format="json")

        response = self.client.get("/store/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_order_history_empty(self):
        response = self.client.get("/store/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_order_history_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/store/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("store.views.requests.post")
    def test_order_detail_returns_items(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})
        checkout = self.client.post("/store/checkout/", format="json")
        order_id = checkout.data["order_id"]

        response = self.client.get(f"/store/orders/{order_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], order_id)
        self.assertEqual(len(response.data["items"]), 1)

    @patch("store.views.requests.post")
    def test_order_detail_other_user_blocked(self, mock_post):
        mock_post.return_value = MagicMock(json=lambda: {"status": "success", "data": {"link": "https://pay.flw.com"}})
        checkout = self.client.post("/store/checkout/", format="json")
        order_id = checkout.data["order_id"]

        other = self.create_verified_user(email="other@example.com")
        self.authenticate(other)
        response = self.client.get(f"/store/orders/{order_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_detail_not_found(self):
        response = self.client.get("/store/orders/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =====================================================================
# PAYMENT VERIFICATION TESTS
# =====================================================================

class PaymentVerificationTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_verified_user()
        self.product = self.create_product(price=5000, quantity=10)
        self.authenticate(self.user)
        self.order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PENDING,
            total_price=Decimal("10000.00"),
        )
        OrderedProduct.objects.create(
            order=self.order, product=self.product, quantity=2, price_at_purchase=Decimal("5000.00")
        )

    def _flw_success_response(self, amount=10000.0):
        return MagicMock(json=lambda: {
            "data": {
                "id": 111222,
                "status": "successful",
                "amount": amount,
                "currency": "NGN",
                "tx_ref": "tx-ref-abc",
                "meta": {"order_id": self.order.id, "userId": self.user.id},
            }
        })

    def test_verify_missing_transaction_id(self):
        response = self.client.get("/store/payment/verify/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("store.views.requests.get")
    def test_verify_success_marks_order_paid(self, mock_get):
        mock_get.return_value = self._flw_success_response()

        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.StatusChoices.PAID)

    @patch("store.views.requests.get")
    def test_verify_success_creates_receipt(self, mock_get):
        mock_get.return_value = self._flw_success_response()

        self.client.get("/store/payment/verify/?transaction_id=111222")

        receipt = Receipt.objects.get(order=self.order)
        self.assertEqual(receipt.flw_transaction_id, "111222")
        self.assertEqual(receipt.status, Receipt.StatusChoices.SUCCESSFUL)
        self.assertEqual(receipt.currency, "NGN")

    @patch("store.views.requests.get")
    def test_verify_failed_payment_status(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {
            "data": {
                "id": 111222,
                "status": "failed",
                "amount": 10000.0,
                "currency": "NGN",
                "tx_ref": "tx-ref-abc",
                "meta": {"order_id": self.order.id, "userId": self.user.id},
            }
        })

        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    @patch("store.views.requests.get")
    def test_verify_amount_mismatch_blocked(self, mock_get):
        mock_get.return_value = self._flw_success_response(amount=5000.0)

        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mismatch", response.data["message"].lower())

    @patch("store.views.requests.get")
    def test_verify_duplicate_receipt_returns_200(self, mock_get):
        Receipt.objects.create(
            order=self.order, user=self.user,
            flw_transaction_id="111222", tx_ref="tx-ref-abc",
            amount_paid=10000.0, currency="NGN",
            status=Receipt.StatusChoices.SUCCESSFUL,
        )
        mock_get.return_value = self._flw_success_response()

        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already verified", response.data["message"])
        self.assertEqual(Receipt.objects.filter(order=self.order).count(), 1)

    @patch("store.views.requests.get")
    def test_verify_other_users_order_blocked(self, mock_get):
        other = self.create_verified_user(email="other@example.com")
        self.authenticate(other)
        mock_get.return_value = self._flw_success_response()

        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/store/payment/verify/?transaction_id=111222")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
