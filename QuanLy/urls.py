from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.products, name='products'),
    path('categories/', views.categories, name='categories'),
    path('import/', views.import_goods, name='import'),
    path('export/', views.export_goods, name='export'),
    path('return/', views.return_goods, name='return'),
    path('po/', views.po, name='po'),
    path('asn/', views.asn, name='asn'),
    path('suppliers/', views.suppliers, name='suppliers'),
    path('reports/', views.reports, name='reports'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

]
