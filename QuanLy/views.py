from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from datetime import date
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
import pdfkit

from .models import ImportReceipt, ExportReceipt, ReturnReceipt

from .models import (
    Category, ProductMaster, StockItem,
    Supplier, ImportReceipt, ImportItem,
    ExportReceipt, ExportItem,
    ReturnReceipt, ReturnItem,
    PurchaseOrder, PurchaseOrderItem,
    ASN, ASNItem
)
from .forms import (
    CategoryForm, SupplierForm,
    ProductMasterForm, StockItemForm,
    ImportReceiptForm, ImportItemFormSet,
    ExportReceiptForm, ExportItemFormSet,
    ReturnReceiptForm, ReturnItemFormSet,
    PurchaseOrderForm, PurchaseOrderItemFormSet,
    ASNForm, ASNItemFormSet
)

# ===================== DASHBOARD =====================
@login_required(login_url='login')
def index(request):
    today = date.today()
    context = {
        "today": today.strftime("%d/%m/%Y"),
        "total_products": ProductMaster.objects.count(),
        "total_stock": StockItem.objects.aggregate(total=Sum("quantity"))["total"] or 0,
        "expired": StockItem.objects.filter(status="expired").count(),
        "nearly_expired": StockItem.objects.filter(status="nearly_expired").count(),
        "total_imports": ImportReceipt.objects.count(),
        "total_exports": ExportReceipt.objects.count(),
        "total_returns": ReturnReceipt.objects.count(),
    }
    return render(request, "index.html", context)

from django.db.models import Q, Count

# ===================== DANH MỤC =====================
@login_required(login_url='login')
def categories(request):
    q = request.GET.get("q", "").strip()
    count_filter = request.GET.get("count", "")

    data = Category.objects.all()

    # Tìm kiếm theo mã + tên + mô tả
    if q:
        data = data.filter(
            Q(category_code__icontains=q) |
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    # Lọc theo số lượng sản phẩm
    if count_filter == "0":
        data = data.annotate(total_products=Count("products")).filter(total_products=0)
    elif count_filter == "1":
        data = data.annotate(total_products=Count("products")).filter(total_products__gt=0)

    data = data.order_by("category_code")

    return render(request, "categories.html", {
        "categories": data,
        "q": q,
        "count_filter": count_filter,
    })


@login_required(login_url='login')
def add_category(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Thêm danh mục mới thành công!")
        return redirect("categories")
    return render(request, "category_add.html", {"form": form})

@login_required(login_url='login')
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Đã cập nhật danh mục!")
        return redirect("categories")
    return render(request, "category_edit.html", {"form": form, "category": category})


# ===================== NHÀ CUNG ỨNG =====================
@login_required(login_url='login')
def suppliers(request):
    suppliers = Supplier.objects.all()
    return render(request, "suppliers.html", {"suppliers": suppliers})

@login_required(login_url='login')
def add_supplier(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Thêm nhà cung ứng thành công!")
        return redirect("suppliers")
    return render(request, "supplier_add.html", {"form": form})

@login_required(login_url='login')
def edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Cập nhật nhà cung ứng thành công!")
        return redirect("suppliers")
    return render(request, "supplier_edit.html", {"form": form, "supplier": supplier})


# ===================== SẢN PHẨM KINH DOANH =====================
@login_required(login_url='login')
def product_master_list(request):
    products = ProductMaster.objects.select_related("category").all()
    return render(request, "product_master_list.html", {"products": products})

@login_required(login_url='login')
def add_product_master(request):
    form = ProductMasterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Thêm sản phẩm mới thành công!")
        return redirect("product_master_list")
    return render(request, "product_master_add.html", {"form": form})

@login_required(login_url='login')
def edit_product_master(request, pk):
    product = get_object_or_404(ProductMaster, pk=pk)
    form = ProductMasterForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Cập nhật sản phẩm thành công!")
        return redirect("product_master_list")
    return render(request, "product_master_edit.html", {"form": form, "product": product})

@login_required(login_url='login')
def delete_product_master(request, pk):
    product = get_object_or_404(ProductMaster, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, f"✅ Đã xóa sản phẩm {product.name} thành công.")
        return redirect("product_master_list")
    return render(request, "product_master_confirm_delete.html", {"product": product})


# ===================== TỒN KHO =====================
from django.db.models import Case, When, Value, IntegerField, Q
from .models import StockItem, Category
from django.db import models

@login_required(login_url='login')
def stock_list(request):
    """Trang quản lý tồn kho có bộ lọc nâng cao"""
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    location_filter = request.GET.get('location', '').strip()

    # Lấy danh sách tất cả category và location để fill vào select box
    categories = Category.objects.all().order_by("name")
    locations = StockItem.objects.exclude(location__isnull=True).exclude(location="").values_list("location", flat=True).distinct()

    # Lọc tồn kho
    stocks = StockItem.objects.select_related("product", "product__category", "import_receipt")

    # Tìm kiếm theo nhiều trường
    if query:
        stocks = stocks.filter(
            models.Q(import_receipt__import_code__icontains=query) |
            models.Q(return_receipt__return_code__icontains=query) |
            models.Q(product__product_code__icontains=query) |
            models.Q(product__name__icontains=query) |
            models.Q(location__icontains=query)
        )

    # Lọc theo danh mục
    if category_filter:
        stocks = stocks.filter(product__category__name__icontains=category_filter)

    # Lọc theo vị trí
    if location_filter:
        stocks = stocks.filter(location__icontains=location_filter)

    # Lọc theo trạng thái
    if status_filter:
        stocks = stocks.filter(status=status_filter)

    # Sắp xếp ưu tiên: Cận hạn → Còn hạn → Hết hạn
    sort_order = models.Case(
        models.When(status="nearly_expired", then=models.Value(0)),
        models.When(status="valid", then=models.Value(1)),
        models.When(status="expired", then=models.Value(2)),
        default=models.Value(3),
        output_field=models.IntegerField()
    )
    stocks = stocks.order_by(sort_order, "-import_receipt__import_date")

    for s in stocks:
        s.save()  # cập nhật trạng thái hạn nếu cần

    return render(request, "stock_list.html", {
        "stocks": stocks,
        "categories": categories,
        "locations": locations,
        "query": query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "location_filter": location_filter,
    })


@login_required(login_url='login')
def edit_stock(request, pk):
    stock = get_object_or_404(StockItem, pk=pk)
    form = StockItemForm(request.POST or None, instance=stock)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Cập nhật tồn kho thành công!")
        return redirect("stock_list")
    return render(request, "stock_edit.html", {"form": form, "stock": stock})


# ===================== NHẬP KHO =====================
@login_required(login_url='login')
def import_list(request):
    imports = ImportReceipt.objects.select_related("supplier").prefetch_related("items__product").order_by("-import_date")
    return render(request, "import_list.html", {"imports": imports})


@login_required(login_url='login')
@transaction.atomic
def create_import(request):

    form = ImportReceiptForm(request.POST or None)
    formset = ImportItemFormSet(request.POST or None, prefix="items")

    if request.method == "POST":

        if form.is_valid() and formset.is_valid():

            receipt = form.save(commit=False)
            receipt.created_by = request.user
            receipt.save()

            saved = 0
            formset.instance = receipt
            items = formset.save(commit=False)

            for item in items:
                if not item.product or item.quantity <= 0:
                    continue

                item.import_receipt = receipt
                item.save()      # ImportItem.save() sẽ tự tạo StockItem
                saved += 1

            if saved == 0:
                receipt.delete()
                messages.warning(request, "⚠️ Chưa có sản phẩm hợp lệ.")
                return redirect("import_list")

            messages.success(request, f"✅ Đã tạo phiếu nhập {receipt.import_code}.")
            return redirect("import_list")

        messages.error(request, "❌ Vui lòng kiểm tra dữ liệu.")

    return render(request, "import_create.html", {"form": form, "formset": formset})

# ===================== DELETE IMPORT =====================
@transaction.atomic
@login_required(login_url='login')
def delete_import(request, code):
    # LẤY THEO MÃ PHIẾU NHẬP (import_code), KHÔNG PHẢI pk
    receipt = get_object_or_404(ImportReceipt, import_code=code)

    # Trừ tồn kho / xóa lô tương ứng
    for item in receipt.items.all():
        item.delete()   # ImportItem.delete() đã xử lý StockItem

    # Xóa phiếu nhập
    receipt.delete()

    messages.success(request, f"🗑️ Đã xóa phiếu nhập {code}.")
    return redirect("import_list")

import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings

@login_required(login_url='login')
def import_export_pdf(request, code):
    """
    In phiếu nhập kho dạng PDF
    """
    receipt = get_object_or_404(ImportReceipt, import_code=code)
    html = render_to_string('import_pdf.html', {'receipt': receipt})

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(
        html,
        False,
        configuration=config,
        options={
            'encoding': 'utf-8',
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-bottom': '15mm',
            'margin-left': '10mm',
            'margin-right': '10mm',
        },
    )

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=\"PhieuNhap_{receipt.import_code}.pdf\"'
    return response


# ===================== XUẤT KHO =====================
@login_required(login_url='login')
def export_list(request):
    exports = ExportReceipt.objects.prefetch_related("items__stock_item__product").order_by("-export_date")
    return render(request, "export_list.html", {"exports": exports})


@login_required(login_url='login')
@transaction.atomic
def create_export(request):

    form = ExportReceiptForm(request.POST or None)
    formset = ExportItemFormSet(request.POST or None, prefix="items")
    if not form.is_valid():
        print("FORM ERROR:", form.errors)

    if not formset.is_valid():
        print("FORMSET ERROR:", formset.errors)

    if request.method == "POST":
        print("=== DEBUG EXPORT FORM ===")
        print("POST DATA:", request.POST)

        if form.is_valid() and formset.is_valid():

            receipt = form.save(commit=False)
            receipt.created_by = request.user
            receipt.save()

            saved = 0
            for f in formset:

                if not f.cleaned_data or f.cleaned_data.get("DELETE", False):
                    continue

                item = f.save(commit=False)
                if not item.stock_item:
                    continue  # tránh lỗi "ExportItem has no stock_item"

                # kiểm tra tồn kho đủ
                if item.quantity > item.stock_item.quantity:
                    messages.error(request, "❌ Số lượng vượt tồn kho.")
                    raise transaction.TransactionManagementError

                item.receipt = receipt
                item.save()  # ExportItem.save() sẽ tự trừ tồn kho
                saved += 1

            if saved == 0:
                receipt.delete()
                messages.error(request, "❌ Không có dòng hợp lệ.")
                return redirect("export_list")

            messages.success(request, f"✅ Đã tạo phiếu xuất {receipt.export_code}.")
            return redirect("export_list")

        messages.error(request, "❌ Lỗi dữ liệu.")

    return render(request, "export_create.html", {"form": form, "formset": formset})


@login_required(login_url='login')
@transaction.atomic
def delete_export(request, code):

    receipt = get_object_or_404(ExportReceipt, export_code=code)

    for item in receipt.items.select_related("stock_item"):
        si = item.stock_item
        si.quantity += item.quantity
        si.save()

        item.delete()

    receipt.delete()

    messages.success(request, f"🗑️ Đã xóa phiếu xuất {code} và hoàn tồn.")
    return redirect("export_list")

# views.py
import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

@login_required(login_url='login')
def export_export_pdf(request, code):
    """
    In phiếu xuất kho dạng PDF
    """
    receipt = get_object_or_404(ExportReceipt, export_code=code)
    html = render_to_string('export_pdf.html', {'receipt': receipt})

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(
        html,
        False,
        configuration=config,
        options={
            'encoding': 'utf-8',
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-bottom': '15mm',
            'margin-left': '10mm',
            'margin-right': '10mm',
        },
    )

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=\"PhieuXuat_{receipt.export_code}.pdf\"'
    return response



# ------------------------ DANH SÁCH PHIẾU HOÀN ------------------------
# ------------------------ DANH SÁCH PHIẾU HOÀN ------------------------
# ===================== HOÀN HÀNG =====================
@login_required(login_url='login')
def return_list(request):
    returns = ReturnReceipt.objects.prefetch_related("items").order_by("-return_date")
    return render(request, "return_list.html", {"returns": returns})



# ------------------------ TẠO PHIẾU HOÀN ------------------------


# ------------------------ TẠO PHIẾU HOÀN ------------------------
@login_required(login_url='login')
@transaction.atomic
def create_return(request):
    form = ReturnReceiptForm(request.POST or None)
    formset = ReturnItemFormSet(request.POST or None, prefix="items", queryset=ReturnItem.objects.none())

    if request.method == "POST":

        if form.is_valid() and formset.is_valid():

            receipt = form.save(commit=False)
            receipt.created_by = request.user
            receipt.save()

            saved = 0

            for f in formset:
                if not f.cleaned_data or f.cleaned_data.get("DELETE", False):
                    continue

                item = f.save(commit=False)

                if item.quantity <= 0:
                    continue

                item.receipt = receipt
                item.save()  # ReturnItem.save() tự tạo StockItem(source=return)
                saved += 1

            if saved == 0:
                receipt.delete()
                messages.error(request, "❌ Không có dòng hợp lệ.")
                return redirect("return_list")

            messages.success(request, f"✅ Đã tạo phiếu hoàn {receipt.return_code}.")
            return redirect("return_list")

        messages.error(request, "❌ Dữ liệu không hợp lệ.")

    return render(request, "return_create.html", {"form": form, "formset": formset})


@login_required(login_url='login')
@transaction.atomic
def delete_return(request, code):

    receipt = get_object_or_404(ReturnReceipt, return_code=code)

    for item in receipt.items.all():
        # nếu có lô tồn kho thì xóa
        if item.stock_item_id:
            item.stock_item.delete()
        item.delete()

    receipt.delete()

    messages.success(request, f"🗑️ Đã xóa phiếu hoàn {code}.")
    return redirect("return_list")



from .models import ReturnReceipt

@login_required(login_url='login')
def return_export_pdf(request, code):
    """
    In phiếu hoàn hàng dạng PDF
    """
    receipt = get_object_or_404(ReturnReceipt, return_code=code)
    html = render_to_string('return_pdf.html', {'receipt': receipt})

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(
        html,
        False,
        configuration=config,
        options={
            'encoding': 'utf-8',
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-bottom': '15mm',
            'margin-left': '10mm',
            'margin-right': '10mm',
        },
    )

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=\"PhieuHoan_{receipt.return_code}.pdf\"'
    return response





# ===================== ĐƠN ĐẶT HÀNG (PO) =====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import PurchaseOrder
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet

@login_required(login_url='login')
def po_list(request):
    pos = PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("items__product").order_by("-created_date")
    return render(request, "po_list.html", {"pos": pos})

@login_required(login_url='login')
@transaction.atomic
def create_po(request):
    form = PurchaseOrderForm(request.POST or None)
    formset = PurchaseOrderItemFormSet(request.POST or None)
    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            formset.instance = po
            formset.save()
            messages.success(request, f"✅ Đã tạo đơn đặt hàng {po.po_code} thành công!")
            return redirect("po_list")
        messages.error(request, "❌ Dữ liệu chưa hợp lệ, vui lòng kiểm tra lại.")
    return render(request, "po_create.html", {"form": form, "formset": formset})

@login_required(login_url='login')
@transaction.atomic
def po_edit(request, code):
    po = get_object_or_404(PurchaseOrder, pk=code)
    form = PurchaseOrderForm(request.POST or None, instance=po)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Đã cập nhật đơn đặt hàng {po.po_code}.")
            return redirect("po_list")
        messages.error(request, "❌ Cập nhật thất bại, vui lòng kiểm tra lại.")
    return render(request, "po_edit.html", {"form": form, "po": po})

@login_required(login_url='login')
def delete_po(request, code):
    po = get_object_or_404(PurchaseOrder, pk=code)
    po.delete()
    messages.success(request, f"🗑️ Đã xóa đơn đặt hàng {code} thành công.")
    return redirect("po_list")


# ===================== ASN =====================
from datetime import date, timedelta
from django.db.models import Sum, F
from .models import ASN, ASNItem
from .forms import ASNForm, ASNItemFormSet
@login_required(login_url='login')



@login_required(login_url='login')


def asn_list(request):
    today = date.today()
    asns = ASN.objects.prefetch_related("items__product", "po", "supplier").order_by("-expected_date")
    return render(request, "asn_list.html", {
        "asns": asns,
        "today": today,
        "today_plus_30": today + timedelta(days=30),
    })


@login_required(login_url='login')
@transaction.atomic
def create_asn(request):
    form = ASNForm(request.POST or None)
    formset = ASNItemFormSet(request.POST or None)
    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            asn = form.save(commit=False)
            asn.created_by = request.user
            asn.save()
            formset.instance = asn
            formset.save()
            messages.success(request, f"✅ Phiếu ASN {asn.asn_code} đã được tạo!")
            return redirect("asn_list")
        else:
            messages.error(request, "❌ Dữ liệu không hợp lệ!")
    return render(request, "asn_create.html", {"form": form, "formset": formset})

def asn_export_pdf(request, code):
    asn = get_object_or_404(ASN, asn_code=code)
    return render(request, "asn_pdf.html", {"asn": asn})
# ===================== BÁO CÁO =====================
@login_required(login_url='login')
def reports(request):
    today = date.today()
    start_date = request.GET.get("start_date") or today.replace(day=1).strftime("%Y-%m-%d")
    end_date = request.GET.get("end_date") or today.strftime("%Y-%m-%d")

    total_imports = ImportReceipt.objects.filter(import_date__range=[start_date, end_date]).count()
    total_exports = ExportReceipt.objects.filter(export_date__range=[start_date, end_date]).count()
    total_returns = ReturnReceipt.objects.filter(return_date__range=[start_date, end_date]).count()
    total_stock = StockItem.objects.aggregate(total=Sum("quantity"))["total"] or 0
    expired = StockItem.objects.filter(status="expired").count()
    nearly = StockItem.objects.filter(status="nearly_expired").count()

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "total_imports": total_imports,
        "total_exports": total_exports,
        "total_returns": total_returns,
        "total_stock": total_stock,
        "expired": expired,
        "nearly": nearly,
    }
    return render(request, "reports.html", context)
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

@login_required(login_url='login')
def delete_asn(request, code):
    """Xóa phiếu giao hàng ASN cùng các chi tiết liên quan."""
    asn = get_object_or_404(ASN, pk=code)
    asn.delete()
    messages.success(request, f"🗑️ Đã xóa phiếu giao hàng {code} thành công.")
    return redirect("asn_list")