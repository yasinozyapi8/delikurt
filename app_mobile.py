import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup

# Uygulama Genel Koyu Arka Plan Rengi
Window.clearcolor = (0.1, 0.12, 0.15, 1)

# Örnek Stok Veritabanı
stok_veritabani = {
    "8690000000001": {
        "ad": "Rulman 6204", 
        "kod": "PRC-001", 
        "kategori": "Rulman", 
        "raf": "A-12", 
        "stok": 15, 
        "kritik": 5
    },
    "8690000000002": {
        "ad": "Yağ Filtresi H-12", 
        "kod": "PRC-002", 
        "kategori": "Filtre", 
        "raf": "B-05", 
        "stok": 8, 
        "kritik": 3
    }
}


class AnaStokEkrani(Screen):
    """Ana Stok Listesi Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stok_liste'
        
        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)
        
        # Üst Arama / Barkod Alanı
        scan_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='48dp')
        
        self.txt_scan = TextInput(
            hint_text='Barkod No Girin / Okutun...',
            multiline=False,
            font_size='16sp',
            size_hint_x=0.72,
            background_color=(0.9, 0.9, 0.9, 1)
        )
        btn_scan = Button(
            text='İşle',
            size_hint_x=0.28,
            background_normal='',
            background_color=(0.2, 0.55, 0.85, 1),
            bold=True,
            font_size='16sp'
        )
        btn_scan.bind(on_release=self.barkod_isle)
        
        scan_box.add_widget(self.txt_scan)
        scan_box.add_widget(btn_scan)
        main_layout.add_widget(scan_box)
        
        # Stok Liste Başlığı
        main_layout.add_widget(Label(
            text="MEVCUT STOK LİSTESİ", 
            size_hint_y=None, 
            height='30dp', 
            bold=True,
            color=(0.3, 0.7, 1, 1),
            font_size='16sp'
        ))
        
        # Stok Listesi ScrollView
        scroll = ScrollView()
        self.grid_stok = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.grid_stok.bind(minimum_height=self.grid_stok.setter('height'))
        
        scroll.add_widget(self.grid_stok)
        main_layout.add_widget(scroll)
        
        # Manuel Ekleme Butonu
        btn_go_add = Button(
            text='Manuel Yedek Parça Ekle',
            size_hint_y=None,
            height='50dp',
            background_normal='',
            background_color=(0.2, 0.25, 0.3, 1),
            bold=True,
            font_size='16sp'
        )
        btn_go_add.bind(on_release=self.parca_ekle_sayfasina_git)
        main_layout.add_widget(btn_go_add)
        
        self.add_widget(main_layout)

    def on_enter(self):
        self.stok_listesini_yenile()

    def stok_listesini_yenile(self):
        self.grid_stok.clear_widgets()
        for barkod, bilgi in stok_veritabani.items():
            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='45dp', padding=5)
            lbl = Label(
                text=f"[{barkod}] {bilgi['ad']} | Kat: {bilgi.get('kategori', 'Genel')} | Raf: {bilgi.get('raf', '-')} | Stok: {bilgi['stok']}",
                halign='left',
                valign='middle',
                font_size='14sp'
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
    """Orijinal Koyu Tasarımlı & Üste Hizalı Parça Ekleme Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'parca_ekle'
        
        main_layout = BoxLayout(orientation='vertical', padding=[15, 10, 15, 10], spacing=8)
        
        # Sayfa Başlığı (Görseldeki Mavi Renk)
        title = Label(
            text="YENİ YEDEK PARÇA EKLE", 
            font_size='20sp', 
            bold=True, 
            color=(0.3, 0.65, 0.95, 1),
            size_hint_y=None, 
            height='45dp'
        )
        main_layout.add_widget(title)
        
        # Form İçin Kaydırılabilir Alan
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        form_layout = BoxLayout(orientation='vertical', spacing=6, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))
        
        # Görseldeki Etiket ve Metin Kutusu Yapısı
        def create_field(label_text, hint_text, is_num=False):
            lbl = Label(
                text=label_text, 
                font_size='14sp', 
                bold=True, 
                halign='center', 
                size_hint_y=None, 
                height='22dp',
                color=(1, 1, 1, 1)
            )
            lbl.bind(size=lbl.setter('text_size'))
            
            inp = TextInput(
                hint_text=hint_text,
                multiline=False,
                font_size='15sp',
                size_hint_y=None,
                height='42dp',
                padding=[10, 10, 10, 10],
                background_color=(0.92, 0.92, 0.92, 1),
                foreground_color=(0, 0, 0, 1)
            )
            if is_num:
                inp.input_filter = 'int'
                
            form_layout.add_widget(lbl)
            form_layout.add_widget(inp)
            return inp

        # Orijinal Sıralama + Yeni Kategori Alanı
        self.txt_ad = create_field("Parça Adı:", "Örn: Rulman 6204")
        self.txt_kod = create_field("Parça Kodu:", "Örn: PRC-001")
        self.txt_barkod = create_field("Barkod / QR:", "Örn: 86900012345")
        self.txt_kategori = create_field("Kategori:", "Örn: Rulman / Filtre")
        self.txt_raf = create_field("Raf Numarası:", "Örn: A-12")
        self.txt_stok = create_field("Mevcut Stok Adedi:", "Örn: 10", is_num=True)
        self.txt_kritik = create_field("Kritik Stok Uyarısı Sınırı:", "Örn: 5", is_num=True)
        
        scroll.add_widget(form_layout)
        main_layout.add_widget(scroll)
        
        # Alt Butonlar (Yeşil Kaydet / Kırmızı İptal)
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height='60dp')
        
        btn_kaydet = Button(
            text="Kaydet", 
            background_normal='',
            background_color=(0.12, 0.68, 0.32, 1), 
            font_size='18sp',
            bold=True
        )
        btn_kaydet.bind(on_release=self.parca_kaydet)
        
        btn_iptal = Button(
            text="İptal", 
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1), 
            font_size='18sp',
            bold=True
        )
        btn_iptal.bind(on_release=self.iptal_et)
        
        btn_box.add_widget(btn_kaydet)
        btn_box.add_widget(btn_iptal)
        main_layout.add_widget(btn_box)
        
        self.add_widget(main_layout)

    def parca_kaydet(self, instance):
        barkod = self.txt_barkod.text.strip()
        ad = self.txt_ad.text.strip()
        kod = self.txt_kod.text.strip()
        kategori = self.txt_kategori.text.strip() or "Genel"
        raf = self.txt_raf.text.strip()
        stok = int(self.txt_stok.text) if self.txt_stok.text else 1
        kritik = int(self.txt_kritik.text) if self.txt_kritik.text else 5
        
        if barkod and ad:
            stok_veritabani[barkod] = {
                "ad": ad,
                "kod": kod,
                "kategori": kategori,
                "raf": raf,
                "stok": stok,
                "kritik": kritik
            }
            self.formu_temizle()
            self.manager.current = 'stok_liste'

    def iptal_et(self, instance):
        self.formu_temizle()
        self.manager.current = 'stok_liste'

    def formu_temizle(self):
        self.txt_barkod.text = ''
        self.txt_ad.text = ''
        self.txt_kod.text = ''
        self.txt_kategori.text = ''
        self.txt_raf.text = ''
        self.txt_stok.text = ''
        self.txt_kritik.text = ''


class MobileApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.stok_ekrani = AnaStokEkrani()
        self.parca_ekrani = ParcaEkleEkrani()
        
        self.sm.add_widget(self.stok_ekrani)
        self.sm.add_widget(self.parca_ekrani)
        return self.sm

    def process_barcode_scan(self, barcode_data):
        barcode = str(barcode_data).strip()
        
        if barcode in stok_veritabani:
            self.show_stock_update_popup(barcode)
        else:
            self.parca_ekrani.txt_barkod.text = barcode
            self.sm.current = 'parca_ekle'

    def show_stock_update_popup(self, barcode):
        urun = stok_veritabani[barcode]
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        layout.add_widget(Label(text=f"Ürün: {urun['ad']}\nMevcut Stok: {urun['stok']}", font_size='16sp'))
        
        qty_input = TextInput(text="1", input_filter="int", multiline=False, font_size='20sp', halign='center')
        layout.add_widget(qty_input)
        
        btn_layout = BoxLayout(spacing=10, size_hint_y=0.6)
        btn_add = Button(text="Stok Ekle (+)", background_normal='', background_color=(0.12, 0.68, 0.32, 1), font_size='16sp', bold=True)
        btn_sub = Button(text="Stok Çıkar (-)", background_normal='', background_color=(0.85, 0.22, 0.2, 1), font_size='16sp', bold=True)
        
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
