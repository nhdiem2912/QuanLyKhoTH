from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.utils import timezone

# ===================== DANH MỤC =====================
class Category(models.Model):
    category_code = models.CharField(max_length=10, primary_key=True, verbose_name="Mã danh mục")
    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True,
        verbose_name="Ảnh danh mục")
    def __str__(self):
        return f"{self.name} ({self.category_code})"


# ===================== SẢN PHẨM KINH DOANH (MASTER) =====================
class ProductMaster(models.Model):
    product_code = models.CharField(max_length=10, primary_key=True, verbose_name="Mã sản phẩm")
    name = models.CharField(max_length=200, verbose_name="Tên sản phẩm")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Danh mục")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Đang kinh doanh"), ("inactive", "Ngừng kinh doanh")],
        default="active",
        verbose_name="Trạng thái"
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        verbose_name="Ảnh sản phẩm"
    )
    def __str__(self):
        return f"{self.product_code} - {self.name}"


# ===================== NHÀ CUNG ỨNG =====================
class Supplier(models.Model):
    supplier_code = models.CharField(max_length=10, primary_key=True, verbose_name="Mã NCC")
    company_name = models.CharField(max_length=200, verbose_name="Tên công ty")
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


# ===================== NHẬP KHO =====================
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal

# Giả sử bạn đã có:
# from .models import Supplier, ProductMaster, StockItem


class ImportReceipt(models.Model):
    import_code = models.CharField(
        max_length=20, unique=True, verbose_name="Mã phiếu nhập"
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Nhà cung ứng"
    )
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


class ImportItem(models.Model):
    import_receipt = models.ForeignKey(
        ImportReceipt, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT)
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
        super().save(*args, **kwargs)

        lot, created = StockItem.objects.get_or_create(
            source_type="import",
            import_receipt=self.import_receipt,
            product=self.product,
            expiry_date=self.expiry_date,
            defaults={
                "quantity": self.quantity,
                "unit": self.unit,
                "location": self.location,
            },
        )

        if not created:
            lot.quantity += self.quantity
            lot.unit = self.unit
            lot.location = self.location
            lot.save()

    def delete(self, *args, **kwargs):
        try:
            lot = StockItem.objects.get(
                source_type="import",
                import_receipt=self.import_receipt,
                product=self.product,
                expiry_date=self.expiry_date,
            )
            lot.quantity -= self.quantity
            if lot.quantity <= 0:
                lot.delete()
            else:
                lot.save()
        except StockItem.DoesNotExist:
            pass

        super().delete(*args, **kwargs)



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

    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, verbose_name="Sản phẩm")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Tồn kho")
    unit = models.CharField(max_length=20, verbose_name="Đơn vị")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vị trí")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Hạn sử dụng")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="valid", verbose_name="Trạng thái")

    def save(self, *args, **kwargs):
        if self.expiry_date:
            days_left = (self.expiry_date - date.today()).days
            if days_left < 0:
                self.status = "expired"
            elif days_left <= 30:
                self.status = "nearly_expired"
            else:
                self.status = "valid"
        else:
            self.status = "valid"

        super().save(*args, **kwargs)

    def __str__(self):
        if self.source_type == "import" and self.import_receipt:
            code = self.import_receipt.import_code
        elif self.source_type == "return" and self.return_receipt:
            code = self.return_receipt.return_code
        else:
            code = "N/A"

        expiry = self.expiry_date.strftime("%d/%m/%Y") if self.expiry_date else "Không HSD"
        status_label = {
            "valid": "Còn hạn",
            "nearly_expired": "Cận hạn",
            "expired": "Hết hạn",
        }.get(self.status, "Không rõ")
        return f"{self.product.name} ({code}) - SL: {self.quantity} - HSD: {expiry} [{status_label}]"

    class Meta:
        ordering = ["expiry_date", "product__product_code"]
        verbose_name = "Hàng tồn kho"
        verbose_name_plural = "Tồn kho"




# ===================== PHIẾU XUẤT KHO =====================
from django.core.exceptions import ValidationError

class ExportReceipt(models.Model):
    export_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phiếu xuất")
    export_date = models.DateField(default=date.today, verbose_name="Ngày xuất")
    destination = models.CharField(max_length=200, verbose_name="Nơi nhận")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Người tạo")

    def __str__(self):
        return self.export_code

    @property
    def total_quantity(self):
        """Tổng số lượng sản phẩm trong phiếu xuất"""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        """Tổng tiền của phiếu xuất"""
        return sum((item.total or 0) for item in self.items.all())

    @property
    def total_discount(self):
        """
        Tổng tiền chiết khấu = Σ( SL * đơn giá * %CK/100 )
        Yêu cầu ExportItem có field discount_percent (Decimal).
        """
        total = Decimal("0.00")
        for it in self.items.all():
            base = (it.unit_price or 0) * (it.quantity or 0)
            disc = base * (getattr(it, "discount_percent", 0) or 0) / 100
            total += disc
        return total

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
        # tính tiền
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

    def delete(self, *args, **kwargs):
        si = self.stock_item
        si.quantity += self.quantity
        si.save()
        super().delete(*args, **kwargs)



# ===================== PHIẾU HOÀN (TRẢ HÀNG VỀ KHO) =====================
class ReturnReceipt(models.Model):
    return_code = models.CharField(max_length=20, primary_key=True)
    return_date = models.DateField(default=date.today)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.return_code

    @property
    def total_quantity(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def total_price(self):
        return sum(i.total for i in self.items.all())


    # 🔥 FIX QUAN TRỌNG: Tự xóa ReturnItem để trigger ReturnItem.delete()
    def delete(self, *args, **kwargs):
        for item in self.items.all():
            item.delete()        # ← gọi đúng logic xóa StockItem

        super().delete(*args, **kwargs)



class ReturnItem(models.Model):
    receipt = models.ForeignKey(ReturnReceipt, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(ProductMaster, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    location = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    reason = models.CharField(max_length=255)
    detail_note = models.TextField(blank=True, null=True)

    stock_item = models.OneToOneField(
        "StockItem", on_delete=models.SET_NULL, null=True, blank=True
    )

    @property
    def total(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.quantity <= 0:
            return

        # chưa có lô → tạo
        if not self.stock_item:
            lot = StockItem.objects.create(
                source_type="return",
                return_receipt=self.receipt,
                product=self.product,
                quantity=self.quantity,
                unit=self.unit,
                expiry_date=self.expiry_date,
                location=self.location,
            )
            self.stock_item = lot
            super().save(update_fields=["stock_item"])
            return

        # đã có → update
        lot = self.stock_item
        lot.quantity = self.quantity
        lot.unit = self.unit
        lot.location = self.location
        lot.expiry_date = self.expiry_date
        lot.save()

    def delete(self, *args, **kwargs):
        # chỉ xóa nếu stock_item tồn tại thực sự
        if self.stock_item_id:
            try:
                self.stock_item.delete()
            except:
                pass
        super().delete(*args, **kwargs)


# ===================== ĐƠN ĐẶT HÀNG (PO) =====================
from django.db import models
from django.contrib.auth.models import User
from datetime import date

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Chờ duyệt"),
        ("approved", "Đã duyệt"),
        ("closed", "Đã đóng"),
    ]

    po_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã PO")
    supplier = models.ForeignKey("Supplier", on_delete=models.CASCADE, verbose_name="Nhà cung ứng")
    created_date = models.DateField(auto_now_add=True, verbose_name="Ngày tạo")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Trạng thái")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")

    def __str__(self):
        return f"{self.po_code} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Đơn đặt hàng (PO)"
        verbose_name_plural = "Đơn đặt hàng (PO)"
        ordering = ["-created_date"]


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items", verbose_name="PO")
    product = models.ForeignKey("ProductMaster", on_delete=models.CASCADE, verbose_name="Sản phẩm")
    quantity = models.PositiveIntegerField(verbose_name="Số lượng")
    unit = models.CharField(max_length=20, default="Thùng", verbose_name="Đơn vị")

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.unit}"

    class Meta:
        verbose_name = "Sản phẩm đặt hàng"
        verbose_name_plural = "Chi tiết đơn đặt hàng"


# ===================== ASN (THÔNG BÁO GIAO HÀNG) =====================
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

class ASN(models.Model):
    asn_code = models.CharField(max_length=20, primary_key=True, verbose_name="Mã ASN")
    po = models.ForeignKey("PurchaseOrder", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Đơn đặt hàng (PO)")
    supplier = models.ForeignKey("Supplier", on_delete=models.CASCADE, verbose_name="Nhà cung ứng")
    deliverer_name = models.CharField(max_length=100, verbose_name="Người giao hàng")
    deliverer_phone = models.CharField(max_length=20, verbose_name="SĐT người giao")
    expected_date = models.DateField(verbose_name="Ngày dự kiến giao")
    created_date = models.DateField(auto_now_add=True, verbose_name="Ngày tạo")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú")

    def __str__(self):
        return f"{self.asn_code}" + (f" (PO: {self.po.po_code})" if self.po else "")

    @property
    def total_quantity(self):
        """Tổng số lượng tất cả sản phẩm giao"""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_value(self):
        """Tổng tiền = Σ (số lượng × đơn giá)"""
        result = self.items.aggregate(
            total=Sum(ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField(max_digits=20, decimal_places=2)))
        )['total']
        return result or 0

    class Meta:
        verbose_name = "Phiếu giao hàng (ASN)"
        verbose_name_plural = "Phiếu giao hàng (ASN)"


class ASNItem(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name='items', verbose_name="ASN")
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, verbose_name="Sản phẩm")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Số lượng")
    unit = models.CharField(max_length=20, verbose_name="Đơn vị")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Đơn giá")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Hạn sử dụng")

    @property
    def total_value(self):
        """Thành tiền của dòng sản phẩm"""
        return (self.unit_price or 0) * (self.quantity or 0)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} {self.unit})"

    class Meta:
        verbose_name = "Sản phẩm ASN"
        verbose_name_plural = "Chi tiết ASN"



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
