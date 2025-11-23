from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal


# ===================== DANH MỤC =====================
class Category(models.Model):
    category_code = models.CharField(max_length=10, primary_key=True, verbose_name="Mã danh mục")
    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True,
        verbose_name="Ảnh danh mục"
    )

    def __str__(self):
        return f"{self.name} ({self.category_code})"


# ===================== NHÀ CUNG ỨNG =====================
class Supplier(models.Model):
    supplier_code = models.CharField(max_length=10, primary_key=True, verbose_name="Mã NCC")
    company_name = models.CharField(max_length=200, verbose_name="Tên công ty")
    tax_code = models.CharField(max_length=20, verbose_name="Mã số thuế", blank=True, null=True)
    contact_name = models.CharField(max_length=100, verbose_name="Người liên hệ")
    phone = models.CharField(max_length=15, verbose_name="SĐT")
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, verbose_name="Địa chỉ", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Hoạt động"), ("inactive", "Tạm dừng")],
        default="active",
        verbose_name="Trạng thái"
    )

    def __str__(self):
        return f"{self.company_name} ({self.supplier_code})"
    # ❌ Bỏ property products lỗi cũ, dùng reverse manager supplier.products (related_name ở SupplierProduct)


# ===================== SẢN PHẨM NHÀ CUNG ỨNG (PRODUCT CHÍNH) =====================
class SupplierProduct(models.Model):
    supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.CASCADE,
        related_name="products",          # supplier.products
        verbose_name="Nhà cung ứng"
    )

    product_code = models.CharField(
        max_length=30,
        verbose_name="Mã sản phẩm NCC"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Tên sản phẩm NCC"
    )

    # Gắn danh mục (không bắt buộc) – để Category.products dùng được
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="products",          # Category.products
        verbose_name="Danh mục"
    )

    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Đơn giá NCC"
    )

    is_active = models.BooleanField(default=True, verbose_name="Đang cung cấp")

    class Meta:
        verbose_name = "Sản phẩm nhà cung ứng"
        verbose_name_plural = "Sản phẩm nhà cung ứng"
        unique_together = ("supplier", "product_code")  # 1 NCC – 1 mã SP

    def __str__(self):
        return f"{self.product_code} - {self.name} ({self.supplier.supplier_code})"


# ===================== NHẬP KHO =====================
class ImportReceipt(models.Model):
    import_code = models.CharField(
        max_length=20, unique=True, verbose_name="Mã phiếu nhập", blank=True
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Nhà cung ứng"
    )
    asn = models.ForeignKey(
        'ASN',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Phiếu ASN"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    import_date = models.DateField(default=timezone.now, verbose_name="Ngày nhập")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Người tạo"
    )

    class Meta:
        verbose_name = "Phiếu nhập kho"
        verbose_name_plural = "Phiếu nhập kho"
        ordering = ["-import_date", "-id"]

    def __str__(self):
        return f"{self.import_code} - {self.import_date.strftime('%d/%m/%Y')}"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total for item in self.items.all())

    @staticmethod
    def generate_new_code():
        prefix = "PN"
        last = ImportReceipt.objects.filter(import_code__startswith=prefix).order_by("-import_code").first()

        if not last:
            return "PN0001"

        last_number = last.import_code.replace(prefix, "")
        if not last_number.isdigit():
            return "PN0001"

        new_number = int(last_number) + 1
        return f"{prefix}{new_number:04d}"

    def save(self, *args, **kwargs):
        if not self.export_code:
            self.export_code = ExportReceipt.generate_new_code()
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        # nếu có ASN mà chưa set supplier → tự set
        if self.asn and not self.supplier:
            self.supplier = self.asn.supplier

        # tự sinh code nếu chưa có
        if not self.import_code:
            self.import_code = self._generate_import_code()

        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        # ✅ Nếu chọn ASN thì supplier phải trùng
        if self.asn and self.supplier and self.asn.supplier != self.supplier:
            raise ValidationError("Nhà cung ứng của phiếu nhập phải trùng với phiếu ASN được chọn.")


class ImportItem(models.Model):
    import_receipt = models.ForeignKey(
        ImportReceipt,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Dòng ASN gốc (nếu nhập theo ASN)
    asn_item = models.ForeignKey(
        "ASNItem",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Dòng ASN"
    )

    product = models.ForeignKey("SupplierProduct", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    unit = models.CharField(max_length=20)
    location = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)

    @property
    def total(self):
        base = self.quantity * self.unit_price
        return base - (base * self.discount_percent / 100)

    def save(self, *args, **kwargs):
        # Auto sync từ ASNItem nếu có
        if self.asn_item_id:
            self.product = self.asn_item.product
            if not self.unit_price:
                self.unit_price = self.asn_item.unit_price
            if not self.unit:
                self.unit = self.asn_item.unit
            if not self.expiry_date:
                self.expiry_date = self.asn_item.expiry_date

        super().save(*args, **kwargs)

        # Cập nhật / tạo lô tồn kho
        lot, created = StockItem.objects.get_or_create(
            source_type="import",
            import_receipt=self.import_receipt,
            product=self.product,
            expiry_date=self.expiry_date,
            defaults={
                "quantity": self.quantity,
                "unit": self.unit,
                "location": self.location,
                "unit_price": self.unit_price,
            },
        )

        if not created:
            lot.quantity += self.quantity
            lot.unit = self.unit
            lot.location = self.location
            lot.unit_price = self.unit_price
            lot.save()


# ===================== TỒN KHO (LÔ HÀNG) =====================
class StockItem(models.Model):
    STATUS_CHOICES = [
        ("valid", "Còn hạn"),
        ("nearly_expired", "Cận hạn"),
        ("expired", "Hết hạn"),
    ]

    SOURCE_CHOICES = [
        ("import", "Nhập kho"),
        ("return", "Hoàn hàng"),
    ]

    import_receipt = models.ForeignKey(
        "ImportReceipt",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stock_items",
        verbose_name="Phiếu nhập",
    )
    return_receipt = models.ForeignKey(
        "ReturnReceipt",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stock_items",
        verbose_name="Phiếu hoàn",
    )

    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="import",
        verbose_name="Loại lô",
    )

    product = models.ForeignKey(
        "SupplierProduct",
        on_delete=models.CASCADE,
        verbose_name="Sản phẩm NCC"
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name="Tồn kho")
    unit = models.CharField(max_length=20, verbose_name="Đơn vị")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vị trí")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Hạn sử dụng")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Đơn giá nhập")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="valid", verbose_name="Trạng thái")

    def update_status(self):
        if self.expiry_date:
            today = date.today()
            if self.expiry_date < today:
                self.status = "expired"
            elif self.expiry_date <= today + timedelta(days=30):
                self.status = "nearly_expired"
            else:
                self.status = "valid"
        else:
            self.status = "valid"

    def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.source_type == "import" and self.import_receipt:
            code = self.import_receipt.import_code
        elif self.source_type == "return" and self.return_receipt:
            code = self.return_receipt.return_code
        else:
            code = "N/A"
        return f"{self.product.name} - {self.quantity} {self.unit} ({code})"


# ===================== PHIẾU XUẤT KHO =====================
from django.core.exceptions import ValidationError


class ExportReceipt(models.Model):
    export_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phiếu xuất")
    export_date = models.DateField(default=date.today, verbose_name="Ngày xuất")
    receiver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Người nhận")
    receiver_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="SĐT người nhận")
    destination = models.CharField(max_length=200, verbose_name="Nơi nhận")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Người tạo")

    def __str__(self):
        return self.export_code

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum((item.total or 0) for item in self.items.all())

    @property
    def total_discount(self):
        total = Decimal("0.00")
        for it in self.items.all():
            base = (it.unit_price or 0) * (it.quantity or 0)
            disc = base * (getattr(it, "discount_percent", 0) or 0) / 100
            total += disc
        return total

    @staticmethod
    def generate_new_code():
        prefix = "XK"
        last = ExportReceipt.objects.filter(export_code__startswith=prefix).order_by("-export_code").first()

        if not last:
            return "XK0001"

        last_number = last.export_code.replace(prefix, "")
        if not last_number.isdigit():
            return "XK0001"

        new_number = int(last_number) + 1
        return f"{prefix}{new_number:04d}"

    def save(self, *args, **kwargs):
        if not self.export_code:
            self.export_code = ExportReceipt.generate_new_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Phiếu xuất kho"
        verbose_name_plural = "Phiếu xuất kho"


class ExportItem(models.Model):
    receipt = models.ForeignKey(ExportReceipt, on_delete=models.CASCADE, related_name="items")
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    unit = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # luôn dùng đơn giá của lô hàng
        if self.stock_item and (not self.unit_price or self.unit_price == 0):
            self.unit_price = self.stock_item.unit_price

        base = self.quantity * self.unit_price
        self.total = base - (base * self.discount_percent / 100)

        # trừ tồn kho
        if self.pk:
            old = ExportItem.objects.get(pk=self.pk)
            delta = self.quantity - old.quantity
        else:
            delta = self.quantity

        si = StockItem.objects.get(pk=self.stock_item_id)
        if si.quantity < delta:
            raise ValidationError("Không đủ tồn kho")
        si.quantity -= delta
        si.save()

        super().save(*args, **kwargs)


# ===================== PHIẾU HOÀN =====================
class ReturnReceipt(models.Model):
    return_code = models.CharField(max_length=20, primary_key=True)
    return_date = models.DateField(default=date.today)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    export_receipt = models.ForeignKey(
        ExportReceipt,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Phiếu xuất tương ứng"
    )

    def __str__(self):
        return self.return_code

    @property
    def total_quantity(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def total_price(self):
        return sum(i.total for i in self.items.all())


    @staticmethod
    def generate_new_code():
        prefix = "HH"
        last = ReturnReceipt.objects.filter(return_code__startswith=prefix).order_by("-return_code").first()

        if not last:
            return "HH0001"

        last_number = last.return_code.replace(prefix, "")
        if not last_number.isdigit():
            return "HH0001"

        new_number = int(last_number) + 1
        return f"{prefix}{new_number:04d}"
    def save(self, *args, **kwargs):
        if not self.return_code:
            self.return_code = ReturnReceipt.generate_new_code()
        super().save(*args, **kwargs)


class ReturnItem(models.Model):
    receipt = models.ForeignKey(
        ReturnReceipt,
        on_delete=models.CASCADE,
        related_name="items"
    )

    export_item = models.ForeignKey(
        "ExportItem",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Dòng phiếu xuất"
    )

    product = models.ForeignKey("SupplierProduct", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    location = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)

    reason = models.CharField(max_length=255, blank=True, null=True)
    detail_note = models.Textarea = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # 🔥 THÊM FIELD LÔ TỒN KHO CHO HÀNG HOÀN
    stock_item = models.OneToOneField(
        StockItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="return_item",
        verbose_name="Lô tồn kho hoàn"
    )

    def save(self, *args, **kwargs):
        from django.db.models import Sum

        if self.export_item:
            ei = self.export_item
            self.product = ei.stock_item.product
            self.unit = ei.unit
            self.unit_price = ei.unit_price
            self.expiry_date = ei.stock_item.expiry_date
            self.location = ei.stock_item.location

            exported_qty = ei.quantity
            returned_qty = ReturnItem.objects.filter(
                export_item=ei
            ).exclude(pk=self.pk).aggregate(
                total=Sum("quantity")
            )["total"] or 0

            if self.quantity + returned_qty > exported_qty:
                raise ValidationError("Số lượng hoàn vượt quá số lượng đã xuất.")

        base = self.quantity * self.unit_price
        self.total = base

        super().save(*args, **kwargs)

        if self.quantity <= 0:
            return

        # tạo / update lô tồn kho từ hàng hoàn
        if not self.stock_item:
            lot = StockItem.objects.create(
                source_type="return",
                return_receipt=self.receipt,
                product=self.product,
                quantity=self.quantity,
                unit=self.unit,
                expiry_date=self.expiry_date,
                location=self.location,
                unit_price=self.unit_price,
            )
            self.stock_item = lot
            super().save(update_fields=["stock_item"])
        else:
            lot = self.stock_item
            lot.quantity = self.quantity
            lot.unit = self.unit
            lot.location = self.location
            lot.expiry_date = self.expiry_date
            lot.unit_price = self.unit_price
            lot.save()

    def delete(self, *args, **kwargs):
        # xóa luôn lô tồn kho hoàn nếu có
        if self.stock_item_id:
            self.stock_item.delete()
        super().delete(*args, **kwargs)


# ===================== ĐƠN ĐẶT HÀNG (PO) =====================
class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Chờ duyệt"),
        ("approved", "Đã duyệt"),
        ("closed", "Hoàn tất"),
    ]

    po_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã PO")
    supplier = models.ForeignKey("Supplier", on_delete=models.CASCADE, verbose_name="Nhà cung ứng")
    created_date = models.DateField(auto_now_add=True, verbose_name="Ngày tạo")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Trạng thái")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")

    def __str__(self):
        return self.po_code

    @staticmethod
    def generate_new_code():
        """
        Sinh mã PO001, PO002, PO003...
        Dựa trên mã lớn nhất hiện có.
        """
        prefix = "PO"
        last = PurchaseOrder.objects.filter(po_code__startswith=prefix).order_by("-po_code").first()

        if not last:
            return "PO001"

        last_number = last.po_code.replace(prefix, "")
        if not last_number.isdigit():
            return "PO001"

        new_number = int(last_number) + 1
        return f"{prefix}{new_number:03d}"

    def save(self, *args, **kwargs):
        if not self.po_code:
            self.po_code = PurchaseOrder.generate_new_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.po_code} ({self.get_status_display()})"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self):
        return sum(item.total for item in self.items.all())

    class Meta:
        verbose_name = "Đơn đặt hàng (PO)"
        verbose_name_plural = "Đơn đặt hàng (PO)"
        ordering = ["-created_date"]


from django.db.models import Sum as DjangoSum  # tránh đè Sum ở dưới


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="PO"
    )

    product = models.ForeignKey(
        "SupplierProduct",
        on_delete=models.CASCADE,
        verbose_name="Sản phẩm NCC"
    )

    quantity = models.PositiveIntegerField(verbose_name="Số lượng")
    unit = models.CharField(max_length=20, default="Thùng", verbose_name="Đơn vị")

    unit_price = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Đơn giá NCC"
    )
    total = models.DecimalField(
        max_digits=20, decimal_places=2,
        default=0,
        verbose_name="Thành tiền"
    )

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.unit}"

    class Meta:
        verbose_name = "Sản phẩm đặt hàng"
        verbose_name_plural = "Chi tiết đơn đặt hàng"

    def clean(self):
        if self.po_id and self.product_id:
            if self.product.supplier_id != self.po.supplier_id:
                raise ValidationError("Sản phẩm không thuộc nhà cung ứng của PO đã chọn.")
        super().clean()

    def save(self, *args, **kwargs):
        if self.product_id and (not self.unit_price or self.unit_price == 0):
            self.unit_price = self.product.unit_price

        self.total = (self.unit_price or 0) * (self.quantity or 0)
        super().save(*args, **kwargs)


# ===================== ASN (THÔNG BÁO GIAO HÀNG) =====================
from django.db.models import Sum, F, ExpressionWrapper, DecimalField as DjDecimalField


class ASN(models.Model):
    STATUS_CHOICES = [
        ("not_delivered", "Chưa giao"),
        ("delivering", "Đang giao"),
        ("delivered", "Đã giao"),
    ]
    asn_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã ASN")
    po = models.ForeignKey("PurchaseOrder", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Đơn đặt hàng (PO)")
    supplier = models.ForeignKey("Supplier", on_delete=models.CASCADE, verbose_name="Nhà cung ứng")
    deliverer_name = models.CharField(max_length=100, verbose_name="Người giao hàng")
    deliverer_phone = models.CharField(max_length=20, verbose_name="SĐT người giao")
    expected_date = models.DateField(verbose_name="Ngày dự kiến giao")
    created_date = models.DateField(auto_now_add=True, verbose_name="Ngày tạo")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="not_delivered",
        verbose_name="Trạng thái giao"
    )

    def __str__(self):
        return f"{self.asn_code}" + (f" (PO: {self.po.po_code})" if self.po else "")

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_value(self):
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        result = self.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField(max_digits=20, decimal_places=2)
                )
            )
        )['total']
        return result or 0

    @staticmethod
    def generate_new_code():
        prefix = "ASN"
        last = ASN.objects.filter(asn_code__startswith=prefix).order_by("-asn_code").first()

        if not last:
            return "ASN0001"

        last_number = last.asn_code.replace(prefix, "")
        if not last_number.isdigit():
            return "ASN0001"

        new_number = int(last_number) + 1
        return f"{prefix}{new_number:04d}"

    def save(self, *args, **kwargs):
        if not self.asn_code:
            self.asn_code = ASN.generate_new_code()
        super().save(*args, **kwargs)

    def clean(self):
        # ✅ Nếu có PO thì nhà cung ứng của ASN phải trùng PO
        if self.po and self.supplier and self.po.supplier_id != self.supplier_id:
            raise ValidationError("Nhà cung ứng của ASN phải trùng với nhà cung ứng của PO.")
        super().clean()

    class Meta:
        verbose_name = "Phiếu giao hàng (ASN)"
        verbose_name_plural = "Phiếu giao hàng (ASN)"


class ASNItem(models.Model):
    asn = models.ForeignKey(
        ASN,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="ASN"
    )

    product = models.ForeignKey(
        "SupplierProduct",
        on_delete=models.CASCADE,
        verbose_name="Sản phẩm NCC"
    )

    quantity = models.PositiveIntegerField(default=0, verbose_name="Số lượng")
    unit = models.CharField(max_length=20, verbose_name="Đơn vị")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Đơn giá")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Hạn sử dụng")

    @property
    def total_value(self):
        return (self.unit_price or 0) * (self.quantity or 0)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} {self.unit})"

    class Meta:
        verbose_name = "Sản phẩm ASN"
        verbose_name_plural = "Chi tiết ASN"

    def clean(self):
        """
        Ràng buộc: tổng số lượng giao (tất cả ASN cùng PO) không vượt số lượng đặt trong PO.
        """
        if self.asn_id and self.product_id and self.asn.po_id:
            po = self.asn.po

            # SL đặt
            ordered = PurchaseOrderItem.objects.filter(
                po=po,
                product=self.product,
            ).aggregate(total=Sum("quantity"))["total"] or 0

            # SL đã giao (các ASN khác)
            delivered = ASNItem.objects.filter(
                asn__po=po,
                product=self.product,
            ).exclude(pk=self.pk if self.pk else None).aggregate(
                total=Sum("quantity")
            )["total"] or 0

            if self.quantity + delivered > ordered:
                raise ValidationError(
                    f"Số lượng giao vượt quá số lượng trên PO. Tối đa còn lại: {ordered - delivered}."
                )

        super().clean()


# ===================== BÁO CÁO =====================
class Report(models.Model):
    report_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã báo cáo")
    report_date = models.DateField(auto_now_add=True, verbose_name="Ngày tạo báo cáo")
    total_imports = models.PositiveIntegerField(default=0, verbose_name="Số phiếu nhập")
    total_exports = models.PositiveIntegerField(default=0, verbose_name="Số phiếu xuất")
    total_returns = models.PositiveIntegerField(default=0, verbose_name="Số phiếu hoàn")
    total_stock = models.PositiveIntegerField(default=0, verbose_name="Tổng tồn kho")
    total_expired = models.PositiveIntegerField(default=0, verbose_name="Sản phẩm hết hạn")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")

    def __str__(self):
        return f"Báo cáo {self.report_code} - {self.report_date.strftime('%d/%m/%Y')}"

    class Meta:
        ordering = ['-report_date']
        verbose_name = "Báo cáo thống kê"
        verbose_name_plural = "Báo cáo thống kê"


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    send_count = models.PositiveIntegerField(default=1)   # số lần gửi trong 1 giờ

    def is_valid(self):
        return timezone.now() <= self.created_at + timedelta(minutes=5)

