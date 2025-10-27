from django.db import models
from django.contrib.auth.models import User


# DANH MỤC
class Category(models.Model):
    category_code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# SẢN PHẨM
class Product(models.Model):
    product_code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20, default='Hộp')
    location = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Còn hàng'),
            ('low', 'Cận hạn'),
            ('out', 'Hết hàng'),
        ],
        default='available'
    )

    def __str__(self):
        return f"{self.name} ({self.product_code})"


# NHÀ CUNG ỨNG
class Supplier(models.Model):
    supplier_code = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Hoạt động'),
            ('inactive', 'Tạm dừng'),
        ],
        default='active'
    )

    def __str__(self):
        return self.company_name


# PHIẾU NHẬP KHO
class ImportReceipt(models.Model):
    import_code = models.CharField(max_length=10, unique=True)
    import_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=20, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('done', 'Hoàn thành'),
            ('processing', 'Đang xử lý'),
        ],
        default='processing'
    )

    def __str__(self):
        return f"{self.import_code}"


# PHIẾU XUẤT KHO
class ExportReceipt(models.Model):
    export_code = models.CharField(max_length=10, unique=True)
    export_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=20, decimal_places=2)
    destination = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=[
            ('done', 'Hoàn thành'),
            ('delivering', 'Đang giao'),
        ],
        default='delivering'
    )

    def __str__(self):
        return self.export_code


# PHIẾU HOÀN HÀNG
class ReturnReceipt(models.Model):
    return_code = models.CharField(max_length=10, unique=True)
    return_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    return_type = models.CharField(
        max_length=50,
        choices=[
            ('customer', 'Khách hàng hoàn'),
            ('store', 'Cửa hàng hoàn'),
        ]
    )
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=[
            ('done', 'Đã xử lý'),
            ('processing', 'Đang xử lý'),
        ],
        default='done'
    )

    def __str__(self):
        return self.return_code


# ĐƠN ĐẶT HÀNG (PO)
class PurchaseOrder(models.Model):
    po_code = models.CharField(max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20)
    created_date = models.DateField()
    total_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt')], default='pending')

    def __str__(self):
        return self.po_code


# ASN (Thông báo giao hàng)
class ASN(models.Model):
    asn_code = models.CharField(max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20)
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    deliverer_name = models.CharField(max_length=100)
    deliverer_phone = models.CharField(max_length=20)
    created_date = models.DateField()
    expected_date = models.DateField()

    def __str__(self):
        return self.asn_code


# BÁO CÁO
class Report(models.Model):
    report_date = models.DateField(auto_now_add=True)
    total_imports = models.PositiveIntegerField(default=0)
    total_exports = models.PositiveIntegerField(default=0)
    total_returns = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Báo cáo ngày {self.report_date}"
