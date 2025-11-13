from django import forms
from django.forms import inlineformset_factory
from .models import (
    Category, Supplier,
    ProductMaster, StockItem,
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
        fields = ["category_code", "name", "description"]
        labels = {
            "category_code": "Mã danh mục",
            "name": "Tên danh mục",
            "description": "Mô tả",
        }
        widgets = {
            "category_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


# ===================== SUPPLIER =====================
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["supplier_code", "company_name", "contact_name", "phone", "email", "status"]
        labels = {
            "supplier_code": "Mã nhà cung ứng",
            "company_name": "Tên công ty",
            "contact_name": "Người liên hệ",
            "phone": "Số điện thoại",
            "email": "Email",
            "status": "Trạng thái",
        }
        widgets = {
            "supplier_code": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


# ===================== PRODUCT MASTER =====================
class ProductMasterForm(forms.ModelForm):
    class Meta:
        model = ProductMaster
        fields = ["product_code", "name", "category", "status"]
        labels = {
            "product_code": "Mã sản phẩm",
            "name": "Tên sản phẩm",
            "category": "Danh mục",
            "status": "Trạng thái",
        }
        widgets = {
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


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


from django import forms
from django.forms import inlineformset_factory
from .models import ImportReceipt, ImportItem

# -------------------- PHIẾU NHẬP KHO --------------------
class ImportReceiptForm(forms.ModelForm):
    class Meta:
        model = ImportReceipt
        fields = ["import_code", "supplier", "import_date", "note"]
        widgets = {
            "import_code": forms.TextInput(attrs={"class": "form-control"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "import_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ImportItemForm(forms.ModelForm):
    class Meta:
        model = ImportItem
        fields = ["product", "quantity", "unit_price","discount_percent", "unit", "location", "expiry_date"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control text-end", "min": 1}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control text-end", "min": 0, "step": "0.01"}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "VD: Thùng"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "VD: Kệ A1"}),  # ✅ vị trí
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "discount_percent": forms.NumberInput(attrs={
                "class": "form-control text-end discount",
                "min": 0,
                "step": "0.01",
                "value": "0",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["discount_percent"].required = False

ImportItemFormSet = inlineformset_factory(
    ImportReceipt,
    ImportItem,
    form=ImportItemForm,
    extra=1,
    can_delete=True
)

# ===================== EXPORT RECEIPT =====================
from django import forms
from django.forms import inlineformset_factory
from .models import ExportReceipt, ExportItem, StockItem

class ExportReceiptForm(forms.ModelForm):
    class Meta:
        model = ExportReceipt
        fields = ["export_code", "export_date", "destination", "note"]
        labels = {
            "export_code": "Mã phiếu xuất",
            "export_date": "Ngày xuất",
            "destination": "Nơi nhận hàng",
            "note": "Ghi chú",
        }
        widgets = {
            "export_code": forms.TextInput(attrs={"class": "form-control"}),
            "export_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "destination": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ExportItemForm(forms.ModelForm):
    stock_item = forms.ModelChoiceField(
        queryset=StockItem.objects.filter(quantity__gt=0).order_by("expiry_date"),
        label="Lô hàng (FEFO)",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = ExportItem
        fields = ["stock_item", "quantity", "unit_price", "discount_percent", "unit"]
        labels = {
            "stock_item": "Lô hàng",
            "quantity": "Số lượng xuất",
            "unit_price": "Đơn giá (₫)",
            "discount_percent": "Chiết khấu (%)",
            "unit": "Đơn vị",
        }
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control text-end quantity", "min": 1}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control text-end unit-price", "min": 0, "step": 0.01}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control text-end discount", "min": 0, "step": 0.01, "value": "0"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
        }




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
        fields = ["return_code", "return_date", "note"]  # bỏ return_type
        labels = {
            "return_code": "Mã phiếu hoàn",
            "return_date": "Ngày hoàn",
            "note": "Ghi chú",
        }
        widgets = {
            "return_code": forms.TextInput(attrs={"class": "form-control"}),
            "return_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }



class ReturnItemForm(forms.ModelForm):
    class Meta:
        model = ReturnItem
        fields = ["product", "quantity", "unit", "unit_price", "expiry_date","location", "reason", "detail_note"]
        labels = {
            "product": "Sản phẩm hoàn",
            "quantity": "Số lượng hoàn",
            "unit": "Đơn vị",
            "location": "Vị trí",
            "reason": "Lý do hoàn hàng",
            "detail_note": "Ghi chú chi tiết",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control quantity text-end",
                "min": 1
            }),
            "unit_price": forms.NumberInput(attrs={
                "class": "form-control unit-price text-end",
                "min": 0
            }),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

ReturnItemFormSet = inlineformset_factory(
    ReturnReceipt, ReturnItem,
    form=ReturnItemForm,
    extra=1,
    can_delete=True
)


# ===================== FORM ĐƠN ĐẶT HÀNG =====================
from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseOrder, PurchaseOrderItem

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["po_code", "supplier", "note", "status"]
        labels = {
            "po_code": "Mã PO",
            "supplier": "Nhà cung ứng",
            "note": "Ghi chú",
            "status": "Trạng thái",
        }
        widgets = {
            "po_code": forms.TextInput(attrs={"class": "form-control"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["po_code"].widget.attrs.update({
                "readonly": True,
                "class": "form-control bg-light"
            })
            self.fields["supplier"].widget.attrs.update({"class": "form-select"})
            self.fields["status"].widget.attrs.update({"class": "form-select"})
            self.fields["note"].widget.attrs.update({"class": "form-control", "rows": 3})

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["product", "quantity", "unit"]
        labels = {
            "product": "Sản phẩm",
            "quantity": "Số lượng",
            "unit": "Đơn vị",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "VD: Thùng"}),
        }

# Inline formset gắn item vào PO
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
        fields = ["asn_code", "po", "supplier", "deliverer_name", "deliverer_phone", "expected_date"]
        labels = {
            "asn_code": "Mã ASN",
            "po": "Đơn đặt hàng (PO)",
            "supplier": "Nhà cung ứng",
            "deliverer_name": "Người giao hàng",
            "deliverer_phone": "Số điện thoại",
            "expected_date": "Ngày dự kiến giao",
        }
        widgets = {
            "asn_code": forms.TextInput(attrs={"class": "form-control"}),
            "po": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "deliverer_name": forms.TextInput(attrs={"class": "form-control"}),
            "deliverer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "expected_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


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
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

ASNItemFormSet = inlineformset_factory(
    ASN, ASNItem,
    form=ASNItemForm,
    extra=1,
    can_delete=True
)
