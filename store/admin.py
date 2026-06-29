from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# ALL REQUIRED IMPORTS COLLATED CLEANLY
from .models import (
    User as UserType,
    Order as OrderTypes,
    OrderedProduct as OrderproductTypes,
    Product_cart as ProductCartType,
    Category as CategoryType,
    Product as ProductType,
    Cart as CartType,
    Receipt as ReceiptType,
)

# =========================================================================
# 1. FIXED CUSTOM FORM FOR CREATING USERS
# =========================================================================
class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    image = forms.ImageField(widget=forms.FileInput, required=False)

    class Meta:
        model = UserType
        fields = (
            "email",
            "name",
            "phone",
            "password",
            "image",
            "is_verified",
            "is_staff",
            "is_active",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        # Save the uploaded image directly from cleaned data
        if self.cleaned_data.get("image"):
            user.image = self.cleaned_data["image"]

        if commit:
            user.save()
        return user


# =========================================================================
# 2. CUSTOM USER MANAGEMENT ADMIN
# =========================================================================
@admin.register(UserType)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm

    list_display = (
        "id",
        "username",
        "email",
        "name",
        "phone",
        "image",
        "is_verified",
        "is_staff",
    )
    list_filter = ("is_verified", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "name", "phone")
    ordering = ("-id",)

    # Form layout when modifying an existing user profile
    fieldsets = (
        (None, {"fields": ("email", "name", "phone", "image")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Form layout when generating a completely brand new user instance
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "phone",
                    "password",
                    "image",
                    "is_verified",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    # ◄ FIX 1: Overrides Django's form builder to pull binary file uploads on creation
    # =========================================================================
    # 2. CUSTOM USER MANAGEMENT ADMIN
    # =========================================================================
    # ... keep your list_display, fieldsets, and add_fieldsets exactly as they are ...

    # ◄ FIXED: Adjusted positional argument pass-through to match UserAdmin definitions
    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    # ◄ FIXED: Removed the redundant validation wrapper causing view redirection bugs
    def add_view(self, request, form_url="", extra_context=None):
        return super().add_view(request, form_url, extra_context)


# =========================================================================
# 3. CATEGORY MANAGEMENT
# =========================================================================
@admin.register(CategoryType)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


# =========================================================================
# 4. PRODUCT MANAGEMENT (Rest assured, standard model admin handles images natively)
# =========================================================================
@admin.register(ProductType)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "category",
        "defaultSize",
        "quantity",
        "created_at",
    )
    list_filter = ("category", "defaultSize", "new_hit", "created_at")
    search_fields = ("name", "category__name")
    ordering = ("-id",)


# =========================================================================
# 5. MASTER CART HEADERS
# =========================================================================
@admin.register(CartType)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    search_fields = ("user__username", "user__email")


# =========================================================================
# 6. SHOPPING CART LINE ITEMS
# =========================================================================
@admin.register(ProductCartType)
class ProductCartAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "size", "quantity", "created_at")
    list_filter = ("created_at",)
    search_fields = ("cart__user__username", "product__name")


# =========================================================================
# 7. ORDER INLINE MANAGERS (Displays linked products inside the core Order)
# =========================================================================
class OrderProductInline(admin.TabularInline):
    model = OrderproductTypes
    extra = 0
    readonly_fields = ("product", "quantity", "price_at_purchase")
    can_delete = False


# =========================================================================
# 8. MASTER ORDER CONTROL INVOICE ADMIN
# =========================================================================
@admin.register(OrderTypes)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_email", "status", "total_price", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    inlines = [OrderProductInline]


@admin.register(ReceiptType)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "user",
        "flw_transaction_id",
        "amount_paid",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("flw_transaction_id", "tx_ref", "user__email")
    ordering = ("-created_at",)
