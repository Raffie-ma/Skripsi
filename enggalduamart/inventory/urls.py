from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    
    path('barang/', views.barang_list, name='barang_list'),
    path('barang/tambah/', views.barang_create, name='barang_create'),
    path('barang/<str:kode_barang>/edit/', views.barang_update, name='barang_update'),
    path('barang/<str:kode_barang>/delete/', views.barang_delete, name='barang_delete'),
    path('barang/datang/<int:pk>/',views.barang_datang_konfirmasi,name='barang_datang_konfirmasi'),
  

  
    path('pemesanan/', views.pemesanan_list, name='pemesanan_list'),
    path('pemesanan/tambah/<int:kode_barang>/', views.pemesanan_create, name='pemesanan_create'),
    path('pemesanan/verifikasi/', views.pemesanan_verifikasi_list,name='pemesanan_verifikasi_list'),
    path('pemesanan/<int:pk>/verifikasi/<str:aksi>/',views.pemesanan_verifikasi,name='pemesanan_verifikasi'),
    path('pemesanan/<int:pk>/datang/', views.barang_datang_konfirmasi, name='barang_datang_konfirmasi'),
    
    path('notifikasi/baca/<int:pk>/', views.notif_baca, name='notif_baca'),
    path('laporan/barang-datang/',views.laporan_barang_datang, name='laporan_barang_datang'),
    path('laporan/keuangan/', views.laporan_keuangan, name='laporan_keuangan'),
    path('setting/batas-minimal/', views.set_batas_minimal, name='set_batas_minimal'),

    path('retur/', views.daftar_retur, name='daftar_retur'),
    path('retur/tambah/', views.tambah_retur, name='tambah_retur'),
    path('retur/ubah-status/<int:id>/', views.ubah_status_retur, name='ubah_status_retur'),

    path('kasir/', views.kasir, name='kasir'),
    path('kasir/tambah/', views.tambah_ke_keranjang, name='tambah_keranjang'),
    path('kasir/bayar/', views.proses_bayar, name='proses_bayar'),

]
