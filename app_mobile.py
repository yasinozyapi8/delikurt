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
from kivy.uix.camera import Camera
from kivy.graphics import Color, Rectangle, PushMatrix, Rotate, PopMatrix

Window.clearcolor = (0.1, 0.12, 0.15, 1)

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/stok-takip-f061b/databases/(default)/documents/stoklar"


class RotatedCamera(Camera):
    """Android Dikey Ekran İçin Açı Düzeltmeli Kamera Bileşeni"""
    def __init__(self, angle=-90, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=angle, axis=(0, 0, 1))
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update_rot, size=self._update_rot)

    def _update_rot(self, *args):
        self.rot.origin = self.center


class FirestoreManager:
    @staticmethod
    def _parse_firestore_doc(doc):
        fields = doc.get("fields", {})
        data = {}
        for key, val in fields.items():
            if "stringValue" in val:
                data[key] = val["stringValue"]
            elif "integerValue" in val:
                data[key] = int(val["integerValue"])
            elif "doubleValue" in val:
                data[key] = float(val["doubleValue"])
        
        doc_id = doc.get("name", "").split("/")[-1]
        data["doc_id"] = doc_id
        return doc_id, data

    @staticmethod
    def _build_firestore_fields(data):
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
        try:
            res = requests.get(FIRESTORE_URL, timeout=5)
            if res.status_code == 200:
                docs = res.json().get("documents", [])
                stok_dict = {}
                for doc in docs:
                    doc_id, data = cls._parse_firestore_doc(doc)
                    stok_dict[doc_id] = data
                return stok_dict
            return {}
        except Exception as e:
            print(f"Firestore Bağlantı Hatası: {e}")
            return {}

    @classmethod
    def urun_kaydet_veya_guncelle(cls, doc_id, urun_data):
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
        self.tum_stoklar_cache = {}
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Üst Başlık
        title = Label(
            text="STOK TAKİP SİSTEMİ", 
            font_size='22sp', 
            bold=True, 
            color=(0.3, 0.65, 0.95, 1),
            size_hint_y=None, 
            height='40dp'
        )
        main_layout.add_widget(title)
        
        # Arama + Kamera Üst Barı
        scan_box = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height='50dp')
        
        self.txt_scan = TextInput(
            hint_text='Barkod veya Parça Ara...',
            multiline=False,
            font_size='16sp',
            size_hint_x=0.6,
            background_color=(0.05, 0.05, 0.05, 1),
            foreground_color=(1, 1, 1, 1),
            padding=[10, 12, 10, 10]
        )
        self.txt_scan.bind(text=self.anlik_arama_yap)
        
        btn_ara = Button(
            text='Ara',
            size_hint_x=0.2,
            background_normal='',
            background_color=(0.2, 0.55, 0.85, 1),
            bold=True,
            font_size='16sp'
        )
        btn_ara.bind(on_release=lambda x: self.filtrele_ve_goster(self.txt_scan.text.strip()))
        
        btn_kamera = Button(
            text='📷 Kamera',
            size_hint_x=0.2,
            background_normal='',
            background_color=(0.85, 0.45, 0.1, 1),
            bold=True,
            font_size='14sp'
        )
        btn_kamera.bind(on_release=self.kamera_popup_ac)
        
        scan_box.add_widget(self.txt_scan)
        scan_box.add_widget(btn_ara)
        scan_box.add_widget(btn_kamera)
        main_layout.add_widget(scan_box)
        
        # Stok Kartları ScrollView
        scroll = ScrollView()
        self.grid_stok = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.grid_stok.bind(minimum_height=self.grid_stok.setter('height'))
        
        scroll.add_widget(self.grid_stok)
        main_layout.add_widget(scroll)
        
        # Alt Yeşil Buton
        btn_go_add = Button(
            text='+ Yeni Yedek Parça Ekle',
            size_hint_y=None,
            height='55dp',
            background_normal='',
            background_color=(0.12, 0.68, 0.32, 1),
            bold=True,
            font_size='18sp'
        )
        btn_go_add.bind(on_release=self.parca_ekle_sayfasina_git)
        main_layout.add_widget(btn_go_add)
        
        self.add_widget(main_layout)

    def on_enter(self):
        self.stok_verilerini_yukle()

    def stok_verilerini_yukle(self):
        self.tum_stoklar_cache = FirestoreManager.tum_stoklari_getir()
        self.filtrele_ve_goster(self.txt_scan.text.strip())

    def anlik_arama_yap(self, instance, value):
        self.filtrele_ve_goster(value.strip())

    def filtrele_ve_goster(self, arama_metni=""):
        self.grid_stok.clear_widgets()
        
        if not self.tum_stoklar_cache:
            self.grid_stok.add_widget(Label(text="Kayıtlı ürün bulunamadı.", size_hint_y=None, height='40dp'))
            return

        bulunan_sayisi = 0
        q = arama_metni.lower()

        for doc_id, bilgi in self.tum_stoklar_cache.items():
            ad = bilgi.get('parca_adi') or bilgi.get('ad') or '-'
            kod = bilgi.get('parca_kodu') or bilgi.get('kod') or doc_id
            barkod = bilgi.get('barkod') or bilgi.get('barkod_no') or doc_id
            raf = bilgi.get('raf_konumu') or bilgi.get('raf') or '-'
            stok = bilgi.get('stok') if bilgi.get('stok') is not None else bilgi.get('miktar', 0)
            
            if q:
                if (q not in ad.lower() and 
                    q not in kod.lower() and 
                    q not in barkod.lower() and 
                    q not in raf.lower()):
                    continue

            bulunan_sayisi += 1

            card = BoxLayout(orientation='horizontal', size_hint_y=None, height='80dp', padding=8, spacing=5)
            
            with card.canvas.before:
                Color(0.18, 0.22, 0.28, 1)
                Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda instance, value: self._update_rect(instance), size=lambda instance, value: self._update_rect(instance))

            info_text = f"Adı: {ad}\nKod: {kod} | Barkod: {barkod}\nRaf: {raf} | Stok: {stok} Adet"
            lbl_info = Label(
                text=info_text,
                halign='left',
                valign='middle',
                font_size='13sp',
                size_hint_x=0.75,
                color=(0.9, 0.9, 0.9, 1)
            )
            lbl_info.bind(size=lbl_info.setter('text_size'))
            card.add_widget(lbl_info)

            btn_box = BoxLayout(orientation='vertical', size_hint_x=0.25, spacing=3)
            
            btn_inc = Button(
                text='+', 
                background_normal='', 
                background_color=(0.12, 0.68, 0.32, 1), 
                bold=True, 
                font_size='18sp'
            )
            btn_dec = Button(
                text='-', 
                background_normal='', 
                background_color=(0.85, 0.22, 0.2, 1), 
                bold=True, 
                font_size='18sp'
            )
            
            btn_inc.bind(on_release=lambda x, d=doc_id, u=bilgi: self.stok_degistir(d, u, 1))
            btn_dec.bind(on_release=lambda x, d=doc_id, u=bilgi: self.stok_degistir(d, u, -1))
            
            btn_box.add_widget(btn_inc)
            btn_box.add_widget(btn_dec)
            card.add_widget(btn_box)

            self.grid_stok.add_widget(card)

        if bulunan_sayisi == 0 and q:
            self.grid_stok.add_widget(Label(text=f"'{arama_metni}' bulunamadı.", size_hint_y=None, height='40dp'))

    def _update_rect(self, instance):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.18, 0.22, 0.28, 1)
            Rectangle(pos=instance.pos, size=instance.size)

    def stok_degistir(self, doc_id, urun_data, miktar_degisimi):
        mevcut_stok = urun_data.get('stok') if urun_data.get('stok') is not None else urun_data.get('miktar', 0)
        yeni_stok = max(0, mevcut_stok + miktar_degisimi)
        
        urun_data['stok'] = yeni_stok
        urun_data['miktar'] = yeni_stok
        
        if FirestoreManager.urun_kaydet_veya_guncelle(doc_id, urun_data):
            self.stok_verilerini_yukle()

    def kamera_popup_ac(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        try:
            # Sola yatık görüntüyü düzeltmek için RotatedCamera (-90 derece) kullanılır
            cam = RotatedCamera(angle=-90, play=True, resolution=(640, 480))
            content.add_widget(cam)
        except Exception as e:
            content.add_widget(Label(text="Kamera başlatılamadı veya izin verilmedi."))

        btn_kapat = Button(
            text="Kapat", 
            size_hint_y=None, 
            height='45dp', 
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1),
            bold=True
        )
        content.add_widget(btn_kapat)
        
        popup = Popup(title="QR / Barkod Kamera Tara", content=content, size_hint=(0.9, 0.7))
        btn_kapat.bind(on_release=popup.dismiss)
        popup.open()

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


if __name__ == '__main__':
    MobileApp().run()
