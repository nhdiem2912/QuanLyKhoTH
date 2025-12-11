from django import forms
from django.forms import inlineformset_factory
from django.db.models import Sum

from .models import (
    Category, Supplier, SupplierProduct,
    StockItem,
    ImportReceipt, ImportItem,
    ExportReceipt, ExportItem,
    ReturnReceipt, ReturnItem,
    PurchaseOrder, PurchaseOrderItem,
    ASN, ASNItem
)

# ===================== CATEGORY =====================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["category_code", "name", "description", "image"]
        labels = {
            "category_code": "Mã danh mục",
            "name": "Tên danh mục",
            "description": "Mô tả",
            "image": "Ảnh danh mục",
        }
        widgets = {
            "category_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Nếu đang chỉnh sửa → khóa mã + tên
        if self.instance and self.instance.pk:
            self.fields["category_code"].disabled = True
            self.fields["name"].disabled = True

# ===================== SUPPLIER =====================
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["supplier_code", "company_name", "tax_code",
                  "contact_name", "phone", "email", "address", "status"]
        labels = {
            "supplier_code": "Mã nhà cung ứng",
            "company_name": "Tên công ty",
            "tax_code": "Mã số thuế",
            "contact_name": "Người liên hệ",
            "phone": "Số điện thoại",
            "email": "Email",
            "address": "Địa chỉ",
            "status": "Trạng thái",
        }
        widgets = {
            "supplier_code": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_code": forms.TextInput(attrs={"class": "form-control"}),
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["supplier_code"].disabled = True
            self.fields["company_name"].disabled = True
            self.fields["tax_code"].disabled = True

# ===================== SUPPLIER PRODUCT =====================
class SupplierProductForm(forms.ModelForm):
    class Meta:
        model = SupplierProduct
        fields = ["product_code", "name", "category", "unit_price", "is_active"]
        labels = {
            "product_code": "Mã sản phẩm NCC",
            "name": "Tên sản phẩm NCC",
            "category": "Danh mục",
            "unit_price": "Đơn giá NCC (₫)",
            "is_active": "Đang cung cấp",
        }
        widgets = {
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control text-end", "min": "0", "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cho phép để trống để coi như dòng trắng
        self.fields["product_code"].required = False
        self.fields["name"].required = False
        self.fields["category"].required = False
        self.fields["unit_price"].required = False

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("product_code")
        name = cleaned.get("name")
        price = cleaned.get("unit_price")

        if not code and not name and (price is None or price == 0):
            return cleaned

        if not code:
            self.add_error("product_code", "Vui lòng nhập mã sản phẩm NCC.")
        if not name:
            self.add_error("name", "Vui lòng nhập tên sản phẩm NCC.")
        if not price or price <= 0:
            self.add_error("unit_price", "Đơn giá phải lớn hơn 0.")

        return cleaned


SupplierProductFormSet = inlineformset_factory(
    Supplier,
    SupplierProduct,
    form=SupplierProductForm,
    extra=1,
    can_delete=True,
)


# ===================== STOCK ITEM =====================
class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = ["quantity", "unit", "location", "expiry_date"]
        labels = {
            "quantity": "Số lượng tồn",
            "unit": "Đơn vị",
            "location": "Vị trí trong kho",
            "expiry_date": "Hạn sử dụng",
        }
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


# ===================== PHIẾU NHẬP KHO =====================
class ImportReceiptForm(forms.ModelForm):
    class Meta:
        model = ImportReceipt
        fields = ["import_code", "supplier", "asn", "import_date", "note"]
        labels = {
            "import_code": "Mã phiếu nhập",
            "supplier": "Nhà cung ứng",
            "asn": "Phiếu ASN",
            "import_date": "Ngày nhập",
            "note": "Ghi chú",
        }
        widgets = {
            "import_code": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "asn": forms.Select(attrs={"class": "form-select asn-select"}),
            "import_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ImportItemForm(forms.ModelForm):
    class Meta:
        model = ImportItem
        fields = [
            "asn_item", "product", "quantity", "unit_price",
            "unit", "location", "expiry_date"
        ]
        labels = {
            "asn_item": "Dòng ASN",
            "product": "Sản phẩm",
            "quantity": "Số lượng",
            "unit_price": "Đơn giá",
            "unit": "Đơn vị",
            "location": "Vị trí",
            "expiry_date": "Hạn sử dụng",
        }
        widgets = {
            "asn_item": forms.HiddenInput(),
            "product": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control text-end quantity", "min": 1}
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control text-end unit-price",
                    "min": 0,
                    "step": "0.01",
                    "readonly": "readonly",
                }
            ),
            "unit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "VD: Thùng",
                    "readonly": "readonly",
                }
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "VD: Kệ A1"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "readonly": "readonly"}
            ),

        }

    def __init__(self, *args, **kwargs):
        # nhận thêm asn và supplier từ form_kwargs
        asn = kwargs.pop("asn", None)
        supplier = kwargs.pop("supplier", None)
        super().__init__(*args, **kwargs)

        qs = SupplierProduct.objects.all()

        # Nếu có ASN thì chỉ cho chọn các sản phẩm có trong ASN đó
        if asn is not None:
            qs = SupplierProduct.objects.filter(
                pk__in=asn.items.values_list("product_id", flat=True)
            )
        # Nếu không có ASN nhưng có NCC thì lọc theo NCC
        elif supplier is not None:
            qs = SupplierProduct.objects.filter(
                supplier=supplier,
                is_active=True
            )

        self.fields["product"].queryset = qs.order_by("name")
        self.fields["product"].empty_label = "---------"

    def clean(self):
        cleaned = super().clean()
        asn_item = cleaned.get("asn_item")
        product = cleaned.get("product")
        quantity = cleaned.get("quantity")

        # Dòng hoàn toàn trống thì bỏ qua
        if not asn_item and not product and not quantity:
            return cleaned

        # Nếu đã chọn ASNItem mà chưa chọn product thì tự set product = ASNItem.product
        if asn_item and not product:
            cleaned["product"] = asn_item.product

        # Nếu đã chọn ASNItem mà chưa nhập quantity thì lấy mặc định từ ASN
        if asn_item and (not quantity or quantity <= 0):
            cleaned["quantity"] = asn_item.quantity

            # Quantity phải > 0
        qty = cleaned.get("quantity")
        if qty is not None and qty <= 0:
            self.add_error("quantity", "Số lượng phải lớn hơn 0.")

        return cleaned


ImportItemFormSet = inlineformset_factory(
    ImportReceipt,
    ImportItem,
    form=ImportItemForm,
    extra=0,
    can_delete=True
)


# ===================== EXPORT RECEIPT =====================
class ExportReceiptForm(forms.ModelForm):
    class Meta:
        model = ExportReceipt
        fields = ["export_code", "export_date", "destination",
                  "receiver_name", "receiver_phone", "note"]
        widgets = {
            "export_code": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "export_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "destination": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "VD: Cửa hàng Nguyễn Văn Linh, chi nhánh Hà Nội,…"
            }),
            "receiver_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Người chịu trách nhiệm ký nhận hàng"
            }),
            "receiver_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "SĐT liên hệ khi giao hàng"
            }),
            "note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Ghi chú thêm (nếu có)…"
            }),
        }
        labels = {
            "export_code": "Mã phiếu xuất",
            "export_date": "Ngày xuất",
            "destination": "Nơi nhận",
            "receiver_name": "Người nhận",
            "receiver_phone": "SĐT người nhận",
            "note": "Ghi chú",
        }


class ExportItemForm(forms.ModelForm):
    class Meta:
        model = ExportItem
        fields = ["stock_item", "quantity", "unit_price",
                  "discount_percent", "unit", "total"]

        widgets = {
            "stock_item": forms.Select(attrs={
                "class": "form-select stock-select",
                "size": 6
            }),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control text-end quantity",
                "min": 1
            }),
            "unit_price": forms.NumberInput(attrs={
                "class": "form-control text-end unit-price",
                "step": "0.01",
                "readonly": True
            }),
            "discount_percent": forms.NumberInput(attrs={
                "class": "form-control text-end discount",
                "step": "0.01",
                "min": 0
            }),
            "unit": forms.TextInput(attrs={"class": "form-control unit-field"}),
            "total": forms.NumberInput(attrs={
                "class": "form-control text-end total-input",
                "readonly": True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from django.db import models as dj

        base_qs = StockItem.objects.all().order_by(
            dj.Case(
                dj.When(status="nearly_expired", then=0),
                dj.When(status="expired", then=1),
                dj.When(status="valid", then=2),
                default=3,
                output_field=dj.IntegerField()
            ),
            "expiry_date"
        )


        try:
            if self.instance and hasattr(self.instance, "stock_item") and self.instance.stock_item:
                p = self.instance.stock_item.product
                base_qs = base_qs.filter(product=p)
        except:
            pass

        self.fields["stock_item"].queryset = base_qs



ExportItemFormSet = inlineformset_factory(
    ExportReceipt,
    ExportItem,
    form=ExportItemForm,
    extra=1,
    can_delete=True
)


# ===================== RETURN RECEIPT =====================
class ReturnReceiptForm(forms.ModelForm):
    class Meta:
        model = ReturnReceipt
        fields = ["return_code", "return_date", "export_receipt", "note"]
        labels = {
            "return_code": "Mã phiếu hoàn",
            "return_date": "Ngày hoàn",
            "export_receipt": "Phiếu xuất liên quan",
            "note": "Ghi chú",
        }
        widgets = {
            "return_code": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "return_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "export_receipt": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ReturnItemForm(forms.ModelForm):
    export_item = forms.ModelChoiceField(
        queryset=ExportItem.objects.select_related("stock_item__product", "receipt"),
        label="Dòng phiếu xuất",
        widget=forms.Select(attrs={"class": "form-select export-item-select"}),
        required=False
    )

    class Meta:
        model = ReturnItem
        fields = ["export_item", "product", "quantity", "unit",
                  "unit_price", "expiry_date", "location", "reason", "detail_note"]
        labels = {
            "export_item": "Dòng phiếu xuất",
            "product": "Sản phẩm hoàn",
            "quantity": "Số lượng hoàn",
            "unit": "Đơn vị",
            "unit_price": "Đơn giá",
            "location": "Vị trí",
            "expiry_date": "Hạn sử dụng",
            "reason": "Lý do hoàn hàng",
            "detail_note": "Ghi chú chi tiết",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select product-select"}),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control quantity text-end",
                "min": 1
            }),
            "unit_price": forms.NumberInput(attrs={
                "class": "form-control unit-price text-end",
                "min": 0,
                "readonly": "readonly"
            }),
            "unit": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "location": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date", "readonly": "readonly"}),
            "reason": forms.TextInput(attrs={"class": "form-control"}),
            "detail_note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        export_receipt = kwargs.pop("export_receipt", None)
        super().__init__(*args, **kwargs)

        # cho phép dòng trống
        self.fields["product"].required = False
        self.fields["quantity"].required = False
        self.fields["unit"].required = False
        self.fields["unit_price"].required = False
        self.fields["location"].required = False
        self.fields["expiry_date"].required = False
        self.fields["reason"].required = False
        self.fields["detail_note"].required = False

        if export_receipt:
            self.fields["export_item"].queryset = ExportItem.objects.filter(
                receipt=export_receipt
            ).select_related("stock_item__product")

    def clean(self):
        cleaned = super().clean()
        export_item = cleaned.get("export_item")
        quantity = cleaned.get("quantity")
        product = cleaned.get("product")

        # hoàn toàn trống → bỏ qua
        if not export_item and not product and not quantity:
            return cleaned

        # có dữ liệu nhưng không chọn dòng xuất -> lỗi
        if not export_item:
            raise forms.ValidationError("Vui lòng chọn dòng phiếu xuất.")

        # validate SL hoàn không vượt SL còn lại
        if export_item and quantity:
            exported_qty = export_item.quantity
            returned_qty = ReturnItem.objects.filter(
                export_item=export_item
            ).exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).aggregate(total=Sum("quantity"))["total"] or 0

            max_qty = exported_qty - returned_qty
            if quantity > max_qty:
                raise forms.ValidationError(
                    f"Số lượng hoàn tối đa cho dòng này là {max_qty}."
                )
            qty = cleaned.get("quantity")
            if qty is not None and qty <= 0:
                raise forms.ValidationError("Số lượng phải lớn hơn 0.")

        return cleaned


ReturnItemFormSet = inlineformset_factory(
    ReturnReceipt, ReturnItem,
    form=ReturnItemForm,
    extra=1,
    can_delete=True
)


# ===================== PURCHASE ORDER (PO) =====================
class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["po_code", "supplier", "status", "note"]
        labels = {
            "po_code": "Mã PO",
            "supplier": "Nhà cung ứng",
            "status": "Trạng thái",
            "note": "Ghi chú",
        }
        widgets = {
            "po_code": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["supplier"].disabled = True
            self.fields["po_code"].disabled = True

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["product", "quantity", "unit", "unit_price"]
        labels = {
            "product": "Sản phẩm",
            "quantity": "Số lượng",
            "unit": "Đơn vị",
            "unit_price": "Đơn giá NCC (₫)",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select product-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control quantity", "min": "1"}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "VD: Thùng"}),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control text-end unit-price",
                    "readonly": "readonly"
                }),
        }

    def __init__(self, *args, **kwargs):
        supplier = kwargs.pop("supplier", None)
        super().__init__(*args, **kwargs)

        if supplier is not None:
            self.fields["product"].queryset = SupplierProduct.objects.filter(
                supplier=supplier,
                is_active=True
            ).order_by("product_code")

        else:
            self.fields["product"].queryset = SupplierProduct.objects.none()



PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True
)


# ===================== ASN (GIAO HÀNG) =====================
class ASNForm(forms.ModelForm):
    class Meta:
        model = ASN
        fields = ["asn_code", "po", "supplier",
                  "deliverer_name", "deliverer_phone", "expected_date", "status"]
        labels = {
            "asn_code": "Mã ASN",
            "po": "Đơn đặt hàng (PO)",
            "supplier": "Nhà cung ứng",
            "deliverer_name": "Người giao hàng",
            "deliverer_phone": "Số điện thoại",
            "expected_date": "Ngày dự kiến giao",
            "status": "Trạng thái giao",
        }
        widgets = {
            "asn_code": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "po": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "deliverer_name": forms.TextInput(attrs={"class": "form-control"}),
            "deliverer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "expected_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        po = cleaned.get("po")
        supplier = cleaned.get("supplier")

        if po and not supplier:
            cleaned["supplier"] = po.supplier
            supplier = po.supplier

        if po and supplier and po.supplier != supplier:
            raise forms.ValidationError("Nhà cung ứng của ASN phải trùng với nhà cung ứng của PO.")
        return cleaned


class ASNItemForm(forms.ModelForm):
    class Meta:
        model = ASNItem
        fields = ["product", "quantity", "unit", "unit_price", "expiry_date"]
        labels = {
            "product": "Sản phẩm",
            "quantity": "Số lượng",
            "unit": "Đơn vị",
            "unit_price": "Đơn giá",
            "expiry_date": "Hạn sử dụng",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select product-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control quantity", "min": 1}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control","step":1, "min": 0}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        po = kwargs.pop("po", None)
        super().__init__(*args, **kwargs)
        self._po = po
        if po is not None:
            self.fields["product"].queryset = SupplierProduct.objects.filter(
                purchaseorderitem__po=po
            ).distinct().order_by("product_code")
        else:
            self.fields["product"].queryset = SupplierProduct.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")

        if not product or not quantity:
            return cleaned_data

        # Lấy asn / po hiện tại
        asn = getattr(self.instance, "asn", None)
        po = None
        if asn and asn.po_id:
            po = asn.po
        elif hasattr(self, "_po") and self._po:
            po = self._po

        if po:
            from .models import PurchaseOrderItem, ASNItem

            po_item = PurchaseOrderItem.objects.filter(
                po=po,
                product=product
            ).first()

            if not po_item:
                raise forms.ValidationError(
                    f"Sản phẩm '{product.name}' không có trong PO đã chọn."
                )

            ordered_qty = po_item.quantity

            delivered_qty = ASNItem.objects.filter(
                asn__po=po,
                product=product
            ).exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).aggregate(total=Sum("quantity"))["total"] or 0

            max_qty = ordered_qty - delivered_qty

            if quantity > max_qty:
                raise forms.ValidationError(
                    f"Số lượng giao ({quantity}) vượt quá số lượng còn lại trong PO ({max_qty})."
                )

        return cleaned_data


ASNItemFormSet = inlineformset_factory(
    ASN, ASNItem,
    form=ASNItemForm,
    extra=1,
    can_delete=True
)
class ASNStatusForm(forms.ModelForm):
    class Meta:
        model = ASN
        fields = ["status"]
        labels = {"status": "Trạng thái giao hàng"}
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"})
        }
