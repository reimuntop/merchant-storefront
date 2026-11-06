from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewIn(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    body: str
    user_id: int
    is_anonymous: bool = False


class ProductQuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=5000)


class ProductQuestionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=5000)


class AuthIn(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=1)


class ChangeEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )


class ProfileUpdate(BaseModel):
    display_name: str


class TeamMemberIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["viewer", "editor"] = "viewer"


class TeamMemberUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)
    role: Optional[Literal["viewer", "editor"]] = None
    active: Optional[bool] = None


class WebhookIn(BaseModel):
    name: str = Field(default="Discord notifications", min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=500)
    active: bool = True


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    active: Optional[bool] = None


class WebhookTestIn(BaseModel):
    url: str = Field(min_length=1, max_length=500)


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=30)
    logo_url: Optional[str] = Field(default=None, max_length=400)
    banner_url: Optional[str] = Field(default=None, max_length=400)
    address: Optional[str] = Field(default=None, max_length=300)
    opening_hours: Optional[str] = Field(default=None, max_length=2000)
    return_policy: Optional[str] = Field(default=None, max_length=5000)


class StoreUpdate(BaseModel):
    # LAB KERENTANAN YANG DISENGAJA: LAB-NEW-06
    owner_id: Optional[int] = None # Memungkinkan user yang tidak berwenang untuk mengubah pemilik toko dengan memanipulasi owner_id.
    name: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    logo_url: Optional[str] = Field(default=None, max_length=400)
    banner_url: Optional[str] = Field(default=None, max_length=400)
    address: Optional[str] = Field(default=None, max_length=300)
    opening_hours: Optional[str] = Field(default=None, max_length=2000)
    return_policy: Optional[str] = Field(default=None, max_length=5000)


class EmailPreviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    price: float = Field(ge=0)
    image_url: str = Field(default="", max_length=400)
    category_id: Optional[int] = Field(default=None, gt=0)
    stock: int = Field(ge=0)
    sku: Optional[str] = Field(default=None, max_length=80)
    status: Literal["draft", "active", "archived"] = "draft"


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = Field(default=None, max_length=400)
    category_id: Optional[int] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, max_length=80)
    status: Optional[Literal["draft", "active", "archived"]] = None


class ProductImageImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2000)


class OrderStatusIn(BaseModel):
    status: Literal["pending", "confirmed", "packed", "shipped", "completed", "cancelled"]


class VariantIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    size: Optional[str] = Field(default=None, max_length=60)
    color: Optional[str] = Field(default=None, max_length=60)
    sku: str = Field(min_length=1, max_length=80)
    stock: int = Field(ge=0)
    price: Optional[float] = Field(default=None, ge=0)
    active: bool = True


class VariantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    size: Optional[str] = Field(default=None, max_length=60)
    color: Optional[str] = Field(default=None, max_length=60)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=80)
    stock: Optional[int] = Field(default=None, ge=0)
    price: Optional[float] = Field(default=None, ge=0)
    active: Optional[bool] = None


class AddressIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    recipient_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=30)
    address_line: str = Field(min_length=1, max_length=300)
    city: str = Field(min_length=1, max_length=120)
    postal_code: str = Field(min_length=1, max_length=20)
    is_default: bool = False


class AddressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = Field(default=None, min_length=1, max_length=80)
    recipient_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, min_length=1, max_length=30)
    address_line: Optional[str] = Field(default=None, min_length=1, max_length=300)
    city: Optional[str] = Field(default=None, min_length=1, max_length=120)
    postal_code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    is_default: Optional[bool] = None


class CheckoutIn(BaseModel):
    address_id: Optional[int] = Field(default=None, gt=0)


class CartShippingAddressIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_id: int = Field(gt=0)


class CartCouponIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class OrderInternalNoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    internal_note: Optional[str] = Field(default=None, max_length=2000)


class RefundCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)
    refund_amount: float = Field(gt=0, allow_inf_nan=False)


class ReturnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int
    reason: str = Field(min_length=1, max_length=1000)


class DiscountIn(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["percentage", "fixed"]
    value: float = Field(gt=0)
    min_subtotal: float = Field(default=0, ge=0)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    active: bool = True
    scope: Literal["all", "category", "product"] = "all"
    target_id: Optional[int] = Field(default=None, gt=0)


class DiscountUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Optional[Literal["percentage", "fixed"]] = None
    value: Optional[float] = Field(default=None, gt=0)
    min_subtotal: Optional[float] = Field(default=None, ge=0)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    active: Optional[bool] = None
    scope: Optional[Literal["all", "category", "product"]] = None
    target_id: Optional[int] = Field(default=None, gt=0)
