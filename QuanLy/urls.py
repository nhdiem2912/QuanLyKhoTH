from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    path('', views.home_redirect, name='home'),

    # ===================== TRANG CH =====================
    path('dashboard/', views.index, name='index'),


    # ===================== DANH MỤC =====================
    path('categories/', views.categories, name='categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<str:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<str:pk>/', views.delete_category, name='delete_category'),

    # ===================== NHÀ CUNG ỨNG =====================
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/edit/<str:pk>/', views.edit_supplier, name='edit_supplier'),

    # ===================== TỒN KHO =====================
    path('stock/', views.stock_list, name='stock_list'),

    # ===================== NHẬP KHO =====================
    path('import/', views.import_list, name='import_list'),
    path('import/new/', views.create_import, name='create_import'),
    path("import/export/<str:code>/", views.import_export_pdf, name="import_export_pdf"),


    # ===================== XUẤT KHO =====================
    path('export/', views.export_list, name='export_list'),
    path('export/new/', views.create_export, name='create_export'),
    path("export/export/<str:code>/", views.export_export_pdf, name="export_export_pdf"),

    # ===================== HOÀN HÀNG =====================
    path('return/', views.return_list, name='return_list'),
    path('return/new/', views.create_return, name='create_return'),
    path("return/export/<str:code>/", views.return_export_pdf, name="return_export_pdf"),

    # ===================== ĐƠN ĐẶT HÀNG (PO) =====================
    path('po/', views.po_list, name='po_list'),
    path("po/create/", views.create_po, name="po_create"),

    path("po/edit/<str:code>/", views.po_edit, name="po_edit"),
    path('po/export/<str:code>/', views.po_export_pdf, name="po_export_pdf"),


    # ===================== ASN =====================
    path('asn/', views.asn_list, name='asn_list'),
    path('asn/new/', views.create_asn, name='create_asn'),
    path("asn/<str:code>/edit/", views.edit_asn, name="asn_edit"),
    path("asn/export/<str:code>/", views.asn_export_pdf, name="asn_export_pdf"),

    # ===================== BÁO CÁO =====================
    path('reports/', views.reports, name='reports'),

    # ===================== API ENDPOINTS =====================
    path('api/supplier-products/<str:supplier_id>/', views.api_supplier_products, name='api_supplier_products'),
    path('api/po-details/<str:po_id>/', views.api_po_details, name='api_po_details'),
    path('api/export-items/<str:export_code>/', views.api_export_items, name='api_export_items'),
    path('api/asn-items/<str:asn_code>/', views.api_asn_items, name='api_asn_items'),
    path("api/asn-items/<str:asn_code>/", views.api_asn_items, name="api_asn_items"),
    path('suppliers/<str:pk>/history/', views.supplier_history, name='supplier_history'),


    # ===================== ĐĂNG NHẬP / ĐĂNG XUẤT =====================
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),

]
