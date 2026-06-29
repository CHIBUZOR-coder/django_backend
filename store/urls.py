# store/urls.py
from django.urls import path
from .views import (
    # Auth Views
    CreateUser,
    ActivateAccountView,
    LoginView,
    UserUpdateView,
    # Product views
    ProductCreateView,
    ProductUpdateView,
    # Cart Views
    CartDetailView,
    CartAddItemView,
    CartDecrementItemView,
    CartRemoveItemView,
    # Order Views
    OrderCheckoutView,
    OrderHistoryListView,
    OrderDetailView,
    # Payment
    PaymentVerifyView,    # Account Recovery
    PasswordResetRequestView,  # ← add
    PasswordResetConfirmView,  # ← add
)

urlpatterns = [
    # =========================================================================
    # STORE ACCOUNT & AUTHENTICATION
    # =========================================================================
    # http://127.0.0.1:9000/store/register/
    path("register/", CreateUser.as_view(), name="user-register"),
    # http://127.0.0.1:9000/store/login/
    path("login/", LoginView.as_view(), name="user-login"),
    # http://127.0.0.1:9000/store/updateuser/
    path("updateuser/", UserUpdateView.as_view(), name="user-update"),
    # http://127.0.0.1:9000/store/verify/
    path("verify/", ActivateAccountView.as_view(), name="api-activate-account"),
    # =========================================================================
    # PRODUCT MANAGEMENT
    # =========================================================================
    # http://127.0.0.1:9000/store/createproduct/
    path("createproduct/", ProductCreateView.as_view(), name="create-product"),
    # http://127.0.0.1:9000/store/updateproduct/
    path(
        "updateproduct/<int:product_id>/",
        ProductUpdateView.as_view(),
        name="update-product",
    ),
    # =========================================================================
    # SHOPPING CART MANAGEMENT
    # =========================================================================
    # http://127.0.0.1:9000/store/getcart/
    path("getcart/", CartDetailView.as_view(), name="cart-detail"),
    # http://127.0.0.1:9000/store/addCartItem/
    path("addCartItem/", CartAddItemView.as_view(), name="cart-add"),
    # Fixed duplication: http://127.0.0.1:9000/store/decrementCartItem/12/
    path(
        "decrementCartItem/<int:item_id>/",
        CartDecrementItemView.as_view(),
        name="cart-decrement",
    ),
    # Fixed typo: http://127.0.0.1:9000/store/removeCartItem/12/
    path(
        "removeCartItem/<int:item_id>/",
        CartRemoveItemView.as_view(),
        name="cart-remove",
    ),
    # =========================================================================
    # ORDER INVOICING & CHECKOUT FLOW
    # =========================================================================
    # http://127.0.0.1:9000/store/checkout/
    path("checkout/", OrderCheckoutView.as_view(), name="order-checkout"),
    # http://127.0.0.1:9000/store/orders/
    path("orders/", OrderHistoryListView.as_view(), name="order-history-list"),
    # http://127.0.0.1:9000/store/orders/42/
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    # =========================================================================
    # PAYMENT
    # =========================================================================
    path("payment/verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    # =========================================================================
    # PASSWORD RECOVERY
    # =========================================================================
    # Step 1: User requests reset link → http://127.0.0.1:9000/store/password-reset/
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    # Step 2: User submits new password → http://127.0.0.1:9000/store/password-reset-confirm/
    path(
        "password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
