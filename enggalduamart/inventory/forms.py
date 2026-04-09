from django import forms
from .models import Pemesanan, Barang

class BarangDatangForm(forms.ModelForm):
    class Meta:
        model = Pemesanan
        fields = ['jumlah_datang', 'keterangan']

        widgets = {
            'jumlah_datang': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'keterangan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Contoh: 2 rusak, 1 bocor'
            }),
        }

class BarangForm(forms.ModelForm):
    class Meta:
        model = Barang
        fields = '__all__'
        error_messages = {
            'kode_barang': {
                'unique': '⚠️ Kode barang sudah digunakan!'
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
           self.fields['kode_barang'].disabled = True
           self.fields['kode_barang'].widget.attrs.update({'readonly': True,'class': 'form-control bg-light' })

    def clean_kode_barang(self):
        if self.instance and self.instance.pk:
            return self.instance.kode_barang
        return self.cleaned_data.get('kode_barang')