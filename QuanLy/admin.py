from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Supplier)
admin.site.register(ImportReceipt)
admin.site.register(ExportReceipt)
admin.site.register(ReturnReceipt)
admin.site.register(PurchaseOrder)
admin.site.register(ASN)
admin.site.register(Report)