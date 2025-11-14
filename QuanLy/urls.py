from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ĐẶT HOME = home_redirect
    path('', views.home_redirect, name='home'),

    # ===================== DASHBOARD =====================
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

    # ===================== SẢN PHẨM KINH DOANH =====================
    path('product-master/', views.product_master_list, name='product_master_list'),
    path('product-master/add/', views.add_product_master, name='add_product_master'),
    path('product-master/edit/<str:pk>/', views.edit_product_master, name='edit_product_master'),
    path('product-master/delete/<str:pk>/', views.delete_product_master, name='delete_product_master'),

    # ===================== TỒN KHO =====================
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/edit/<int:pk>/', views.edit_stock, name='edit_stock'),

    # ===================== NHẬP KHO =====================
    path('import/', views.import_list, name='import_list'),
    path('import/new/', views.create_import, name='create_import'),
    path('import/delete/<str:code>/', views.delete_import, name='delete_import'),
    path("import/export/<str:code>/", views.import_export_pdf, name="import_export_pdf"),


    # ===================== XUẤT KHO =====================
    path('export/', views.export_list, name='export_list'),
    path('export/new/', views.create_export, name='create_export'),
    path('export/delete/<str:code>/', views.delete_export, name='delete_export'),
    path("export/export/<str:code>/", views.export_export_pdf, name="export_export_pdf"),

    # ===================== HOÀN HÀNG =====================
    path('return/', views.return_list, name='return_list'),
    path('return/new/', views.create_return, name='create_return'),
    path('return/delete/<str:code>/', views.delete_return, name='delete_return'),
    path("return/export/<str:code>/", views.return_export_pdf, name="return_export_pdf"),


    # ===================== ĐƠN ĐẶT HÀNG (PO) =====================
    path('po/', views.po_list, name='po_list'),
    path('po/new/', views.create_po, name='create_po'),
    path("po/edit/<str:code>/", views.po_edit, name="po_edit"),
    path('po/delete/<str:code>/', views.delete_po, name='delete_po'),
    path('po/export/<str:code>/', views.po_export_pdf, name="po_export_pdf"),


    # ===================== ASN =====================
    path('asn/', views.asn_list, name='asn_list'),
    path('asn/new/', views.create_asn, name='create_asn'),
    path("asn/delete/<str:code>/", views.delete_asn, name="delete_asn"),
    path("asn/export/<str:code>/", views.asn_export_pdf, name="asn_export_pdf"),


    # ===================== BÁO CÁO =====================
    path('reports/', views.reports, name='reports'),

    # ===================== ĐĂNG NHẬP / ĐĂNG XUẤT =====================
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
