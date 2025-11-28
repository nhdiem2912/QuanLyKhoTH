from django.db import transaction
from decimal import Decimal
from .models import (
    Category,  StockItem,
    Supplier, SupplierProduct, ImportReceipt, ImportItem,
    ExportReceipt, ExportItem,
    ReturnReceipt, ReturnItem,
    PurchaseOrder, PurchaseOrderItem,
    ASN, ASNItem)
from .forms import (
    CategoryForm, SupplierForm,
    StockItemForm,
    ImportReceiptForm, ImportItemFormSet,
    ExportReceiptForm, ExportItemFormSet,
    ReturnReceiptForm, ReturnItemFormSet,
    PurchaseOrderForm, PurchaseOrderItemFormSet,
    ASNForm, ASNItemFormSet, SupplierProductFormSet,)
from .decorators import group_required, get_permission_flags

# ===================== DASHBOARD TRANG CHỦ =====================
@group_required('Cửa hàng trưởng', 'Nhân viên')
def index(request):
    today = timezone.localdate()

    # --- Đếm phiếu theo hôm nay ---
    import_today = ImportReceipt.objects.filter(import_date=today).count()
    export_today = ExportReceipt.objects.filter(export_date=today).count()
    return_today = ReturnReceipt.objects.filter(return_date=today).count()

    # --- TỔNG SỐ LƯỢNG HÀNG ĐANG LƯU KHO ---
    stock_total = StockItem.objects.aggregate(total=Sum("quantity"))["total"] or 0

    # (nếu bạn muốn giữ thêm các chỉ số khác:)
    expired = StockItem.objects.filter(status="expired").count()
    nearly_expired = StockItem.objects.filter(status="nearly_expired").count()
    total_products = SupplierProduct.objects.values("product_code").distinct().count()

    context = {
        "today": today.strftime("%d/%m/%Y"),

        # tổng tồn kho (dùng cho cả hero + thẻ "Tồn kho hiện tại")
        "stock_total": stock_total,

        # tổng quan hôm nay
        "import_count_today": import_today,
        "export_count_today": export_today,
        "return_count_today": return_today,

        # nếu bạn còn dùng ở nơi khác thì giữ lại:
        "expired": expired,
        "nearly_expired": nearly_expired,
        "total_products": total_products,
    }
    return render(request, "index.html", context)



from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def home_redirect(request):
    user = request.user

    # Superuser → Trang chủ (dashboard)
    if user.is_superuser:
        return redirect('index')

    # Cửa hàng trưởng / Nhân viên
    if user.groups.filter(name__in=['Cửa hàng trưởng', 'Nhân viên']).exists():
        return redirect('index')

    # Nhà cung ứng
    if user.groups.filter(name='Nhà cung ứng').exists():
        return redirect('asn_list')

    # Unknown role → logout
    return redirect('logout')

from django.db.models import Q, Count
from django.db.models.functions import Lower
# ===================== DANH MỤC =====================
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')


def categories(request):
    q = (request.GET.get("q") or "").strip()
    count_filter = request.GET.get("count", "")

    # Base queryset
    data = Category.objects.all()

    # 🔎 BỘ LỌC TÌM KIẾM — không phân biệt hoa/thường + tìm trong sản phẩm
    if q:
        search = q.lower()

        data = data.annotate(
            name_l=Lower("name"),
            code_l=Lower("category_code"),
            desc_l=Lower("description"),
        ).filter(
            Q(name_l__contains=search) |
            Q(code_l__contains=search) |
            Q(desc_l__contains=search) |
            Q(products__name__icontains=search) |
            Q(products__product_code__icontains=search)
        ).distinct()

    # 🔢 Lọc theo số lượng sản phẩm
    if count_filter == "0":
        data = data.annotate(total_products=Count("products")).filter(total_products=0)
    elif count_filter == "1":
        data = data.annotate(total_products=Count("products")).filter(total_products__gt=0)

    data = data.order_by("category_code")

    # 📌 Lấy danh sách sản phẩm duy nhất từ phiếu nhập
    for category in data:
        import_items = ImportItem.objects.filter(
            product__category=category
        ).select_related("product").order_by(
            "product__product_code", "-import_receipt__import_date"
        )

        unique_products = {}
        for item in import_items:
            code = item.product.product_code
            if code not in unique_products:
                unique_products[code] = {
                    "product_code": code,
                    "name": item.product.name,
                    "unit_price": item.unit_price,
                }

        category.products_from_imports = list(unique_products.values())

    return render(request, "categories.html", {
        "categories": data,
        "q": q,
        "count_filter": count_filter,
    })



@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def add_category(request):
    form = CategoryForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thêm danh mục mới thành công!")
        return redirect("categories")
    return render(request, "category_add.html", {"form": form})


@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, " Đã cập nhật danh mục!")
        return redirect("categories")
    return render(request, "category_edit.html", {"form": form, "category": category})


from django.views.decorators.http import require_POST


@require_POST
@group_required('Cửa hàng trưởng', 'Nhân viên')
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()

    # Nếu là request AJAX (fetch) → trả JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"success": True, "message": "Đã xoá danh mục thành công."})

    # Nếu là request thường → quay về danh sách
    messages.success(request, "Đã xoá danh mục.")
    return redirect('categories')


# ===================== NHÀ CUNG ỨNG =====================
from django.db.models import Q, Count

@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def suppliers(request):
    q = request.GET.get("q", "").strip()
    city = request.GET.get("city", "")
    count_filter = request.GET.get("count", "")

    user = request.user
    perms = get_permission_flags(user)

    if perms["is_supplier"]:
        # username của user NCC = supplier_code
        suppliers = Supplier.objects.filter(supplier_code=user.username)
    else:
        suppliers = Supplier.objects.all()

    # --- Search (Tên, mã, người liên hệ, email, số điện thoại…) ---
    if q:
        suppliers = suppliers.filter(
            Q(company_name__icontains=q) |
            Q(supplier_code__icontains=q) |
            Q(contact_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(address__icontains=q)
        )

    # --- Lọc theo thành phố ---
    if city:
        suppliers = suppliers.filter(address__icontains=city)

    suppliers = suppliers.order_by("company_name")

    perms = get_permission_flags(request.user)

    context = {
        "suppliers": suppliers,
        "q": q,
        "city_filter": city,
        "count_filter": count_filter,
        **perms,  # 🔹 Đẩy toàn bộ cờ quyền xuống template
    }
    return render(request, "suppliers.html", context)


@group_required('Cửa hàng trưởng', 'Nhà cung ứng')
@transaction.atomic
def add_supplier(request):
    supplier_form = SupplierForm(request.POST or None)
    formset = SupplierProductFormSet(request.POST or None)

    if request.method == "POST":
        if supplier_form.is_valid() and formset.is_valid():
            try:
                supplier = supplier_form.save()
                formset.instance = supplier

                instances = formset.save(commit=False)

                for instance in instances:
                    # Bỏ qua dòng trắng
                    if (not instance.product_code
                        and not instance.name
                        and (instance.unit_price is None or instance.unit_price == 0)):
                        continue

                    instance.supplier = supplier

                    # Nếu đã có sản phẩm cùng mã trong NCC này → update thay vì tạo mới
                    existing = SupplierProduct.objects.filter(
                        supplier=supplier,
                        product_code=instance.product_code
                    ).first()

                    if existing and (not instance.pk or existing.pk != instance.pk):
                        existing.name = instance.name
                        existing.category = instance.category
                        existing.unit_price = instance.unit_price
                        existing.is_active = instance.is_active
                        existing.save()
                    else:
                        instance.save()

                # Xóa các dòng được tick DELETE
                for obj in formset.deleted_objects:
                    obj.delete()

                messages.success(request, "Đã thêm nhà cung ứng mới.")
                return redirect("suppliers")
            except Exception as e:
                import traceback
                messages.error(request, f"Lỗi khi lưu: {str(e)}")
                print(f"Error in add_supplier: {str(e)}")
                print(traceback.format_exc())
        else:
            ...
            # (giữ nguyên phần show lỗi như code cũ của bạn)

    return render(request, "supplier_add.html", {
        "form": supplier_form,
        "formset": formset,
    })


@group_required('Cửa hàng trưởng', 'Nhà cung ứng')
@login_required(login_url='login')
@transaction.atomic
def edit_supplier(request, pk):
    user = request.user
    perms = get_permission_flags(user)

    if perms["is_supplier"] and pk != user.username:
        return redirect("suppliers")  # silent redirect

    supplier = get_object_or_404(Supplier, pk=pk)

    supplier_form = SupplierForm(request.POST or None, instance=supplier)
    formset = SupplierProductFormSet(request.POST or None, instance=supplier)

    if request.method == "POST":
        if supplier_form.is_valid() and formset.is_valid():
            try:
                supplier_form.save()

                instances = formset.save(commit=False)
                for instance in instances:
                    if (not instance.product_code
                        and not instance.name
                        and (instance.unit_price is None or instance.unit_price == 0)):
                        continue

                    instance.supplier = supplier

                    existing = SupplierProduct.objects.filter(
                        supplier=supplier,
                        product_code=instance.product_code
                    ).first()

                    if existing and (not instance.pk or existing.pk != instance.pk):
                        existing.name = instance.name
                        existing.category = instance.category
                        existing.unit_price = instance.unit_price
                        existing.is_active = instance.is_active
                        existing.save()
                    else:
                        instance.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                messages.success(request, "Đã cập nhật nhà cung ứng.")
                return redirect("suppliers")
            except Exception as e:
                import traceback
                messages.error(request, f"Lỗi khi lưu: {str(e)}")
                print(f"Error in edit_supplier: {str(e)}")
                print(traceback.format_exc())
        else:
            ...
    return render(request, "supplier_edit.html", {
        "form": supplier_form,
        "formset": formset,
        "supplier": supplier
    })




# ===================== TỒN KHO =====================
from django.db.models import Case, When, Value, IntegerField, Q
from .models import StockItem, Category
from django.db import models


@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def stock_list(request):
    """Trang quản lý tồn kho có bộ lọc nâng cao"""
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    location_filter = request.GET.get('location', '').strip()

    # Lấy danh sách tất cả category và location để fill vào select box
    categories = Category.objects.all().order_by("name")
    locations = StockItem.objects.exclude(location__isnull=True)\
                                 .exclude(location="")\
                                 .values_list("location", flat=True)\
                                 .distinct()

    # Lọc tồn kho
    stocks = StockItem.objects.select_related(
        "product",
        "product__category",
        "import_receipt",
        "return_receipt"
    )

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
        output_field=models.IntegerField(),
    )
    stocks = stocks.order_by(sort_order, "-import_receipt__import_date")

    # Cập nhật trạng thái hạn sử dụng nếu cần
    for s in stocks:
        s.save()

    # ⭐ TÍNH TỔNG TỒN KHO (quantity toàn bộ StockItem)
    stock_total = StockItem.objects.aggregate(total=models.Sum("quantity"))["total"] or 0

    return render(request, "stock_list.html", {
        "stocks": stocks,
        "categories": categories,
        "locations": locations,
        "query": query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "location_filter": location_filter,
        "stock_total": stock_total,  # ⭐ THÊM VÀO CONTEXT
    })


@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def edit_stock(request, pk):
    stock = get_object_or_404(StockItem, pk=pk)
    form = StockItemForm(request.POST or None, instance=stock)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cập nhật tồn kho thành công!")
        return redirect("stock_list")
    return render(request, "stock_edit.html", {"form": form, "stock": stock})

from django.db.models import Q, Count
from django.db.models.functions import Lower
# ===================== NHẬP KHO =====================
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')


def import_list(request):
    q = (request.GET.get("q") or "").strip()
    supplier_filter = request.GET.get("supplier", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    count_filter = request.GET.get("count", "")

    imports = ImportReceipt.objects.select_related("supplier") \
        .prefetch_related("items__product")

    # -----------------------------
    # 🔎 LỌC THEO TỪ KHÓA (không phân biệt HOA/THƯỜNG)
    # Tìm theo:
    # - mã phiếu nhập
    # - ghi chú
    # - người tạo
    # - tên nhà cung cấp
    # - mã sản phẩm
    # - tên sản phẩm
    # -----------------------------

    if q:
        search = q.lower()

        imports = imports.annotate(
            import_code_l=Lower("import_code"),
            note_l=Lower("note"),
            creator_l=Lower("created_by__username"),
            supplier_l=Lower("supplier__company_name"),
        ).filter(
            Q(import_code_l__contains=search) |
            Q(note_l__contains=search) |
            Q(creator_l__contains=search) |
            Q(supplier_l__contains=search) |
            Q(items__product__product_code__icontains=q) |
            Q(items__product__name__icontains=q)
        ).distinct()

    # -----------------------------
    # 🏢 LỌC THEO NHÀ CUNG CẤP
    # -----------------------------
    if supplier_filter:
        imports = imports.filter(supplier_id=supplier_filter)

    # -----------------------------
    # 📅 LỌC THEO NGÀY
    # -----------------------------
    if date_from:
        imports = imports.filter(import_date__gte=date_from)

    if date_to:
        imports = imports.filter(import_date__lte=date_to)

    # -----------------------------
    # 🔢 LỌC THEO SỐ LƯỢNG DÒNG SẢN PHẨM
    # -----------------------------
    if count_filter == "0":
        imports = imports.annotate(total_items=Count("items")).filter(total_items=0)
    elif count_filter == "1":
        imports = imports.annotate(total_items=Count("items")).filter(total_items__gt=0)

    imports = imports.order_by("-import_date")

    suppliers = Supplier.objects.all()
    perms = get_permission_flags(request.user)

    return render(request, "import_list.html", {
        "imports": imports,
        "suppliers": suppliers,
        "q": q,
        "supplier_filter": supplier_filter,
        "date_from": date_from,
        "date_to": date_to,
        "count_filter": count_filter,
        **perms,
    })


@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
@transaction.atomic
def create_import(request):
    """
    Tạo phiếu nhập:
    - Nếu chọn ASN: tự fill sản phẩm, SL, đơn giá, đơn vị, hạn dùng từ ASN.
    - Supplier bị khóa theo supplier của ASN.
    """
    categories = Category.objects.all().order_by("name")

    # ============= POST (LƯU) =============
    if request.method == "POST":
        # Lấy ASN đã chọn
        asn = None
        asn_id = request.POST.get("asn")
        if asn_id:
            asn = ASN.objects.filter(pk=asn_id).first()

        # Ép supplier theo ASN (nếu có) để không bị lệch
        post_data = request.POST.copy()
        if asn and asn.supplier_id:
            post_data["supplier"] = str(asn.supplier_id)

        form = ImportReceiptForm(post_data)

        formset = ImportItemFormSet(
            post_data,
            prefix="items",
            form_kwargs={
                "asn": asn,
                "supplier": asn.supplier if asn else None,
            },
        )

        if form.is_valid() and formset.is_valid():
            try:
                receipt = form.save(commit=False)

                # 🔹 Auto sinh mã nếu trống
                if not receipt.import_code:
                    receipt.import_code = ImportReceipt.generate_new_code()

                # Gắn lại ASN & Supplier cho chắc
                if asn:
                    receipt.asn = asn
                    receipt.supplier = asn.supplier

                receipt.created_by = request.user
                receipt.save()

                # gán instance cho formset rồi save luôn
                formset.instance = receipt
                items = formset.save()

                if not items:
                    raise ValueError("Chưa có dòng sản phẩm nào hợp lệ.")

                messages.success(
                    request,
                    f" Đã tạo phiếu nhập {receipt.import_code} thành công."
                )
                return redirect("import_list")

            except Exception as e:
                import traceback
                print("Error when saving import:", e)
                print(traceback.format_exc())
                messages.error(request, f" Lỗi khi lưu phiếu nhập: {e}")
        else:
            # log lỗi chi tiết
            print("IMPORT FORM ERRORS:", form.errors)
            print("IMPORT FORMSET ERRORS:", formset.errors)
            if form.errors:
                for field, errs in form.errors.items():
                    for er in errs:
                        messages.error(request, f" {field}: {er}")
            if formset.errors:
                for i, err_dict in enumerate(formset.errors):
                    for field, errs in err_dict.items():
                        for er in errs:
                            messages.error(
                                request,
                                f"Dòng {i+1} - {field}: {er}"
                            )
            if formset.non_form_errors():
                for er in formset.non_form_errors():
                    messages.error(request, f"{er}")

        # nếu tới đây là có lỗi → render lại form với dữ liệu người dùng
        return render(
            request,
            "import_create.html",
            {
                "form": form,
                "formset": formset,
                "categories": categories,
            },
        )

    # ============= GET (LẦN ĐẦU HOẶC CHỌN ASN) =============
    asn_code = request.GET.get("asn")
    asn = ASN.objects.filter(pk=asn_code).first() if asn_code else None

    # 🔥 Chỉ lấy ASN chưa được nhập kho
    available_asn = ASN.objects.filter(
        importreceipt__asn__isnull=True
    )
    initial = {}
    if asn:
        initial["asn"] = asn
        initial["supplier"] = asn.supplier

    # 🔹 Hiển thị mã PN mới luôn trên form
    initial.setdefault("import_code", ImportReceipt.generate_new_code())

    form = ImportReceiptForm(initial=initial)

    # Nếu có ASN → build formset dựa trên ASNItem
    if asn:
        asn_items = list(asn.items.all())
        total = len(asn_items)

        post_data = {
            "items-TOTAL_FORMS": str(total),
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
        }

        for idx, asn_item in enumerate(asn_items):
            prefix = f"items-{idx}-"
            post_data[prefix + "product"] = str(asn_item.product_id)
            post_data[prefix + "quantity"] = str(asn_item.quantity or 0)
            post_data[prefix + "unit_price"] = str(asn_item.unit_price or 0)
            post_data[prefix + "unit"] = asn_item.unit or ""
            post_data[prefix + "expiry_date"] = (
                asn_item.expiry_date.isoformat()
                if asn_item.expiry_date
                else ""
            )
            post_data[prefix + "location"] = ""
            post_data[prefix + "DELETE"] = ""

        formset = ImportItemFormSet(
            post_data,
            prefix="items",
            form_kwargs={"asn": asn, "supplier": asn.supplier},
        )
    else:
        formset = ImportItemFormSet(
            prefix="items",
            form_kwargs={"asn": None, "supplier": None},
        )

    return render(
        request,
        "import_create.html",
        {
            "form": form,
            "formset": formset,
            "categories": categories,
            "available_asn": available_asn,
        },
    )

@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def import_export_pdf(request, code):
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
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def export_list(request):
    q = request.GET.get("q", "").strip()
    destination = request.GET.get("destination", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    count_filter = request.GET.get("count", "")

    exports = ExportReceipt.objects.prefetch_related(
        "items__stock_item__product"
    )

    # --- Search ---
    if q:
        exports = exports.filter(
            Q(export_code__icontains=q) |
            Q(note__icontains=q) |
            Q(destination__icontains=q) |
            Q(created_by__username__icontains=q) |
            Q(items__stock_item__product__name__icontains=q)
        ).distinct()

    # --- Lọc theo nơi nhận ---
    if destination:
        exports = exports.filter(destination__icontains=destination)

    # --- Lọc theo khoảng ngày ---
    if date_from:
        exports = exports.filter(export_date__gte=date_from)
    if date_to:
        exports = exports.filter(export_date__lte=date_to)

    exports = exports.order_by("-export_date")

    # Danh sách nơi nhận gợi ý
    destinations = (
        ExportReceipt.objects.exclude(destination="")
        .values_list("destination", flat=True)
        .distinct()
    )

    return render(request, "export_list.html", {
        "exports": exports,
        "destinations": destinations,
        "q": q,
        "destination_filter": destination,
        "date_from": date_from,
        "date_to": date_to,
        "count_filter": count_filter,
    })


@group_required("Cửa hàng trưởng", "Nhân viên")
@login_required(login_url="login")
@transaction.atomic
def create_export(request):

    # ================== FEFO STOCK QUERYSET ==================
    stock_queryset = StockItem.objects.filter(quantity__gt=0).order_by("expiry_date")

    if request.method == "POST":
        form = ExportReceiptForm(request.POST)
        formset = ExportItemFormSet(request.POST, prefix="items")

        # Validate form + formset
        if form.is_valid() and formset.is_valid():

            # ===== VALIDATE TRƯỚC KHI LƯU =====
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue

                stock_item = f.cleaned_data.get("stock_item")
                qty = f.cleaned_data.get("quantity") or 0

                # Dòng trống → bỏ qua
                if not stock_item or qty <= 0:
                    continue

                # Số lượng vượt tồn kho
                if qty > stock_item.quantity:
                    messages.error(
                        request,
                        f"Số lượng xuất ({qty}) lớn hơn tồn kho của lô {stock_item} ({stock_item.quantity})."
                    )
                    return render(request, "export_create.html", {
                        "form": form,
                        "formset": formset,
                        "stock_queryset": stock_queryset,
                    })

            # ===== LƯU PHIẾU XUẤT =====
            export = form.save(commit=False)
            export.created_by = request.user
            export.save()

            saved_count = 0

            # ===== LƯU TỪNG ITEM =====
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue

                stock_item = f.cleaned_data.get("stock_item")
                qty = f.cleaned_data.get("quantity") or 0

                # Bỏ dòng trống
                if not stock_item or qty <= 0:
                    continue

                item = f.save(commit=False)
                item.receipt = export
                item.save()     # <-- ExportItem.save() sẽ tự trừ tồn

                saved_count += 1

            # Nếu không có dòng nào hợp lệ → xoá phiếu export vừa tạo
            if saved_count == 0:
                export.delete()
                messages.error(request, "Không có dòng hàng hợp lệ. Hãy chọn ít nhất 1 lô.")
                return render(request, "export_create.html", {
                    "form": form,
                    "formset": formset,
                    "stock_queryset": stock_queryset,
                })

            messages.success(request, f"Tạo phiếu xuất {export.export_code} thành công!")
            return redirect("export_list")

        # Form không hợp lệ
        messages.error(request, "Dữ liệu nhập chưa đúng. Vui lòng kiểm tra.")
        return render(request, "export_create.html", {
            "form": form,
            "formset": formset,
            "stock_queryset": stock_queryset,
        })

    # ================== GET REQUEST ==================
    # → tạo form mới + code mới
    new_code = ExportReceipt.generate_new_code()
    form = ExportReceiptForm(initial={"export_code": new_code})
    formset = ExportItemFormSet(prefix="items")

    return render(request, "export_create.html", {
        "form": form,
        "formset": formset,
        "stock_queryset": stock_queryset,
    })



# views.py
import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404


@group_required('Cửa hàng trưởng', 'Nhân viên')
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
# ===================== HOÀN HÀNG =====================
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def return_list(request):
    q = request.GET.get("q", "").strip()

    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    count_filter = request.GET.get("count", "")

    returns = ReturnReceipt.objects.prefetch_related(
        "items__product",
        "created_by"
    )

    # --- Search ---
    if q:
        returns = returns.filter(
            Q(return_code__icontains=q) |
            Q(note__icontains=q) |
            Q(items__reason__icontains=q) |
            Q(items__product__name__icontains=q) |
            Q(created_by__username__icontains=q)
        ).distinct()

    # --- Lọc theo ngày ---
    if date_from:
        returns = returns.filter(return_date__gte=date_from)
    if date_to:
        returns = returns.filter(return_date__lte=date_to)

    returns = returns.order_by("-return_date")

    return render(request, "return_list.html", {
        "returns": returns,
        "q": q,

        "date_from": date_from,
        "date_to": date_to,
        "count_filter": count_filter,
    })


# ------------------------ TẠO PHIẾU HOÀN ------------------------
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
@transaction.atomic
def create_return(request):
    export_receipt = None

    if request.method == "POST":
        export_receipt_id = request.POST.get("export_receipt")
        if export_receipt_id:
            export_receipt = ExportReceipt.objects.filter(pk=export_receipt_id).first()

        form = ReturnReceiptForm(request.POST)
        formset = ReturnItemFormSet(
            request.POST,
            prefix="items",
            queryset=ReturnItem.objects.none(),
            form_kwargs={"export_receipt": export_receipt}
        )

        if form.is_valid() and formset.is_valid():
            try:
                receipt = form.save(commit=False)
                receipt.created_by = request.user

                if not receipt.return_code:
                    receipt.return_code = ReturnReceipt.generate_new_code()

                receipt.save()

                saved = 0

                for f in formset:
                    if not f.cleaned_data or f.cleaned_data.get("DELETE", False):
                        continue

                    item = f.save(commit=False)

                    if not item.export_item_id:
                        continue

                    if item.export_item:
                        try:
                            export_item = item.export_item
                            if not export_item.stock_item:
                                continue

                            item.product = export_item.stock_item.product
                            item.unit_price = export_item.unit_price or Decimal('0')
                            item.unit = export_item.unit or ""
                            item.expiry_date = export_item.stock_item.expiry_date
                            item.location = export_item.stock_item.location or ""

                            if not item.quantity or item.quantity <= 0:
                                continue

                            if not item.reason:
                                item.reason = "Hoàn hàng"
                        except Exception:
                            import traceback
                            print("Error processing export_item:")
                            print(traceback.format_exc())
                            continue

                    item.receipt = receipt
                    item.save()
                    saved += 1

                if saved == 0:
                    receipt.delete()
                    messages.warning(request, "Chưa có sản phẩm hợp lệ.")
                    return redirect("return_list")

                messages.success(request, f"Đã tạo phiếu hoàn {receipt.return_code}.")
                return redirect("return_list")

            except Exception as e:
                import traceback
                messages.error(request, f"Lỗi khi lưu: {str(e)}")
                print(f"Error in create_return: {str(e)}")
                print(traceback.format_exc())
        else:
            # lỗi form / formset
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if formset.errors:
                for error_dict in formset.errors:
                    for field, errors in error_dict.items():
                        for error in errors:
                            messages.error(request, f" {field}: {error}")
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    messages.error(request, f"{error}")

        return render(request, "return_create.html", {"form": form, "formset": formset})

    # GET
    form = ReturnReceiptForm(initial={"return_code": ReturnReceipt.generate_new_code()})
    formset = ReturnItemFormSet(
        prefix="items",
        queryset=ReturnItem.objects.none(),
        form_kwargs={"export_receipt": None}
    )
    return render(request, "return_create.html", {"form": form, "formset": formset})



from .models import ReturnReceipt


@group_required('Cửa hàng trưởng', 'Nhân viên')
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

from django.db.models import Q, Count


@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def po_list(request):
    q = request.GET.get("q", "").strip()
    supplier_id = request.GET.get("supplier", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    count_filter = request.GET.get("count", "")
    status = request.GET.get("status", "")

    pos = PurchaseOrder.objects.select_related(
        "supplier", "created_by"
    ).prefetch_related(
        "items__product"
    )
    user = request.user
    perms = get_permission_flags(user)

    if perms["is_supplier"]:
        pos = pos.filter(supplier__supplier_code=user.username)

    # --- SEARCH ---
    if q:
        pos = pos.filter(
            Q(po_code__icontains=q) |
            Q(note__icontains=q) |
            Q(supplier__company_name__icontains=q) |
            Q(created_by__username__icontains=q) |
            Q(items__product__name__icontains=q)
        ).distinct()

    # --- FILTER BY SUPPLIER ---
    if supplier_id:
        pos = pos.filter(supplier_id=supplier_id)

    # --- FILTER BY STATUS ---
    if status:
        pos = pos.filter(status=status)

    # --- FILTER DATE RANGE ---
    if date_from:
        pos = pos.filter(created_date__gte=date_from)
    if date_to:
        pos = pos.filter(created_date__lte=date_to)

    # --- FILTER BY NUMBER OF PRODUCTS ---
    if count_filter == "0":
        pos = pos.annotate(total_items=Count("items")).filter(total_items=0)
    elif count_filter == "1":
        pos = pos.annotate(total_items=Count("items")).filter(total_items__gt=0)

    pos = pos.order_by("-created_date")

    suppliers = Supplier.objects.all()

    # 🔥 QUAN TRỌNG: LẤY QUYỀN NGƯỜI DÙNG
    perms = get_permission_flags(request.user)

    return render(request, "po_list.html", {
        "pos": pos,
        "suppliers": suppliers,
        "q": q,
        "supplier_id": supplier_id,
        "date_from": date_from,
        "date_to": date_to,
        "count_filter": count_filter,
        "status": status,
        **perms,    # 🔥 BẮT BUỘC PHẢI CÓ
    })


from .models import Supplier, PurchaseOrder, PurchaseOrderItem  # chắc bạn đã import ở trên rồi


@group_required('Cửa hàng trưởng','Nhân viên')
@login_required(login_url='login')

def create_po(request):

    if request.method == "GET":
        # Tạo mã mới để hiển thị trên form
        new_code = PurchaseOrder.generate_new_code()
        form = PurchaseOrderForm(initial={"po_code": new_code})
        formset = PurchaseOrderItemFormSet(form_kwargs={"supplier": None})
        return render(request, "po_create.html", {"form": form, "formset": formset})

    # POST request
    form = PurchaseOrderForm(request.POST)
    supplier = None
    supplier_id = request.POST.get("supplier")
    if supplier_id:
        supplier = Supplier.objects.filter(pk=supplier_id).first()

    formset = PurchaseOrderItemFormSet(
        request.POST,
        form_kwargs={"supplier": supplier}
    )

    if form.is_valid() and formset.is_valid():
        po = form.save(commit=False)
        po.created_by = request.user

        # Nếu người dùng xóa po_code → vẫn tự sinh
        if not po.po_code:
            po.po_code = PurchaseOrder.generate_new_code()

        po.save()
        formset.instance = po
        formset.save()

        messages.success(request, f"Đã tạo đơn đặt hàng {po.po_code} thành công!")
        return redirect("po_list")

    messages.error(request, " Dữ liệu chưa hợp lệ.")
    return render(request, "po_create.html", {"form": form, "formset": formset})



@group_required('Cửa hàng trưởng')
@login_required(login_url='login')
@transaction.atomic
def po_edit(request, code):
    user = request.user
    perms = get_permission_flags(user)

    if perms["is_supplier"]:
        po_obj = get_object_or_404(PurchaseOrder, pk=code)
        if po_obj.supplier.supplier_code != user.username:
            return redirect("po_list")  # silent redirect

    po = get_object_or_404(PurchaseOrder, pk=code)
    form = PurchaseOrderForm(request.POST or None, instance=po)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f" Đã cập nhật đơn đặt hàng {po.po_code}.")
            return redirect("po_list")
        messages.error(request, " Cập nhật thất bại, vui lòng kiểm tra lại.")
    return render(request, "po_edit.html", {"form": form, "po": po})



@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def po_export_pdf(request, code):
    user = request.user
    perms = get_permission_flags(user)

    # lấy PO trước
    po = get_object_or_404(PurchaseOrder, po_code=code)

    if perms["is_supplier"] and po.supplier.supplier_code != user.username:
        return redirect("po_list")

    html = render_to_string("po_pdf.html", {"po": po})

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(
        html,
        False,
        configuration=config,
        options={"encoding": "utf-8"}
    )

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="PO_{po.po_code}.pdf"'
    return response



# ===================== ASN =====================
from datetime import date, timedelta
from django.db.models import Sum, F
from .models import ASN, ASNItem
from .forms import ASNForm, ASNItemFormSet

from django.db.models import Q, Count
from datetime import date, timedelta


@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def asn_list(request):
    user = request.user
    perms = get_permission_flags(user)

    # supplier_id an toàn (không lỗi user.supplier)
    supplier_id_user = getattr(user, "supplier_id", None)
    supplier_code_user = getattr(user, "username", None)

    # load base queryset
    asns = ASN.objects.all().select_related("supplier", "po")

    # NCC chỉ xem phiếu của chính họ
    if perms["is_supplier"]:
        asns = asns.filter(supplier__supplier_code=supplier_code_user)

    # ----- FILTER FORM -----
    q = request.GET.get("q", "").strip()
    supplier_id = request.GET.get("supplier", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    status = request.GET.get("status", "")
    count_filter = request.GET.get("count", "")

    # SEARCH
    if q:
        asns = asns.filter(
            Q(asn_code__icontains=q) |
            Q(po__po_code__icontains=q) |
            Q(supplier__company_name__icontains=q) |
            Q(items__product__name__icontains=q) |
            Q(deliverer_name__icontains=q)
        ).distinct()

    # FILTER SUPPLIER (chỉ cho nhân viên / cửa hàng trưởng)
    if not perms["is_supplier"] and supplier_id:
        asns = asns.filter(supplier_id=supplier_id)

    # DATE RANGE
    if date_from:
        asns = asns.filter(expected_date__gte=date_from)
    if date_to:
        asns = asns.filter(expected_date__lte=date_to)

    # STATUS
    if status:
        asns = asns.filter(status=status)

    # COUNT SP
    if count_filter == "0":
        asns = asns.annotate(total_items=Count("items")).filter(total_items=0)
    elif count_filter == "1":
        asns = asns.annotate(total_items=Count("items")).filter(total_items__gt=0)

    asns = asns.order_by("-expected_date")

    suppliers = Supplier.objects.all()

    return render(request, "asn_list.html", {
        "asns": asns,
        "suppliers": suppliers,
        "q": q,
        "supplier_id": supplier_id,
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "count_filter": count_filter,
        "can_edit_asn": perms["is_supplier"],
        "can_create_asn": perms["is_supplier"],
        **perms
    })



@group_required("Nhà cung ứng")
@login_required(login_url="login")
@transaction.atomic
def create_asn(request):
    user = request.user
    supplier = Supplier.objects.filter(supplier_code=user.username).first()

    if not supplier:
        messages.error(request, "Tài khoản chưa được gán Nhà cung ứng.")
        return redirect("asn_list")

    # PO của NCC này
    allowed_po = PurchaseOrder.objects.filter(supplier=supplier)

    po = None

    if request.method == "POST":
        po_id = request.POST.get("po")

        # chặn chọn PO không thuộc về NCC này
        if po_id:
            po = PurchaseOrder.objects.filter(pk=po_id, supplier=supplier).first()
            if not po:
                messages.error(request, "Bạn không có quyền tạo ASN từ PO này.")
                return redirect("asn_list")

        mutable_post = request.POST.copy()
        mutable_post["supplier"] = str(supplier.pk)

        form = ASNForm(mutable_post)
        if form.is_valid():
            asn = form.save(commit=False)
            if not asn.asn_code:
                asn.asn_code = ASN.generate_new_code()

            asn.supplier = supplier
            asn.created_by = user
            asn.save()

            formset = ASNItemFormSet(
                mutable_post,
                instance=asn,
                form_kwargs={"po": po}
            )

            if formset.is_valid():
                items = formset.save(commit=False)

                for item in items:
                    if not item.product_id:
                        continue
                    if not item.quantity or item.quantity <= 0:
                        messages.error(request, "Số lượng phải > 0")
                        return render(request, "asn_create.html", {
                            "form": form,
                            "formset": formset,
                            "allowed_po": allowed_po
                        })
                    item.asn = asn
                    item.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                messages.success(request, f"Tạo ASN {asn.asn_code} thành công.")
                return redirect("asn_list")

            else:
                messages.error(request, " Lỗi sản phẩm.")
        else:
            messages.error(request, " Lỗi thông tin phiếu.")

        formset = ASNItemFormSet(
            mutable_post,
            instance=ASN(),
            form_kwargs={"po": po}
        )

    else:
        form = ASNForm(initial={"asn_code": ASN.generate_new_code()})
        formset = ASNItemFormSet(
            instance=ASN(),
            form_kwargs={"po": None}
        )

    return render(request, "asn_create.html", {
        "form": form,
        "formset": formset,
        "allowed_po": allowed_po
    })


# ================= ASN EXPORT PDF =================
@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def asn_export_pdf(request, code):
    user = request.user
    perms = get_permission_flags(user)

    asn = get_object_or_404(ASN, asn_code=code)

    # Nhà cung ứng chỉ xem được phiếu của chính mình
    if perms["is_supplier"] and asn.supplier.supplier_code != user.username:
        return redirect("asn_list")

    html = render_to_string("asn_pdf.html", {"asn": asn})

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type="application/pdf")
    # ✅ SỬA LẠI DÒNG NÀY: nháy đơn/bép phải khớp
    response['Content-Disposition'] = f'inline; filename="ASN_{asn.asn_code}.pdf"'
    return response


# ================= EDIT ASN STATUS (NHÀ CUNG ỨNG) =================
from .forms import ASNStatusForm
from .decorators import group_required
@group_required("Nhà cung ứng")
@login_required(login_url="login")
def edit_asn(request, code):
    user = request.user
    perms = get_permission_flags(user)

    # Lấy ASN
    asn = get_object_or_404(ASN, asn_code=code)

    # Chỉ người tạo mới được sửa
    if asn.supplier.supplier_code != user.username:
        messages.error(request, "Bạn không có quyền chỉnh sửa phiếu này.")
        return redirect("asn_list")

    # ----- POST -----
    if request.method == "POST":
        form = ASNStatusForm(request.POST, instance=asn)

        if form.is_valid():
            form.save()
            messages.success(request, f"Đã cập nhật trạng thái ASN {asn.asn_code} thành công!")
            return redirect("asn_list")
        else:
            messages.error(request, " Dữ liệu không hợp lệ.")

    # ----- GET -----
    else:
        form = ASNStatusForm(instance=asn)

    return render(request, "asn_edit.html", {
        "asn": asn,
        "form": form,
        "is_supplier": True,
    })








# ===================== BÁO CÁO =====================



from datetime import date, timedelta
from django.db.models import Sum
import json
@group_required('Cửa hàng trưởng', 'Nhân viên')
@login_required(login_url='login')
def reports(request):
    today = date.today()

    # --- Hàm phụ parse string -> date ---
    def parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    # ---- Lấy input từ request ----
    quick_range = request.GET.get("quick_range", "")
    start_date = parse_date(request.GET.get("start_date"))
    end_date = parse_date(request.GET.get("end_date"))

    # ---- Áp dụng bộ lọc thời gian nhanh (nếu có) ----
    if quick_range:
        if quick_range == "today":
            start_date = end_date = today

        elif quick_range == "this_week":
            start_date = today - timedelta(days=today.weekday())
            end_date = today

        elif quick_range == "this_month":
            start_date = today.replace(day=1)
            end_date = today

        elif quick_range == "last_month":
            first = today.replace(day=1)
            last_month_end = first - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end

        elif quick_range == "this_quarter":
            quarter = (today.month - 1) // 3 + 1
            start_month = 3 * (quarter - 1) + 1
            start_date = date(today.year, start_month, 1)
            end_date = today

        elif quick_range == "this_year":
            start_date = date(today.year, 1, 1)
            end_date = today

    # Nếu chưa có ngày → set mặc định đầu tháng đến hôm nay
    if start_date is None:
        start_date = today.replace(day=1)
    if end_date is None:
        end_date = today

    # ---- 3. Tổng số phiếu nhập / xuất / hoàn trong khoảng ngày ----
    imports_qs = ImportReceipt.objects.filter(
        import_date__range=[start_date, end_date]
    )
    exports_qs = ExportReceipt.objects.filter(
        export_date__range=[start_date, end_date]
    )
    returns_qs = ReturnReceipt.objects.filter(
        return_date__range=[start_date, end_date]
    )

    total_imports = imports_qs.count()
    total_exports = exports_qs.count()
    total_returns = returns_qs.count()

    # Tổng tồn kho & tình trạng hạn dùng (không phụ thuộc ngày)
    total_stock = StockItem.objects.aggregate(total=Sum("quantity"))["total"] or 0
    expired = StockItem.objects.filter(status="expired").count()
    nearly = StockItem.objects.filter(status="nearly_expired").count()

    # ---- 2. Doanh thu = tổng tiền phiếu xuất - tổng tiền phiếu hoàn ----
    total_export_value = ExportItem.objects.filter(
        receipt__export_date__range=[start_date, end_date]
    ).aggregate(total=Sum("total"))["total"] or 0

    total_return_value = ReturnItem.objects.filter(
        receipt__return_date__range=[start_date, end_date]
    ).aggregate(total=Sum("total"))["total"] or 0

    total_revenue = total_export_value - total_return_value

    # ---- 4. Top 3 sản phẩm bán chạy (theo số lượng xuất) ----
    top_products_qs = (
        ExportItem.objects.filter(
            receipt__export_date__range=[start_date, end_date]
        )
        .values(
            "stock_item__product__product_code",
            "stock_item__product__name"
        )
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:3]
    )

    top_products = [
        {
            "code": p["stock_item__product__product_code"],
            "name": p["stock_item__product__name"],
            "total_qty": p["total_qty"],
        }
        for p in top_products_qs
    ]

    # ---- 5. Biểu đồ: Doanh thu theo ngày = xuất - hoàn ----
    exports_by_date = (
        ExportItem.objects.filter(
            receipt__export_date__range=[start_date, end_date]
        )
        .values("receipt__export_date")
        .annotate(total=Sum("total"))
    )

    returns_by_date = (
        ReturnItem.objects.filter(
            receipt__return_date__range=[start_date, end_date]
        )
        .values("receipt__return_date")
        .annotate(total=Sum("total"))
    )

    export_dict = {r["receipt__export_date"]: r["total"] for r in exports_by_date}
    return_dict = {r["receipt__return_date"]: r["total"] for r in returns_by_date}

    # Lấy tất cả các ngày có dữ liệu (xuất hoặc hoàn)
    all_dates = sorted(set(list(export_dict.keys()) + list(return_dict.keys())))

    chart_labels = []
    chart_data = []

    for d in all_dates:
        export_total = export_dict.get(d, 0) or 0
        return_total = return_dict.get(d, 0) or 0
        net = export_total - return_total
        chart_labels.append(d.strftime("%d/%m"))
        chart_data.append(float(net))

    context = {
        # đưa về template dạng string yyyy-mm-dd để gán vào input date
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "quick_range": quick_range,

        "total_imports": total_imports,
        "total_exports": total_exports,
        "total_returns": total_returns,
        "total_stock": total_stock,
        "expired": expired,
        "nearly": nearly,
        "total_revenue": total_revenue,
        "top_products": top_products,

        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_data_json": json.dumps(chart_data),
    }
    return render(request, "reports.html", context)


# ===================== API ENDPOINTS =====================
@login_required
def api_supplier_products(request, supplier_id):
    """✅ API: Lấy danh sách sản phẩm của nhà cung cấp (cho PO)"""
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        products = {}

        for sp in SupplierProduct.objects.filter(
            supplier=supplier,
            is_active=True
        ).order_by("product_code"):
            products[str(sp.pk)] = {
                'code': sp.product_code,
                'name': sp.name,
                'unit_price': float(sp.unit_price),
            }

        return JsonResponse({'products': products})
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Nhà cung cấp không tồn tại'}, status=404)



@login_required
def api_po_details(request, po_id):
    """✅ API: Lấy thông tin PO và sản phẩm (cho ASN)"""
    from django.db.models import Sum
    from .models import PurchaseOrderItem, ASNItem

    try:
        po = PurchaseOrder.objects.get(pk=po_id)
        products = {}

        # Lấy tất cả sản phẩm trong PO
        for po_item in PurchaseOrderItem.objects.filter(po=po).select_related('product'):
            # Tính số lượng đã giao
            delivered_qty = ASNItem.objects.filter(
                asn__po=po,
                product=po_item.product
            ).aggregate(total=Sum('quantity'))['total'] or 0

            # Số lượng còn lại = số lượng đặt - số lượng đã giao
            max_quantity = po_item.quantity - delivered_qty

            products[str(po_item.product.pk)] = {
                'code': po_item.product.product_code,
                'name': po_item.product.name,
                'unit_price': float(po_item.unit_price),
                'max_quantity': max_quantity,  # Số lượng còn lại trong PO
                'ordered_quantity': po_item.quantity,  # Tổng số lượng đặt
            }

        return JsonResponse({
            'supplier_id': po.supplier.pk,
            'products': products
        })
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': 'PO không tồn tại'}, status=404)


@login_required
def api_export_items(request, export_code):
    """✅ API: Lấy danh sách sản phẩm của phiếu xuất (cho phiếu hoàn)"""
    from django.db.models import Sum
    from .models import ExportItem, ReturnItem

    try:
        export_receipt = ExportReceipt.objects.get(pk=export_code)
        items = {}

        for export_item in ExportItem.objects.filter(receipt=export_receipt).select_related('stock_item__product'):
            # Tính số lượng đã hoàn
            returned_qty = ReturnItem.objects.filter(
                export_item=export_item
            ).aggregate(total=Sum('quantity'))['total'] or 0

            # Số lượng còn lại = số lượng xuất - số lượng đã hoàn
            max_quantity = export_item.quantity - returned_qty

            items[str(export_item.pk)] = {
                'product_code': export_item.stock_item.product.product_code,
                'product_name': export_item.stock_item.product.name,
                'product_id': export_item.stock_item.product.pk,
                'unit_price': float(export_item.unit_price),
                'unit': export_item.unit,
                'expiry_date': export_item.stock_item.expiry_date.strftime(
                    '%Y-%m-%d') if export_item.stock_item.expiry_date else None,
                'location': export_item.stock_item.location or '',
                'max_quantity': max_quantity,  # Số lượng còn lại có thể hoàn
                'exported_quantity': export_item.quantity,  # Tổng số lượng đã xuất
            }

        return JsonResponse({'items': items})
    except ExportReceipt.DoesNotExist:
        return JsonResponse({'error': 'Phiếu xuất không tồn tại'}, status=404)


from django.http import JsonResponse
from .models import ASN, ASNItem


def api_asn_items(request, asn_code):
    """
    API trả về toàn bộ thông tin cần thiết của ASN:
    - supplier_id, supplier_name
    - danh sách sản phẩm của ASN
    """
    try:
        asn = ASN.objects.select_related("supplier").get(asn_code=asn_code)
    except ASN.DoesNotExist:
        return JsonResponse({"error": "Không tìm thấy phiếu ASN."}, status=404)

    # Lấy danh sách sản phẩm ASN
    items = ASNItem.objects.filter(asn=asn).select_related("product")

    data = {
        "supplier_id": asn.supplier.supplier_code,
        "supplier_name": asn.supplier.company_name,
        "items": {}
    }

    for item in items:
        data["items"][item.pk] = {
            "asn_item_id": item.pk,
            "product_id": item.product_id,
            "product_code": item.product.product_code,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price or 0),
            "unit": item.unit,
            "expiry_date": item.expiry_date.strftime("%Y-%m-%d") if item.expiry_date else "",
        }

    return JsonResponse(data, safe=False)

# ===================== NHÀ CUNG ỨNG =====================
from django.db.models import Q, Count, Sum, F, DecimalField
from django.db.models.functions import Coalesce
from .models import Supplier, SupplierProduct, ImportItem   # thêm ImportItem nếu chưa import

@group_required('Cửa hàng trưởng', 'Nhân viên', 'Nhà cung ứng')
@login_required(login_url='login')
def supplier_history(request, pk):
    user = request.user
    perms = get_permission_flags(user)

    # NCC chỉ xem được lịch sử của chính họ
    if perms["is_supplier"] and pk != user.username:
        return redirect("suppliers")  # silent redirect

    # pk chính là supplier_code
    supplier = get_object_or_404(Supplier, pk=pk)

    # Tất cả các dòng nhập kho liên quan đến NCC này
    items_qs = ImportItem.objects.filter(
        import_receipt__supplier=supplier
    ).select_related("product", "import_receipt")

    # Tổng quan
    aggregates = items_qs.aggregate(
        total_products=Count("product", distinct=True),
        total_quantity=Coalesce(Sum("quantity"), 0),
        total_value=Coalesce(
            Sum(F("quantity") * F("unit_price")),
            0,
            output_field=DecimalField(max_digits=20, decimal_places=2)
        ),
    )

    # Gom theo từng sản phẩm
    product_stats = (
        items_qs
        .values(
            "product_id",
            "product__product_code",
            "product__name",
            "product__category__name",
        )
        .annotate(
            total_quantity=Sum("quantity"),
            total_value=Sum(F("quantity") * F("unit_price")),
        )
        .order_by("product__name")
    )

    # Chi tiết từng phiếu nhập (nếu cần xem timeline)
    items = items_qs.order_by(
        "-import_receipt__import_date",
        "-import_receipt__id"
    )

    context = {
        "supplier": supplier,
        "aggregates": aggregates,
        "product_stats": product_stats,
        "items": items,
    }
    return render(request, "supplier_history.html", context)


# ============= OTP RESET PASSWORD =============

import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from django.core.mail import send_mail
from smtplib import SMTPException

from .models import PasswordResetOTP, Supplier


def forgot_password(request):
    if request.method == "POST":
        raw_email = request.POST.get("email", "")
        email = raw_email.strip().lower()

        if not email:
            messages.error(request, "Vui lòng nhập email.")
            return render(request, "forgot_password.html")

        # 1) Tìm trong User trước (không phân biệt hoa/thường)
        user = User.objects.filter(email__iexact=email).first()

        # 2) Nếu không có, thử tìm trong Supplier (email nhà cung cấp)
        if not user:
            supplier = Supplier.objects.filter(email__iexact=email).first()
            if supplier:
                # Giả sử username của User NCC = supplier.supplier_code
                user = User.objects.filter(username=supplier.supplier_code).first()

        # 3) Nếu vẫn không có → báo lỗi
        if not user:
            messages.error(
                request,
                "Email này không gắn với tài khoản đăng nhập nào trong hệ thống!"
            )
            return render(request, "forgot_password.html", {"input_email": raw_email})

        # 4) Giới hạn 3 OTP / giờ / user
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = PasswordResetOTP.objects.filter(
            user=user, created_at__gte=one_hour_ago
        ).count()
        if recent_count >= 3:
            messages.error(
                request,
                "Bạn đã yêu cầu OTP quá nhiều lần. Vui lòng thử lại sau 1 giờ."
            )
            return render(request, "forgot_password.html", {"input_email": raw_email})

        # 5) Tạo OTP 6 số
        otp = f"{random.randint(100000, 999999)}"
        PasswordResetOTP.objects.create(user=user, otp=otp)

        # 6) Soạn email HTML, xưng tên người nhận
        full_name = user.get_full_name() or user.username
        greeting = f"Chào anh/chị {full_name},"

        html_message = f"""
        <div style='font-family:Arial; padding:20px; background:#f3f4f6'>
          <div style='max-width:600px; margin:auto; background:#fff; padding:20px;
                      border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.08);'>
            <h2 style='color:#0d6efd;'>Mã OTP khôi phục mật khẩu</h2>
            <p>{greeting}</p>
            <p>Đây là mã OTP dùng để đặt lại mật khẩu trong hệ thống <b>TH True Mart</b>:</p>
            <p style='font-size:30px; font-weight:bold; color:#0d6efd; text-align:center;'>
              {otp}
            </p>
            <p>Mã có hiệu lực trong <b>5 phút</b>. Vui lòng không chia sẻ cho bất kỳ ai.</p>
            <hr/>
            <p style='font-size:12px; color:#777;'>Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.</p>
          </div>
        </div>
        """

        try:
            send_mail(
                subject="Mã OTP khôi phục mật khẩu - TH True Mart",
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        except SMTPException as e:
            print("EMAIL ERROR:", e)
            messages.error(request, "Không gửi được email. Vui lòng thử lại sau.")
            return render(request, "forgot_password.html", {"input_email": raw_email})

        # 7) Lưu user vào session để bước sau xác minh OTP
        request.session["reset_user_id"] = user.id

        return redirect("verify_otp")

    return render(request, "forgot_password.html")


def verify_otp(request):
    user_id = request.session.get("reset_user_id")
    if not user_id:
        return redirect("forgot_password")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()

        if not otp_input:
            messages.error(request, "Vui lòng nhập mã OTP.")
            return render(request, "verify_otp.html")

        record = PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()
        if not record:
            messages.error(request, "Không tìm thấy OTP. Vui lòng yêu cầu lại.")
            return redirect("forgot_password")

        if not record.is_valid():
            messages.error(request, "OTP đã hết hạn. Vui lòng yêu cầu mã mới.")
            return redirect("forgot_password")

        if record.otp != otp_input:
            messages.error(request, "OTP không đúng. Vui lòng kiểm tra lại.")
            return render(request, "verify_otp.html")

        # OTP đúng → cho sang đặt mật khẩu mới
        return redirect("reset_password")

    return render(request, "verify_otp.html")



def reset_password(request):
    user_id = request.session.get("reset_user_id")
    if not user_id:
        return redirect("forgot_password")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        new = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if not new or not confirm:
            messages.error(request, "Vui lòng nhập đầy đủ mật khẩu.")
            return render(request, "reset_password.html")

        if new != confirm:
            messages.error(request, "Mật khẩu không trùng khớp.")
            return render(request, "reset_password.html")

        user.set_password(new)
        user.save()
        request.session.flush()
        messages.success(request, "Đặt lại mật khẩu thành công! Vui lòng đăng nhập lại.")

        return redirect("login")

    return render(request, "reset_password.html")


