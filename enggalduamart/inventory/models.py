from django.db import models

class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('karyawan', 'Karyawan'),
    ]
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255)  
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Barang(models.Model):
    kode_barang = models.IntegerField(primary_key=True)
    nama_barang = models.CharField(max_length=100)
    stock = models.IntegerField()
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    batas_minimal = models.IntegerField(default=15)

    def __str__(self):
        return self.nama_barang

    @property
    def is_low_stock(self):
        return self.stock <= self.batas_minimal

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not is_new:
            try:
                barang_lama = Barang.objects.get(pk=self.pk)

                if barang_lama.stock > barang_lama.batas_minimal and self.stock <= self.batas_minimal:
                    self.cek_dan_buat_notifikasi()

            except Barang.DoesNotExist:
                pass

        
        super().save(*args, **kwargs)

    def cek_dan_buat_notifikasi(self):
        if self.is_low_stock:
            users = User.objects.all()

            for user in users:
                Notifikasi.objects.get_or_create(
                    user=user,
                    barang=self,
                    pesan=f"Stok {self.nama_barang} menipis ({self.stock})",
                    dibaca=False
                )

class Pemesanan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('disetujui', 'Disetujui'),
        ('datang','Barang Datang'),
        ('ditolak', 'Ditolak'),
    ]
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    user_2 = models.ForeignKey(User, on_delete=models.CASCADE)
    jumlah = models.IntegerField()
    status_2 = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tanggal_pesan = models.DateField(auto_now_add=True)
    tanggal_datang = models.DateField(null=True, blank=True)
    jumlah_datang = models.IntegerField(null=True, blank=True)
    jumlah_rusak = models.IntegerField(null=True, blank=True, default=0) 
    keterangan = models.TextField(null=True, blank=True)

    
    def __str__(self):
        return f"Pesan {self.barang.nama_barang} x {self.jumlah}"
    


class Notifikasi(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    pesan = models.TextField()
    dibaca = models.BooleanField(default=False)

    def __str__(self):
        return self.pesan

class TransaksiKeuangan(models.Model):
    JENIS = (
        ('masuk', 'Pemasukan'),
        ('keluar', 'Pengeluaran'),
    )

    tanggal = models.DateTimeField(auto_now_add=True)
    jenis = models.CharField(max_length=10, choices=JENIS)
    keterangan = models.TextField()
    jumlah = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.jenis} - {self.total}"

class Retur(models.Model):

    STATUS_CHOICES = [
        ('menunggu', 'Menunggu'),
        ('disetujui', 'Disetujui'),
        ('ditolak', 'Ditolak'),
    ]

    ALASAN_CHOICES = [
        ('rusak', 'Barang Rusak'),
        ('expired', 'Expired'),
        ('salah_kirim', 'Salah Kirim'),
        ('lainnya', 'Lainnya'),
    ]

    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    jumlah = models.PositiveIntegerField()
    alasan = models.CharField(max_length=20, choices=ALASAN_CHOICES)
    keterangan = models.TextField(blank=True, null=True)

    tanggal_retur = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='menunggu')

    def save(self, *args, **kwargs):
        
        if self.pk: 
            retur_lama = Retur.objects.get(pk=self.pk)

            if retur_lama.status != 'disetujui' and self.status == 'disetujui':
                
                self.barang.stock -= self.jumlah
                self.barang.save()

        super().save(*args, **kwargs)
    def __str__(self):
        return f"Retur {self.barang.nama_barang} x {self.jumlah}"

class TransaksiPenjualan(models.Model):
    kasir = models.ForeignKey(User, on_delete=models.CASCADE)
    tanggal = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Transaksi {self.id}"

class DetailPenjualan(models.Model):
    transaksi = models.ForeignKey(TransaksiPenjualan, on_delete=models.CASCADE)
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    jumlah = models.IntegerField()
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.barang.nama_barang
