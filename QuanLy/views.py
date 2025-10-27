from django.shortcuts import render
from datetime import datetime
from .models import (
    Category, Product, Supplier,
    ImportReceipt, ExportReceipt, ReturnReceipt,
    PurchaseOrder, ASN, Report
)


# Trang chủ
from django.db.models import Sum
from datetime import date

def index(request):
    today = date.today()
    total_stock = Product.objects.aggregate(total=Sum("quantity"))["total"] or 0
    total_orders_today = PurchaseOrder.objects.filter(created_date=today).count()
    pending_count = (
        PurchaseOrder.objects.filter(status="pending").count()
        + ImportReceipt.objects.filter(status="processing").count()
        + ExportReceipt.objects.filter(status="delivering").count()
    )
    low_stock_count = Product.objects.filter(status="low").count()

    context = {
        "today": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "total_stock": total_stock,
        "total_orders_today": total_orders_today,
        "pending_count": pending_count,
        "low_stock_count": low_stock_count,
    }
    return render(request, "index.html", context)



# Danh mục
def categories(request):
    data = Category.objects.all().order_by("category_code")
    return render(request, "categories.html", {"categories": data})


# Sản phẩm
def products(request):
    data = Product.objects.select_related("category").all().order_by("product_code")
    return render(request, "products.html", {"products": data})


# Nhập kho
def import_goods(request):
    data = ImportReceipt.objects.select_related("product", "supplier").all().order_by("-import_date")
    return render(request, "import.html", {"imports": data})


# Xuất kho
def export_goods(request):
    data = ExportReceipt.objects.select_related("product").all().order_by("-export_date")
    return render(request, "export.html", {"exports": data})


# Hoàn hàng
def return_goods(request):
    data = ReturnReceipt.objects.select_related("product").all().order_by("-return_date")
    return render(request, "return.html", {"returns": data})


# Đơn đặt hàng (PO)
def po(request):
    data = PurchaseOrder.objects.select_related("supplier", "product").all().order_by("-created_date")
    return render(request, "po.html", {"pos": data})

def asn(request):
    data = ASN.objects.select_related("supplier", "product").all().order_by("-created_date")
    return render(request, "asn.html", {"asns": data})


# Nhà cung ứng
def suppliers(request):
    data = Supplier.objects.all().order_by("supplier_code")
    return render(request, "suppliers.html", {"suppliers": data})


# Báo cáo
def reports(request):
    today = date.today()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Mặc định: Tháng này
    if not start_date or not end_date:
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Tổng doanh thu = tổng tiền xuất hàng trong khoảng
    total_revenue = (
        ExportReceipt.objects.filter(export_date__range=[start_date, end_date])
        .aggregate(total=Sum("total_price"))["total"]
        or 0
    )

    # Tổng phiếu nhập
    total_imports = ImportReceipt.objects.filter(import_date__range=[start_date, end_date]).count()

    # Tổng phiếu xuất
    total_exports = ExportReceipt.objects.filter(export_date__range=[start_date, end_date]).count()

    # Tỷ lệ hoàn hàng (phiếu ReturnReceipt / phiếu ExportReceipt)
    total_returns = ReturnReceipt.objects.filter(return_date__range=[start_date, end_date]).count()
    return_rate = 0
    if total_exports > 0:
        return_rate = round((total_returns / total_exports) * 100, 2)

    context = {
        "today": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "start_date": start_date,
        "end_date": end_date,
        "total_revenue": total_revenue,
        "total_imports": total_imports,
        "total_exports": total_exports,
        "return_rate": return_rate,
    }
    return render(request, "reports.html", context)
