import kivy
import requests
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

Window.clearcolor = (0.1, 0.12, 0.15, 1)

# Cloud Firestore REST API Bağlantısı (stok-takip-f061b projesi için)
FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/stok-takip-f061b/databases/(default)/documents/stoklar"


class FirestoreManager:
    """Firestore REST API Veri Dönüştürücü ve Yönetici"""

    @staticmethod
    def _parse_firestore_doc(doc):
        """Firestore JSON formatını standart Python sözlüğüne çevirir"""
        fields = doc.get("fields", {})
        data = {}
        for key, val in fields.items():
            if "stringValue" in val:
                data[key] = val["stringValue"]
            elif "integerValue" in val:
                data[key] = int(val["integerValue"])
            elif "doubleValue" in val:
                data[key] = float(val["doubleValue"])
        
        # Doküman ID'sini al (Örn: BV-1430)
        doc_id = doc.get("name", "").split("/")[-1]
        data["doc_id"] = doc_id
        return doc_id, data

    @staticmethod
    def _build_firestore_fields(data):
        """Python sözlüğünü Firestore JSON formatına dönüştürür"""
        fields = {}
        for key, val in data.items():
            if isinstance(val, int):
                fields[key] = {"integerValue": str(val)}
            elif isinstance(val, float):
                fields[key] = {"doubleValue": val}
            else:
                fields[key] = {"stringValue": str(val)}
        return {"fields": fields}

    @classmethod
    def tum_stoklari_getir(cls):
        """Firestore 'stoklar' koleksiyonundaki tüm belgeleri çeker"""
        try:
            res = requests.get(FIRESTORE_URL, timeout=5)
            if res.status_code == 200:
                docs = res.json().get("documents", [])
                stok_dict = {}
                for doc in docs:
                    doc_id, data = cls._parse_firestore_doc(doc)
                    # Barkod veya Parça Kodu anahtar olarak kullanılır
                    barkod_key = data.get("barkod") or data.get("parca_kodu") or doc_id
                    stok_dict[barkod_key] = data
                return stok_dict
            return {}
        except Exception as e:
            print(f"Firestore Bağlantı Hatası: {e}")
            return {}

    @classmethod
    def urun_kaydet_veya_guncelle(cls, doc_id, urun_data):
        """Ürünü Firestore üzerine kaydeder veya günceller (PATCH)"""
        try:
            url = f"{FIRESTORE_URL}/{doc_id}"
            payload = cls._build_firestore_fields(urun_data)
            res = requests.patch(url, json=payload, timeout=5)
            return res.status_code == 200
        except Exception as e:
            print(f"Firestore Kayıt Hatası: {e}")
            return False


class AnaStokEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stok_liste'
        
        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)
        
        # Arama / Barkod Alanı
        scan_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='48dp')
        self.txt_scan = TextInput(
            hint_text='Barkod / Parça Kodu Girin...',
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
        
        main_layout.add_widget(Label(
            text="FIRESTORE STOK LİSTESİ", 
            size_hint_y=None, 
            height='30dp', 
            bold=True,
            color=(0.3, 0.7, 1, 1),
            font_size='16sp'
        ))
        
        scroll = ScrollView()
        self.grid_stok = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.grid_stok.bind(minimum_height=self.grid_stok.setter('height'))
        
        scroll.add_widget(self.grid_stok)
        main_layout.add_widget(scroll)
        
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
        stoklar = FirestoreManager.tum_stoklari_getir()
        
        if not stoklar:
            self.grid_stok.add_widget(Label(text="Firestore'da kayıtlı ürün bulunamadı.", size_hint_y=None, height='40dp'))
            return

        for key, bilgi in stoklar.items():
            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='45dp', padding=5)
            
            # Firestore şemanıza uygun alan isimleri
            ad = bilgi.get('parca_adi') or bilgi.get('ad') or '-'
            kat = bilgi.get('kategori', 'Genel')
            raf = bilgi.get('raf_konumu') or bilgi.get('raf') or '-'
            stok = bilgi.get('stok') if bilgi.get('stok') is not None else bilgi.get('miktar', 0)
            
            lbl = Label(
                text=f"[{key}] {ad} | Kat: {kat} | Raf: {raf} | Stok: {stok}",
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'parca_ekle'
        
        main_layout = BoxLayout(orientation='vertical', padding=[15, 10, 15, 10], spacing=8)
        
        title = Label(
            text="YENİ YEDEK PARÇA EKLE", 
            font_size='20sp', 
            bold=True, 
            color=(0.3, 0.65, 0.95, 1),
            size_hint_y=None, 
            height='45dp'
        )
        main_layout.add_widget(title)
        
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        form_layout = BoxLayout(orientation='vertical', spacing=6, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))
        
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

        self.txt_ad = create_field("Parça Adı:", "Örn: Blok Vidası 1,4x3,0mm")
        self.txt_kod = create_field("Parça Kodu (Doküman ID):", "Örn: BV-1430")
        self.txt_barkod = create_field("Barkod / QR:", "Örn: 869000111")
        self.txt_kategori = create_field("Kategori:", "Örn: Vida")
        self.txt_raf = create_field("Raf Konumu:", "Örn: C-2b")
        self.txt_stok = create_field("Mevcut Stok Adedi:", "Örn: 5", is_num=True)
        self.txt_kritik = create_field("Kritik Stok Sınırı:", "Örn: 5", is_num=True)
        
        scroll.add_widget(form_layout)
        main_layout.add_widget(scroll)
        
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
        kod = self.txt_kod.text.strip()
        barkod = self.txt_barkod.text.strip()
        ad = self.txt_ad.text.strip()
        kategori = self.txt_kategori.text.strip() or "Genel"
        raf = self.txt_raf.text.strip()
        stok = int(self.txt_stok.text) if self.txt_stok.text else 1
        kritik = int(self.txt_kritik.text) if self.txt_kritik.text else 5
        
        doc_id = kod or barkod
        
        if doc_id and ad:
            urun_data = {
                "ad": ad,
                "parca_adi": ad,
                "parca_kodu": kod,
                "barkod": barkod,
                "barkod_no": kod,
                "kategori": kategori,
                "raf_konumu": raf,
                "raf": raf,
                "stok": stok,
                "miktar": stok,
                "kritik_stok": kritik,
                "kritik_seviye": kritik
            }
            if FirestoreManager.urun_kaydet_veya_guncelle(doc_id, urun_data):
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
        stoklar = FirestoreManager.tum_stoklari_getir()
        
        if barcode in stoklar:
            self.show_stock_update_popup(barcode, stoklar[barcode])
        else:
            self.parca_ekrani.txt_barkod.text = barcode
            self.parca_ekrani.txt_kod.text = barcode
            self.sm.current = 'parca_ekle'

    def show_stock_update_popup(self, doc_id, urun):
        ad = urun.get('parca_adi') or urun.get('ad') or '-'
        mevcut_stok = urun.get('stok') if urun.get('stok') is not None else urun.get('miktar', 0)
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        layout.add_widget(Label(text=f"Ürün: {ad}\nMevcut Stok: {mevcut_stok}", font_size='16sp'))
        
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
                yeni_stok = (mevcut_stok + miktar) if is_addition else max(0, mevcut_stok - miktar)
                
                urun['stok'] = yeni_stok
                urun['miktar'] = yeni_stok
                
                FirestoreManager.urun_kaydet_veya_guncelle(doc_id, urun)
                self.stok_ekrani.stok_listesini_yenile()
                popup.dismiss()
            except ValueError:
                pass

        btn_add.bind(on_release=lambda x: update_qty(True))
        btn_sub.bind(on_release=lambda x: update_qty(False))
        popup.open()


if __name__ == '__main__':
    MobileApp().run()
