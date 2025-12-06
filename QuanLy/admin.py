from django.contrib import admin
from .models import (
    Category, Supplier, StockItem,
    ImportReceipt, ImportItem,
    ExportReceipt, ExportItem,
    ReturnReceipt, ReturnItem,
    PurchaseOrder, PurchaseOrderItem,
    ASN, ASNItem, Report
)


# ===================== CATEGORY =====================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_code", "name", "description")
    search_fields = ("category_code", "name")


# ===================== SUPPLIER =====================
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_code", "company_name", "contact_name", "phone", "status")
    search_fields = ("supplier_code", "company_name", "contact_name")
    list_filter = ("status",)


# ===================== STOCK ITEM =====================
@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        "import_receipt", "product", "quantity", "unit","unit_price", "location", "expiry_date", "status"
    )
    list_filter = ("status", "import_receipt__supplier", "product__category")
    search_fields = ("product__name", "import_receipt__import_code")
    ordering = ("-import_receipt__import_date",)
    readonly_fields = ("status",)
    date_hierarchy = "expiry_date"


# ===================== IMPORT RECEIPT =====================
class ImportItemInline(admin.TabularInline):
    model = ImportItem
    extra = 0


@admin.register(ImportReceipt)
class ImportReceiptAdmin(admin.ModelAdmin):
    list_display = ("import_code", "supplier", "import_date", "total_quantity", "total_price", "created_by")
    list_filter = ("supplier", "import_date")
    search_fields = ("import_code",)
    inlines = [ImportItemInline]
    readonly_fields = ("total_quantity", "total_price")


# ===================== EXPORT RECEIPT =====================
class ExportItemInline(admin.TabularInline):
    model = ExportItem
    extra = 0


@admin.register(ExportReceipt)
class ExportReceiptAdmin(admin.ModelAdmin):
    list_display = ("export_code", "destination", "export_date", "created_by")
    list_filter = ("export_date",)
    search_fields = ("export_code", "destination")
    inlines = [ExportItemInline]


# ===================== RETURN RECEIPT =====================
class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


@admin.register(ReturnReceipt)
class ReturnReceiptAdmin(admin.ModelAdmin):
    list_display = ("return_code", "return_date", "created_by")
    list_filter = ("return_code", "return_date")
    search_fields = ("return_code",)
    inlines = [ReturnItemInline]


# ===================== PURCHASE ORDER =====================
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_code", "supplier", "created_date", "status", "created_by")
    list_filter = ("status", "supplier")
    search_fields = ("po_code",)
    inlines = [PurchaseOrderItemInline]


# ===================== ASN =====================
class ASNItemInline(admin.TabularInline):
    model = ASNItem
    extra = 0


@admin.register(ASN)
class ASNAdmin(admin.ModelAdmin):
    list_display = ("asn_code", "supplier", "po", "expected_date", "created_by")
    list_filter = ("expected_date", "supplier")
    search_fields = ("asn_code", "po__po_code")
    inlines = [ASNItemInline]


# ===================== REPORT =====================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("report_code", "report_date", "total_imports", "total_stock", "total_expired")
    list_filter = ("report_date",)
    search_fields = ("report_code",)
