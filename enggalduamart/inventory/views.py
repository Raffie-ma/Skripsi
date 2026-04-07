from django.shortcuts import render, redirect, get_object_or_404
from .forms import BarangDatangForm
from django.db.models import Q 
from django.db.models import F
from django.http import HttpResponseForbidden
from .models import User, Barang, Pemesanan, Notifikasi,TransaksiKeuangan,Retur,TransaksiPenjualan,DetailPenjualan
from django import forms
from django.db import models ,transaction
from django.db.models import F, ExpressionWrapper, DecimalField,Sum
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.utils import timezone
from django.contrib import messages


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = user.role
            return redirect('dashboard')
        except User.DoesNotExist:
            context = {'error': 'Username / password salah'}
            return render(request, 'login.html', context)

    return render(request, 'login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


def require_login(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(*allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            user_role = request.session.get('role')

            if user_role not in allowed_roles:
                return HttpResponseForbidden("Tidak punya akses.")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator



@require_login
def dashboard(request):
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    barang_list = Barang.objects.all().order_by('nama_barang')
    low_stock = Barang.objects.filter(stock__lte=F('batas_minimal'))
    notif_list = Notifikasi.objects.filter(user_id=user_id, dibaca=False).order_by('-id')
    filter_barang = request.GET.get('filter')
    pencarian = request.GET.get('pencarian', '')
    transaksi = TransaksiKeuangan.objects.filter()
    pemasukan = transaksi.filter(jenis='masuk').aggregate(total=Sum('total'))['total'] or 0
    if pencarian:
        barang_list = barang_list.filter(
            Q(nama_barang__icontains=pencarian)|Q(kode_barang__icontains=pencarian))
    
    if filter_barang == 'menipis':
        barang_list = barang_list.filter(
        stock__lte=F('batas_minimal'),
        stock__gt=0
    )
    
    total_barang = Barang.objects.count()
    barang_menipis = Barang.objects.filter(stock__lte=F('batas_minimal')).count()
    total_stok = Barang.objects.aggregate(total=Sum('stock'))['total'] or 0
    total_nilai = Barang.objects.annotate(nilai=ExpressionWrapper( F('stock') * F('harga'),output_field=DecimalField())).aggregate(total=Sum('nilai'))['total'] or 0
    barang_terlaris = (DetailPenjualan.objects.values('barang__nama_barang').annotate(total_terjual=Sum('jumlah')).order_by('-total_terjual')[:5])
    
    context = {
        'role': role,
        'barang_list': barang_list,
        'low_stock': low_stock,
        'notif_list': notif_list,
        'pencarian' : pencarian,
        'total_barang': total_barang,
        'barang_menipis': barang_menipis,
        'total_stok': total_stok,
        'total_nilai': total_nilai,
        'filter_barang' : filter_barang,
        'barang_terlaris': barang_terlaris,
        'pemasukan':pemasukan
    }

    if role == 'admin':
        return render(request, 'dashboard_admin.html', context)
    else:
        return render(request, 'dashboard_karyawan.html', context)


class BarangForm(forms.ModelForm):
    class Meta:
        model = Barang
        fields = ['kode_barang','nama_barang', 'stock', 'harga']

from django.contrib import messages

@require_login
@require_role('admin')
def set_batas_minimal(request):
    if request.method == 'POST':
        batas = request.POST.get('batas_minimal')

        if batas and batas.isdigit():
            batas = int(batas)

            Barang.objects.all().update(batas_minimal=batas)

            messages.success(request, f"Batas minimal berhasil diubah menjadi {batas} untuk semua barang.")
            return redirect('dashboard')

    return render(request, 'set_batas_minimal.html',{
        'role':'admin',
    })


from django.db.models import Q, F

@require_login
@require_role('admin')
def barang_list(request):
    q = request.GET.get('q', '')
    filter_status = request.GET.get('filter')  
    barang_qs = Barang.objects.all().order_by('nama_barang') 
    
    if q:
        barang_qs = barang_qs.filter(
            Q(nama_barang__icontains=q) |
            Q(kode_barang__icontains=q)
        )

    if filter_status == 'menipis':
        barang_qs = barang_qs.filter(
        stock__lte=F('batas_minimal'),
        stock__gt=0
    )

    context = {
        'role': request.session.get('role'),
        'barang_list': barang_qs,
        'q': q,
    }
    return render(request, 'barang_list.html', context)


@require_login
@require_role('admin')
def barang_create(request):
    if request.method == 'POST':
        form = BarangForm(request.POST)
        if form.is_valid():
            barang = form.save()
            if barang.stock <= barang.batas_minimal:
                karyawan_list = User.objects.filter(role='karyawan')
                for u in karyawan_list:
                    Notifikasi.objects.create(
                        user=u,
                        barang=barang,
                        pesan=f"Stok {barang.nama_barang} menipis ({barang.stock})"
                    )

            messages.success(request, "Barang berhasil ditambahkan",extra_tags='barang')
            return redirect('barang_list')
        else:
            message.error(request,"isi data dengan benar")
    else:
        form = BarangForm()

    return render(request, 'barang_form.html', {'form': form,'judul': 'Tambah Barang'})



@require_login
@require_role('admin')
def barang_update(request, kode_barang):
    barang = get_object_or_404(Barang, pk=kode_barang)
    stok_lama = barang.stock  

    if request.method == 'POST':
        form = BarangForm(request.POST, instance=barang)
        if form.is_valid():
            barang = form.save(commit=False)
            stok_baru = barang.stock
            barang.save()

            
            if stok_baru < stok_lama:
                jumlah_terjual = stok_lama - stok_baru
                total = jumlah_terjual * barang.harga

                TransaksiKeuangan.objects.create(
                    jenis='masuk',
                    jumlah=jumlah_terjual,
                    total=total,
                    keterangan=f"Penjualan {barang.nama_barang}"
                )


            if barang.stock <= barang.batas_minimal:
                karyawan_list = User.objects.filter(role='karyawan')
                for u in karyawan_list:
                    Notifikasi.objects.get_or_create(
                        user=u,
                        barang=barang,
                        pesan=f"Stok {barang.nama_barang} menipis ({barang.stock})",
                        dibaca=False
                    )

            messages.success(request, "Barang berhasil ditambahkan",extra_tags='barang')
            return redirect('barang_list')
    else:
        form = BarangForm(instance=barang)

    return render(request, 'barang_form.html', {'form': form,'judul': 'Edit Barang',})



@require_login
def notif_baca(request, pk):
    notif = get_object_or_404(
        Notifikasi,
        pk=pk,
        user_id=request.session.get('user_id')
    )
    notif.dibaca = True
    notif.save()
    return redirect('dashboard')

@require_login
@require_role('admin')
def barang_delete(request, kode_barang):
    barang = get_object_or_404(Barang, pk=kode_barang)

    if request.method == 'POST':
        barang.delete()
        return redirect('barang_list')

    return render(request, 'barang_confirm_delete.html', {
        'barang': barang,
    })

class PemesananForm(forms.ModelForm):
    class Meta:
        model = Pemesanan
        fields = ['jumlah']

@require_login
@require_role('karyawan')
def pemesanan_create(request, kode_barang):
    barang = get_object_or_404(Barang, pk=kode_barang)
    user = get_object_or_404(User, pk=request.session.get('user_id'))  

    if request.method == 'POST':
        form = PemesananForm(request.POST)
        if form.is_valid():
            pemesanan = form.save(commit=False)
            pemesanan.barang = barang              
            pemesanan.user_2 = user                
            pemesanan.status_2 = 'pending'
            pemesanan.save()
            return redirect('pemesanan_list')
    else:
        form = PemesananForm()

    return render(request, 'pemesanan_form.html', {
        'form': form,
        'barang': barang,
    })


@require_login
def pemesanan_list(request):
    role = request.session.get('role')
    user_id = request.session.get('user_id')

    bulan_input = request.GET.get('bulan')

    
    if not bulan_input:
        now = timezone.now()
        bulan_input = f"{now.year}-{now.month:02d}"

    tahun, bulan = bulan_input.split('-')

    pesanan = Pemesanan.objects.select_related('barang','user_2')

    if role != 'admin':
        pesanan = pesanan.filter(user_2_id=user_id)

    pesanan = pesanan.filter(
        tanggal_pesan__year=tahun,
        tanggal_pesan__month=bulan
    ).order_by('-tanggal_pesan')

    context = {
        'pemesanan_list': pesanan,
        'role': role,
        'bulan': bulan_input
    }

    return render(request, 'pemesanan_list.html', context)


@require_login
@require_role('admin')
def pemesanan_verifikasi_list(request):
    pesanan = Pemesanan.objects.select_related('barang', 'user_2') \
                               .filter(status_2='pending') \
                               .order_by('-tanggal_pesan')
    context = {
        'role': 'admin',
        'pemesanan_list': pesanan,
    }
    return render(request, 'verifikasi_barang.html', context)



@require_login
@require_role('admin')
@transaction.atomic
def pemesanan_verifikasi(request, pk, aksi):
    pemesanan = get_object_or_404(Pemesanan, pk=pk)

    if pemesanan.status_2 != 'pending':
        return redirect('pemesanan_verifikasi_list')

    if aksi == 'setuju':   
        pemesanan.status_2 = 'disetujui'
        pemesanan.save()

        
        user_id = request.session.get('user_id')
        if user_id:
            Notifikasi.objects.create(
                user_id=pemesanan.user_2_id,  
                barang=pemesanan.barang,
                pesan=f"Pemesanan {pemesanan.barang.nama_barang} disetujui!"
            )
            
    elif aksi == 'tolak':
        pemesanan.status_2 = 'ditolak'
        pemesanan.save()

    return redirect('pemesanan_verifikasi_list')


@require_login
@require_role('karyawan')
@transaction.atomic
def barang_datang_konfirmasi(request, pk):
    pemesanan = get_object_or_404(Pemesanan,pk=pk,user_2_id=request.session.get('user_id') )

    if pemesanan.status_2 != 'disetujui':
        return redirect('pemesanan_list')

   
    if request.method == 'GET':
        form = BarangDatangForm(instance=pemesanan)
        return render(request, 'barang_datang_form.html', {'form': form, 'pemesanan': pemesanan })

    elif request.method == 'POST':
        form = BarangDatangForm(request.POST, instance=pemesanan)
        if form.is_valid():
            jumlah_datang = form.cleaned_data['jumlah_datang']

            if jumlah_datang > pemesanan.jumlah:
                form.add_error( 'jumlah_datang','Jumlah datang tidak boleh melebihi jumlah disetujui' )
            else:
                pemesanan = form.save(commit=False)
                pemesanan.status_2 = 'datang'
                pemesanan.save()

                pemesanan.jumlah_datang = jumlah_datang
                pemesanan.status_2 = 'datang'
                pemesanan.save()

                barang = pemesanan.barang
                barang.stock += jumlah_datang
                barang.save()


                return redirect('pemesanan_list')

        return render(request, 'barang_datang_form.html', {
            'form': form,
            'pemesanan': pemesanan
        })


@require_login
@require_role('admin')
def laporan_barang_datang(request):
    pemesanan_list = Pemesanan.objects.filter(status_2='datang').select_related('barang', 'user_2').order_by('-tanggal_pesan')

    return render(request, 'laporan_barang_datang.html', {
        'pemesanan_list': pemesanan_list,
        'role': 'admin'
    })

@require_login
@require_role('admin','karyawan')
def laporan_keuangan(request):
    tanggal_input = request.GET.get('tanggal')
    if tanggal_input:
        tanggal_filter = tanggal_input
    else:
        tanggal_filter = timezone.now().date()

    transaksi = TransaksiKeuangan.objects.filter(tanggal__date=tanggal_filter).order_by('-tanggal')
    pemasukan = transaksi.filter(jenis='masuk').aggregate(total=Sum('total'))['total'] or 0
    pengeluaran = transaksi.filter(jenis='keluar').aggregate( total=Sum('total'))['total'] or 0
    saldo = pemasukan - pengeluaran

    return render(request, 'laporan_keuangan.html', {
        'role': request.session.get('role'),
        'transaksi': transaksi,
        'pemasukan': pemasukan,
        'pengeluaran': pengeluaran,
        'saldo': saldo,
        'tanggal':tanggal_filter
    })

@require_login
@require_role('karyawan','admin')
def daftar_retur(request):
    returs = Retur.objects.select_related('barang', 'user').all().order_by('-tanggal_retur')
    return render(request, 'daftar_retur.html', {
        'returs': returs,
        'role': request.session.get('role'),
        })

@require_login
@require_role('karyawan','admin')
def tambah_retur(request):
    barangs = Barang.objects.all()

    if request.method == 'POST':
        kode_barang = request.POST.get('barang')
        jumlah = int(request.POST.get('jumlah'))
        alasan = request.POST.get('alasan')
        keterangan = request.POST.get('keterangan')

        barang = get_object_or_404(Barang, kode_barang=kode_barang)
        user_id = request.session.get('user_id')
        user = get_object_or_404(User, id=user_id)

        if jumlah > barang.stock:
            messages.error(request, "Jumlah retur melebihi stok!")
            return redirect('tambah_retur')

        Retur.objects.create(
            barang=barang,
            user=user,
            jumlah=jumlah,
            alasan=alasan,
            keterangan=keterangan
        )

        messages.success(request, "Retur berhasil ditambahkan!")
        return redirect('daftar_retur')

    return render(request, 'tambah_retur.html', {
        'barangs': barangs,
        'role': request.session.get('role'),

        })

@require_login
@require_role('admin')
def ubah_status_retur(request, id):
    retur = get_object_or_404(Retur, id=id)

    if request.session.get('role') != 'admin':
        messages.error(request, "Akses ditolak!")
        return redirect('daftar_retur')

    status_baru = request.POST.get('status')
    retur.status = status_baru
    retur.save()

    messages.success(request, "Status retur berhasil diubah!")
    return redirect('daftar_retur')

@require_login
@require_role('karyawan')
def kasir(request):

    barangs = Barang.objects.all()

    keranjang = request.session.get('keranjang', [])

    total = 0
    for item in keranjang:
        total += item['subtotal']

    return render(request, 'kasir.html', {
        'role' :'karyawan',
        'barangs': barangs,
        'keranjang': keranjang,
        'total': total
    })


def tambah_ke_keranjang(request):

    if request.method == "POST":

        kode_barang = request.POST.get('barang')
        jumlah = int(request.POST.get('jumlah'))

        barang = get_object_or_404(Barang, kode_barang=kode_barang)

        keranjang = request.session.get('keranjang', [])

        subtotal = barang.harga * jumlah

        keranjang.append({
            'kode': barang.kode_barang,
            'nama': barang.nama_barang,
            'harga': float(barang.harga),
            'jumlah': jumlah,
            'subtotal': float(subtotal)
        })

        request.session['keranjang'] = keranjang

    return redirect('kasir')

def proses_bayar(request):

    keranjang = request.session.get('keranjang', [])

    if not keranjang:
        messages.error(request, "Keranjang kosong")
        return redirect('kasir')

    total = 0
    total_barang = 0
    daftar_barang = []

    transaksi = TransaksiPenjualan.objects.create(
        kasir_id=request.session.get('user_id'),
        total=0
    )

    for item in keranjang:
        barang = Barang.objects.get(kode_barang=item['kode'])

        if barang.stock < item['jumlah']:
            messages.error(request, f"Stok {barang.nama_barang} tidak cukup")
            return redirect('kasir')

        barang.stock -= item['jumlah']
        barang.save()

        DetailPenjualan.objects.create(
            transaksi=transaksi,
            barang=barang,
            jumlah=item['jumlah'],
            harga=item['harga'],
            subtotal=item['subtotal']
        )

        total += item['subtotal']
        total_barang += item['jumlah']

        
        daftar_barang.append(f"{barang.nama_barang} {item['jumlah']}x")

    transaksi.total = total
    transaksi.save()
    keterangan_barang = "\n".join(daftar_barang)
    TransaksiKeuangan.objects.create(
        jenis='masuk',
        keterangan=keterangan_barang,
        jumlah=total_barang,
        total=total
    )

    request.session['keranjang'] = []

    messages.success(request, "Transaksi berhasil")

    return redirect('kasir')
