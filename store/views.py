from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import (
    CreateUserSerializer,
    GetUserSerializer,
    LoginSerializer,
    updateUserSerializer,
    GetProductSerializer,
    AdminGetProduct,
    CreatProductSerializer,
    upddateProductSerializer,
    AddToCartSerializer,
    ProductCartDetailsSerializer,
    CartSerializer,
    AddOrderSerializer,
    GetOrderSerializer,
    
)
from django.shortcuts import get_object_or_404
from .models import Product, Cart, Product_cart, Order, User, Receipt
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

# Flutterwave
import requests
import uuid
from django.conf import settings


class CreateUser(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # FIX: Pass request.FILES alongside request.data explicitly!
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        serializer_response = GetUserSerializer(user)

        return Response(
            {"message": "User created successfully", "data": serializer_response.data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    # Anyone can attempt to log in
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Pass the incoming JSON credentials (username/email & password) to the serializer
        serializer = LoginSerializer(data=request.data)

        # 2. Trigger validation. This executes the authenticate() logic under the hood.
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Extract the authenticated user object that the serializer attached to attrs
        user = serializer.validated_data["user"]

        # 4. Generate JWT tokens for this specific user session
        refresh = RefreshToken.for_user(user)

        # 5. Serialize user profile data to return to the client
        user_profile_serializer = GetUserSerializer(user)

        # 6. Return response package. Meta status is separate from the body!
        return Response(
            {
                "message": "Login successful.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": user_profile_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserUpdateView(APIView):

    # 1. Protect the endpoint: Only authenticated requests with valid tokens pass through
    permission_classes = [IsAuthenticated]

    # 2. Support file uploads: Allows the view to accept multi-part form data
    # (crucial for profile images alongside text fields like name or password)
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        # 3. Bind the logged-in user instance with incoming request data.
        # partial=True allows the frontend to send only the fields they want to change.
        serializer = updateUserSerializer(request.user, data=request.data, partial=True)

        # 4. Gatekeeper validation check
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 5. Save updates safely
        # (This triggers your custom update() method, popping and hashing the password safely!)
        updated_user = serializer.save()

        # 6. Format the final output layout using your clean read-only serializer
        user_serializer = GetUserSerializer(updated_user)

        # 7. Return success state to the client application (Status 200 separate from body)
        return Response(
            {"message": "Profile updated successfully.", "user": user_serializer.data},
            status=status.HTTP_200_OK,
        )


class ProductCreateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # ← ADD THESE TEMPORARY DEBUG LINES
        print("USER:", request.user)
        print("IS AUTHENTICATED:", request.user.is_authenticated)
        print("IS STAFF:", request.user.is_staff)
        print("AUTH HEADER:", request.headers.get("Authorization"))
        # 1. Bind incoming raw data to the write-serializer
        serializer = CreatProductSerializer(data=request.data)

        # 2. Run data validation rules (e.g., validate_price)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Save the new product to the database (returns a ProductType instance)
        new_product = serializer.save()

        # 4. Hand the database object to the read-serializer for formatting
        serializer_response = AdminGetProduct(new_product)

        # 5. Return the full dictionary data back to the frontend application
        return Response(
            {
                "message": "Product created successfully.",
                "product": serializer_response.data,  # Clean dictionary data
            },
            status=status.HTTP_201_CREATED,
        )


class ProductUpdateView(APIView):

    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, product_id):
        # 1. Use product_id from the URL to fetch the record from the database
        product_instance = get_object_or_404(Product, id=product_id)

        # 2. Match the exact pattern from UpdateUser View:
        # Slot 1: The old database instance
        # Slot 2: The incoming new request data
        # Slot 3: partial=True to allow missing fields
        serializer = upddateProductSerializer(
            product_instance, request.data, partial=True
        )

        # 3. Validation security check
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 4. Save updates (triggers your custom update() serializer method)
        updated_product = serializer.save()

        # 5. Format the final output using your clean read-only serializer
        serializer_response = AdminGetProduct(updated_product)

        # 6. Return success state with the full data block
        return Response(
            {
                "message": "Product updated successfully.",
                "product": serializer_response.data,
            },
            status=status.HTTP_200_OK,
        )


class CartAddItemView(APIView):
    """
    Endpoint for users to add or increment item variants in their cart.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. Fetch or create the active cart frame for this logged-in user
        user_cart, _ = Cart.objects.get_or_create(user=request.user)

        # 2. Inject the server-validated cart ID into the mutable data copy
        payload = request.data.copy()
        payload["cart"] = user_cart.id

        # 3. Process validation through your AddToCartSerializer
        serializer = AddToCartSerializer(data=payload)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 4. Save updates (runs your custom create method with stock checks)
        cart_line_item = serializer.save()

        # 5. Dual Serializer Design Pattern: Format outbound output using deep nested read fields
        response_serializer = ProductCartDetailsSerializer(cart_line_item)
        return Response(
            {
                "message": "Item successfully updated in your cart.",
                "cart_item": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class CartDecrementItemView(APIView):
    """
    Endpoint to lower a cart line item quantity by 1.
    Deletes the item record entirely if quantity drops to 0.
    Accepts: PATCH request with an item_id parameter in the URL.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id: int) -> Response:
        # Secure isolation: Ensure the targeted cart line item belongs to this specific user

        cart_item: Product_cart = get_object_or_404(
            Product_cart, id=item_id, cart__user=request.user
        )

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()

            # Return updated object back to UI so badge counts match smoothly
            response_serializer = ProductCartDetailsSerializer(cart_item)
            return Response(
                {
                    "message": "Item quantity reduced.",
                    "cart_item": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            # If quantity was 1, reducing it down means purging it entirely
            cart_item.delete()
            return Response(
                {
                    "message": "Item completely removed from cart because quantity hit zero."
                },
                status=status.HTTP_200_OK,
            )


class CartRemoveItemView(APIView):
    """
    Endpoint to instantly drop an entire item line variant from the user's basket.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id) -> Response:
        # Secure boundary query check
        cart_item = get_object_or_404(Product_cart, id=item_id, cart__user=request.user)
        cart_item.delete()

        return Response(
            {"message": "Item line completely cleared from your shopping cart."},
            status=status.HTTP_200_OK,
        )


class CartDetailView(APIView):
    """
    Endpoint to retrieve the authenticated user's active shopping cart overview.
    Returns the cart metadata along with all nested product line items.
    Accepts: GET request (No body payload required)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Fetch the user's cart using the clean OneToOne relationship layout.
        # If the user doesn't have a cart record yet, create an empty one on the fly.
        user_cart, _ = Cart.objects.get_or_create(user=request.user)

        # 2. Pass the cart instance to your read-oriented CartSerializer.
        # This triggers the nested 'product_cart_set' lookup to pull all item rows.
        serializer = CartSerializer(user_cart)

        # 3. Return the fully nested JSON payload back to the client application
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = {"user": request.user.id}
        serializer = AddOrderSerializer(data=payload)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 1. Creates Order (PENDING), clears cart, deducts stock — same as before
        placed_order: Order = serializer.save()

        # 2. Build Flutterwave payload — mirrors the Node.js code exactly
        flw_payload = {
            "tx_ref": str(uuid.uuid4()),  # unique transaction reference
            "amount": str(placed_order.total_price),
            "currency": "NGN",
            "redirect_url": f"{settings.FRONTEND_DOMAIN}/payment/verify",  # React page
            "customer": {
                "email": request.user.email,
                "name": request.user.name,
                "phonenumber": request.user.phone,
            },
            "meta": {
                # This is carried by Flutterwave and returned during verification
                # Same pattern as Node.js: meta: { userId, order_id }
                "userId": request.user.id,
                "order_id": placed_order.id,
            },
            "customizations": {
                "title": "My Store",
                "description": "Payment for items in cart",
            },
        }

        # 3. Send to Flutterwave — same as Node.js fetch() call
        flw_response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            json=flw_payload,
            headers={
                "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                "Content-Type": "application/json",
            },
        )

        data = flw_response.json()

        # 4. Handle Flutterwave response — mirrors Node.js check
        if data.get("status") != "success":
            # Payment link failed — cancel the order we just created
            placed_order.status = Order.StatusChoices.CANCELLED
            placed_order.save()
            return Response(
                {"success": False, "message": "Payment initialization failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 5. Return link to React — React redirects user to this link
        return Response(
            {
                "success": True,
                "message": "Payment initialized successfully",
                "link": data["data"]["link"],  # React does: window.location.href = link
                "order_id": placed_order.id,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Get transaction_id from URL query params
        transaction_id = request.query_params.get("transaction_id")

        if not transaction_id:
            return Response(
                {"message": "Missing transaction_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Call Flutterwave to verify
        flw_response = requests.get(
            f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
            headers={"Authorization": f"Bearer {settings.FLW_SECRET_KEY}"},
        )

        data = flw_response.json()

        # 3. Extract data from Flutterwave response
        transaction = data.get("data", {})
        meta = transaction.get("meta", {})

        order_id = meta.get("order_id")
        amount = transaction.get("amount")
        flw_status = transaction.get("status")
        tx_ref = transaction.get("tx_ref")
        currency = transaction.get("currency")
        flw_transaction_id = str(transaction.get("id"))

        # 4. Find the order
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # 5. Check for duplicate — if Receipt already exists for this order
        existing_receipt = Receipt.objects.filter(order=order).first()
        if existing_receipt:
            return Response(
                {
                    "success": True,
                    "message": "Payment already verified",
                    "receipt": {
                        "flw_transaction_id": existing_receipt.flw_transaction_id,
                        "tx_ref": existing_receipt.tx_ref,
                        "amount_paid": existing_receipt.amount_paid,
                        "currency": existing_receipt.currency,
                        "status": existing_receipt.status,
                    },
                    "order": GetOrderSerializer(order).data,
                },
                status=status.HTTP_200_OK,
            )

        # 6. Security checks
        if flw_status != "successful":
            return Response(
                {"success": False, "message": "Payment was not successful"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if float(amount) < float(order.total_price):
            return Response(
                {"success": False, "message": "Amount mismatch. Possible fraud."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 7. Create the Receipt with ALL Flutterwave data
        receipt = Receipt.objects.create(
            order=order,
            user=request.user,
            flw_transaction_id=flw_transaction_id,
            tx_ref=tx_ref,
            amount_paid=amount,
            currency=currency,
            status=Receipt.StatusChoices.SUCCESSFUL,
        )

        # 8. Update order to PAID
        order.status = Order.StatusChoices.PAID
        order.save()

        # 9. Return receipt + full order with nested items to React
        return Response(
            {
                "success": True,
                "message": "Payment successful",
                "receipt": {
                    "flw_transaction_id": receipt.flw_transaction_id,
                    "tx_ref": receipt.tx_ref,
                    # amount_paid comes from Flutterwave — reflects actual amount paid
                    "amount_paid": receipt.amount_paid,
                    "currency": receipt.currency,
                    "status": receipt.status,
                },
                # order contains id, status, total_price, user_email, created_at
                # AND nested items with product name, image, price, quantity
                "order": GetOrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )


class OrderHistoryListView(APIView):
    """
    Endpoint to retrieve all historical orders placed by the authenticated customer.
    Accepts: GET request
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch only the orders belonging to the logged-in user (ordered newest first)
        orders = Order.objects.filter(user=request.user).order_by("-created_at")

        # Notice many=True because we are passing a list/QuerySet of multiple orders
        serializer = GetOrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderDetailView(APIView):
    """
    Endpoint to retrieve the deep-dive details of a single specific order.
    Accepts: GET request with an order_id parameter in the URL.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id: int):
        # Secure isolation: Prevent users from spying on other users' order receipts
        single_order = get_object_or_404(Order, id=order_id, user=request.user)

        # Single instance serialization
        serializer = GetOrderSerializer(single_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActivateAccountView(APIView):
    """
    API Endpoint called by the frontend framework to process
    and complete user account verification.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Read parameters out of the incoming payload body sent by your frontend
        uidb64 = request.data.get("uid")
        token = request.data.get("token")

        if not uidb64 or not token:
            return Response(
                {"detail": "Missing required verification data (uid or token)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 2. Decode the base64 user identifier
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # 3. Mathematically evaluate the token signature validity
        if user is not None and default_token_generator.check_token(user, token):
            if user.is_verified:
                return Response(
                    {"message": "Account is already verified."},
                    status=status.HTTP_200_OK,
                )

            # 4. Success state: Unlock verification flags
            user.is_verified = True
            user.is_active = True
            user.save()

            return Response(
                {"message": "Account verified successfully! You can now log in."},
                status=status.HTTP_200_OK,
            )

        # 5. Token failure handling
        return Response(
            {"detail": "The activation token is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )


from .utils import send_password_reset_email  # ← add to your existing utils import


class PasswordResetRequestView(APIView):
    """
    Step 1: User submits their email to request a password reset.
    Accepts: POST request with { email }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        # 1. Validate that an email was actually provided
        if not email:
            return Response(
                {"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 2. Look up the user by email
            user = User.objects.get(email=email)

            # 3. Send the reset link to their inbox
            send_password_reset_email(user)

        except User.DoesNotExist:
            # 4. Security: Don't reveal whether the email exists or not
            # Always return the same response to prevent email enumeration attacks
            pass

        # 5. Always return success — even if email not found (security best practice)
        return Response(
            {
                "message": "If an account with that email exists, a reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Step 2: User submits their new password along with the uid and token from the email link.
    Accepts: POST request with { uid, token, new_password }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Extract the three required fields from the request body
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        # 2. Validate all fields are present
        if not uidb64 or not token or not new_password:
            return Response(
                {"detail": "uid, token and new_password are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 3. Decode the base64 user ID back to a real ID
            uid = urlsafe_base64_decode(uidb64).decode()

            # 4. Fetch the user from the database
            user = User.objects.get(pk=uid)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # 5. Validate the token is genuine and hasn't expired
        if user is not None and default_token_generator.check_token(user, token):

            # 6. Set and hash the new password using Django's built-in tool
            user.set_password(new_password)
            user.save()

            return Response(
                {
                    "message": "Password reset successful! You can now log in with your new password."
                },
                status=status.HTTP_200_OK,
            )

        # 7. Token is invalid or expired
        return Response(
            {"detail": "The reset link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )
