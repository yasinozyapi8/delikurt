import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup


# Örnek Stok Veritabanı
stok_veritabani = {
    "8690000000001": {"ad": "Rulman 6204", "kategori": "Rulman", "stok": 15},
    "8690000000002": {"ad": "Yağ Filtresi H-12", "kategori": "Filtre", "stok": 8}
}


class AnaStokEkrani(Screen):
    """Ana Stok Listesi ve Barkod Arama Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stok_liste'
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Üst Panel: Barkod Oku / Ara Girişi
        scan_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='50dp')
        
        self.txt_scan = TextInput(
            hint_text='Barkod No Girin / Okutun...',
            multiline=False,
            font_size='18sp',
            size_hint_x=0.7
        )
        btn_scan = Button(
            text='İşle',
            size_hint_x=0.3,
            background_color=(0.2, 0.6, 0.8, 1),
            bold=True
        )
        btn_scan.bind(on_release=self.barkod_isle)
        
        scan_box.add_widget(self.txt_scan)
        scan_box.add_widget(btn_scan)
        main_layout.add_widget(scan_box)
        
        # Stok Liste Alanı (ScrollView)
        main_layout.add_widget(Label(text="Mevcut Stok Listesi", size_hint_y=None, height='30dp', bold=True))
        
        scroll = ScrollView()
        self.grid_stok = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.grid_stok.bind(minimum_height=self.grid_stok.setter('height'))
        
        scroll.add_widget(self.grid_stok)
        main_layout.add_widget(scroll)
        
        # Alt Panel: Ekran Değiştirme Butonu
        btn_go_add = Button(
            text='Manuel Yedek Parça Ekle',
            size_hint_y=None,
            height='50dp',
            background_color=(0.3, 0.3, 0.3, 1),
            bold=True
        )
        btn_go_add.bind(on_release=self.parca_ekle_sayfasina_git)
        main_layout.add_widget(btn_go_add)
        
        self.add_widget(main_layout)

    def on_enter(self):
        """Ekrana her dönüldüğünde stok listesini günceller"""
        self.stok_listesini_yenile()

    def stok_listesini_yenile(self):
        self.grid_stok.clear_widgets()
        for barkod, bilgi in stok_veritabani.items():
            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='45dp', padding=5)
            lbl = Label(
                text=f"[{barkod}] {bilgi['ad']} | Kat: {bilgi['kategori']} | Stok: {bilgi['stok']}",
                halign='left',
                valign='middle'
            )
            lbl.bind(size=lbl.setter('text_size'))
            item_box.add_widget(lbl)
            self.grid_stok.add_widget(item_box)

    def barkod_isle(self, instance):
        barkod = self.txt_scan.text.strip()
        if barkod:
            App.get_running_app().process_barcode_scan(barkod)
            self.txt_scan.text = ''

    def parca_ekle_sayfasina_git(self, instance):
        self.manager.current = 'parca_ekle'


class ParcaEkleEkrani(Screen):
    """Listede Olmayan Yeni Ürün Kayıt Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'parca_ekle'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12)
        
        layout.add_widget(Label(text="Yeni Yedek Parça Kaydı", font_size='22sp', bold=True, size_hint_y=None, height='40dp'))
        
        # Barkod
        layout.add_widget(Label(text="Barkod No:", size_hint_y=None, height='25dp', halign='left'))
        self.txt_barkod = TextInput(multiline=False, font_size='18sp', size_hint_y=None, height='45dp')
        layout.add_widget(self.txt_barkod)
        
        # Parça Adı
        layout.add_widget(Label(text="Parça Adı:", size_hint_y=None, height='25dp', halign='left'))
        self.txt_ad = TextInput(multiline=False, font_size='18sp', size_hint_y=None, height='45dp')
        layout.add_widget(self.txt_ad)
        
        # Kategori
        layout.add_widget(Label(text="Kategori:", size_hint_y=None, height='25dp', halign='left'))
        self.txt_kategori = TextInput(multiline=False, font_size='18sp', size_hint_y=None, height='45dp')
        layout.add_widget(self.txt_kategori)
        
        # Başlangıç Stok
        layout.add_widget(Label(text="Başlangıç Stok Adedi:", size_hint_y=None, height='25dp', halign='left'))
        self.txt_stok = TextInput(text="1", input_filter="int", multiline=False, font_size='18sp', size_hint_y=None, height='45dp')
        layout.add_widget(self.txt_stok)
        
        # Butonlar
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height='50dp')
        
        btn_kaydet = Button(text="Kaydet", background_color=(0.2, 0.7, 0.2, 1), bold=True)
        btn_kaydet.bind(on_release=self.parca_kaydet)
        
        btn_iptal = Button(text="İptal", background_color=(0.8, 0.2, 0.2, 1), bold=True)
        btn_iptal.bind(on_release=self.iptal_et)
        
        btn_box.add_widget(btn_kaydet)
        btn_box.add_widget(btn_iptal)
        layout.add_widget(btn_box)
        
        self.add_widget(layout)

    def parca_kaydet(self, instance):
        barkod = self.txt_barkod.text.strip()
        ad = self.txt_ad.text.strip()
        kategori = self.txt_kategori.text.strip() or "Genel"
        stok = int(self.txt_stok.text) if self.txt_stok.text else 1
        
        if barkod and ad:
            stok_veritabani[barkod] = {
                "ad": ad,
                "kategori": kategori,
                "stok": stok
            }
            self.formu_temizle()
            self.manager.current = 'stok_liste'

    def iptal_et(self, instance):
        self.formu_temizle()
        self.manager.current = 'stok_liste'

    def formu_temizle(self):
        self.txt_barkod.text = ''
        self.txt_ad.text = ''
        self.txt_kategori.text = ''
        self.txt_stok.text = '1'


class MobileApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.stok_ekrani = AnaStokEkrani()
        self.parca_ekrani = ParcaEkleEkrani()
        
        self.sm.add_widget(self.stok_ekrani)
        self.sm.add_widget(self.parca_ekrani)
        return self.sm

    def process_barcode_scan(self, barcode_data):
        """Barkod kontrolünü sağlayan ana mantık fonksiyonu"""
        barcode = str(barcode_data).strip()
        
        if barcode in stok_veritabani:
            # 1. Ürün Var -> Stok Ekle / Çıkar Popup'ı Aç
            self.show_stock_update_popup(barcode)
        else:
            # 2. Ürün Yok -> Parça Ekle Sayfasına Geç ve Barkodu Doldur
            self.parca_ekrani.txt_barkod.text = barcode
            self.sm.current = 'parca_ekle'

    def show_stock_update_popup(self, barcode):
        urun = stok_veritabani[barcode]
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        layout.add_widget(Label(text=f"Ürün: {urun['ad']}\nMevcut Stok: {urun['stok']}", font_size='16sp'))
        
        qty_input = TextInput(text="1", input_filter="int", multiline=False, font_size='20sp', halign='center')
        layout.add_widget(qty_input)
        
        btn_layout = BoxLayout(spacing=10, size_hint_y=0.6)
        btn_add = Button(text="Stok Ekle (+)", background_color=(0.2, 0.7, 0.2, 1), font_size='16sp', bold=True)
        btn_sub = Button(text="Stok Çıkar (-)", background_color=(0.8, 0.2, 0.2, 1), font_size='16sp', bold=True)
        
        btn_layout.add_widget(btn_add)
        btn_layout.add_widget(btn_sub)
        layout.add_widget(btn_layout)
        
        popup = Popup(title="Stok Adedi Güncelle", content=layout, size_hint=(0.85, 0.45))
        
        def update_qty(is_addition):
            try:
                miktar = int(qty_input.text) if qty_input.text else 0
                if is_addition:
                    urun['stok'] += miktar
                else:
                    urun['stok'] = max(0, urun['stok'] - miktar)
                
                self.stok_ekrani.stok_listesini_yenile()
                popup.dismiss()
            except ValueError:
                pass

        btn_add.bind(on_release=lambda x: update_qty(True))
        btn_sub.bind(on_release=lambda x: update_qty(False))
        popup.open()


if __name__ == '__main__':
    MobileApp().run()
