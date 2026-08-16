import io
import requests
from PIL import Image
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Color, Rectangle, PushMatrix, Rotate, PopMatrix, Line

Window.clearcolor = (0.0, 0.0, 0.0, 1) # Tam Siyah Arka Plan

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/stok-takip-f061b/databases/(default)/documents/stoklar"


class SplashEkrani(Screen):
    """Özel Tasarım Açılış ve Yükleme Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'splash'
        
        layout = FloatLayout()
        
        # 1. ORTA ALAN: Uygulama Logosu + Stok Takip Sistemi Yazısı
        center_box = BoxLayout(
            orientation='horizontal',
            size_hint=(0.85, None),
            height='90dp',
            pos_hint={'center_x': 0.5, 'center_y': 0.52},
            spacing=15
        )
        
        app_logo = KivyImage(
            source='app_icon.png',
            size_hint=(None, 1),
            width='90dp',
            allow_stretch=True,
            keep_ratio=True
        )
        
        title_lbl = Label(
            text="Stok Takip\nSistemi",
            font_size='26sp',
            bold=True,
            halign='left',
            valign='middle',
            color=(1, 1, 1, 1)
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))
        
        center_box.add_widget(app_logo)
        center_box.add_widget(title_lbl)
        layout.add_widget(center_box)
        
        # 2. ALT ALAN: Delikurt Stüdyo Logo ve İmza
        bottom_box = BoxLayout(
            orientation='vertical',
            size_hint=(0.8, None),
            height='100dp',
            pos_hint={'center_x': 0.5, 'y': 0.04},
            spacing=5
        )
        
        delikurt_logo = KivyImage(
            source='delikurt_studyo.png',
            size_hint=(1, None),
            height='55dp',
            allow_stretch=True,
            keep_ratio=True
        )
        
        delikurt_imza = KivyImage(
            source='delikurt_imza.png',
            size_hint=(1, None),
            height='35dp',
            allow_stretch=True,
            keep_ratio=True
        )
        
        bottom_box.add_widget(delikurt_logo)
        bottom_box.add_widget(delikurt_imza)
        layout.add_widget(bottom_box)
        
        self.add_widget(layout)

    def on_enter(self):
        Clock.schedule_once(self.ana_ekrana_gec, 2.5)

    def ana_ekrana_gec(self, dt):
        self.manager.current = 'stok_liste'


class LongPressLabel(Label):
    """Hızlı ve Kararlı Uzun Basma Etiketi"""
    def __init__(self, **kwargs):
        self.on_long_press = kwargs.pop('on_long_press', None)
        self.target_data = kwargs.pop('target_data', None)
        super().__init__(**kwargs)
        self._clock = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._clock = Clock.schedule_once(lambda dt: self._trigger_long_press(), 0.3)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._clock:
            Clock.unschedule(self._clock)
            self._clock = None
        return super().on_touch_up(touch)

    def _trigger_long_press(self):
        if self.on_long_press and self.target_data:
            self.on_long_press(self.target_data)


class RotatedCamera(Camera):
    """Açı Düzeltmeli Kamera"""
    def __init__(self, angle=-90, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=angle, axis=(0, 0, 1))
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update_rot, size=self._update_rot)

    def _update_rot(self, *args):
        self.rot.origin = self.center


class CameraScanWidget(FloatLayout):
    """Kamera ve Yeşil Çerçeve Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        try:
            self.cam = RotatedCamera(
                angle=-90, 
                play=True, 
                resolution=(640, 480), 
                size_hint=(0.95, 0.95), 
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(self.cam)
        except Exception:
            self.cam = None
            self.add_widget(Label(text="Kamera başlatılamadı.", pos_hint={'center_x': 0.5, 'center_y': 0.5}))

        with self.canvas.after:
            Color(0.12, 0.85, 0.38, 1)
            self.line = Line(width=4)
            
        self.bind(pos=self.update_frame, size=self.update_frame)
        if self.cam:
            self.cam.bind(pos=self.update_frame, size=self.update_frame)

        lbl = Label(
            text="QR / Barkodu Yeşil Çerçeveye Hizalayın",
            size_hint=(1, None),
            height='35dp',
            pos_hint={'top': 0.99, 'center_x': 0.5},
            bold=True,
            color=(1, 1, 1, 0.95),
            font_size='16sp'
        )
        self.add_widget(lbl)

    def update_frame(self, *args):
        if not hasattr(self, 'cam') or not self.cam:
            return
        cx, cy = self.center
        cam_min_side = min(self.cam.width, self.cam.height)
        w = max(180, cam_min_side * 0.65)
        self.line.rectangle = (cx - w/2, cy - w/2, w, w)


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
        
        title = Label(
            text="STOK TAKİP SİSTEMİ", 
            font_size='22sp', 
            bold=True, 
            color=(0.3, 0.65, 0.95, 1),
            size_hint_y=None, 
            height='40dp'
        )
        main_layout.add_widget(title)
        
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
        
        scroll = ScrollView()
        self.grid_stok = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.grid_stok.bind(minimum_height=self.grid_stok.setter('height'))
        
        scroll.add_widget(self.grid_stok)
        main_layout.add_widget(scroll)
        
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
            
            lbl_info = LongPressLabel(
                text=info_text,
                halign='left',
                valign='middle',
                font_size='13sp',
                size_hint_x=0.75,
                color=(0.9, 0.9, 0.9, 1),
                target_data=bilgi,
                on_long_press=self.parca_duzenle_git
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
            
            # Artık doğrudan değiştirmiyor, Miktar Girmeli Pop-up açıyor
            btn_inc.bind(on_release=lambda x, d=doc_id, u=bilgi: self.stok_miktar_popup_ac(d, u))
            btn_dec.bind(on_release=lambda x, d=doc_id, u=bilgi: self.stok_miktar_popup_ac(d, u))
            
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

    def stok_miktar_popup_ac(self, doc_id, urun_data):
        """Toplu miktar artırma/azaltma pop-up ekranı"""
        ad = urun_data.get('parca_adi') or urun_data.get('ad') or '-'
        mevcut_stok = urun_data.get('stok') if urun_data.get('stok') is not None else urun_data.get('miktar', 0)

        content = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        lbl_info = Label(
            text=f"Parça: {ad}\nMevcut Stok: {mevcut_stok} Adet",
            font_size='15sp',
            bold=True,
            halign='center'
        )
        content.add_widget(lbl_info)

        lbl_hint = Label(text="İşlem Miktarını Girin:", font_size='14sp')
        content.add_widget(lbl_hint)

        txt_miktar = TextInput(
            text='1',
            multiline=False,
            input_filter='int',
            font_size='20sp',
            halign='center',
            size_hint_y=None,
            height='45dp'
        )
        content.add_widget(txt_miktar)

        btn_box = BoxLayout(spacing=10, size_hint_y=None, height='50dp')
        
        btn_artir = Button(
            text="➕ Stok Artır",
            background_normal='',
            background_color=(0.12, 0.68, 0.32, 1),
            bold=True
        )
        btn_azalt = Button(
            text="➖ Stok Azalt",
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1),
            bold=True
        )
        
        btn_box.add_widget(btn_artir)
        btn_box.add_widget(btn_azalt)
        content.add_widget(btn_box)

        btn_kapat = Button(
            text="İptal",
            size_hint_y=None,
            height='40dp',
            background_normal='',
            background_color=(0.5, 0.5, 0.5, 1)
        )
        content.add_widget(btn_kapat)

        popup = Popup(title="Stok Hareketi İşlemi", content=content, size_hint=(0.88, 0.45))

        def stok_islem_yap(degisim_yonu):
            try:
                m = int(txt_miktar.text.strip())
                if m <= 0:
                    return
            except ValueError:
                return

            fark = m if degisim_yonu == 'artir' else -m
            yeni_stok = max(0, mevcut_stok + fark)
            
            urun_data['stok'] = yeni_stok
            urun_data['miktar'] = yeni_stok

            if FirestoreManager.urun_kaydet_veya_guncelle(doc_id, urun_data):
                popup.dismiss()
                self.stok_verilerini_yukle()

        btn_artir.bind(on_release=lambda x: stok_islem_yap('artir'))
        btn_azalt.bind(on_release=lambda x: stok_islem_yap('azalt'))
        btn_kapat.bind(on_release=popup.dismiss)
        
        popup.open()

    def kamera_popup_ac(self, instance):
        content = BoxLayout(orientation='vertical', spacing=8, padding=5)
        
        cam_widget = CameraScanWidget()
        content.add_widget(cam_widget)

        btn_box = BoxLayout(spacing=10, size_hint_y=None, height='50dp')
        
        btn_tara = Button(
            text="📷 TARA / OKU", 
            background_normal='',
            background_color=(0.12, 0.68, 0.32, 1),
            bold=True,
            font_size='16sp'
        )
        btn_kapat = Button(
            text="Kapat", 
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1),
            bold=True,
            font_size='16sp'
        )
        
        btn_box.add_widget(btn_tara)
        btn_box.add_widget(btn_kapat)
        content.add_widget(btn_box)
        
        popup = Popup(title="QR / Barkod Kamera Tara", content=content, size_hint=(0.98, 0.95))
        
        def qr_tara_islem(btn):
            if cam_widget.cam and cam_widget.cam.texture:
                try:
                    btn_tara.text = "İşleniyor..."
                    
                    tex = cam_widget.cam.texture
                    size = tex.size
                    pixels = tex.pixels
                    
                    if not pixels:
                        btn_tara.text = "Kamera Hazır Değil"
                        return

                    img = Image.frombytes('RGBA', size, pixels)
                    img = img.convert('RGB')
                    img_rotated = img.rotate(-90, expand=True)
                    
                    buffer = io.BytesIO()
                    img_rotated.save(buffer, format="JPEG", quality=80)
                    buffer.seek(0)
                    
                    res = requests.post("https://api.qrserver.com/v1/read-qr-code/", files={'file': ('scan.jpg', buffer, 'image/jpeg')}, timeout=5)
                    
                    if res.status_code == 200:
                        res_json = res.json()
                        symbol = res_json[0].get('symbol', [{}])[0]
                        parsed_text = symbol.get('data')
                        
                        if parsed_text:
                            popup.dismiss()
                            q = parsed_text.strip().lower()
                            
                            # Taranan ürünü bulup doğrudan stok değiştirme pop-up'ını açar
                            eslesen_doc_id = None
                            eslesen_data = None
                            
                            for d_id, u_data in self.tum_stoklar_cache.items():
                                b_no = str(u_data.get('barkod') or u_data.get('barkod_no') or '').lower()
                                p_kod = str(u_data.get('parca_kodu') or u_data.get('kod') or '').lower()
                                if q == b_no or q == p_kod or q == d_id.lower():
                                    eslesen_doc_id = d_id
                                    eslesen_data = u_data
                                    break
                            
                            if eslesen_doc_id and eslesen_data:
                                self.stok_miktar_popup_ac(eslesen_doc_id, eslesen_data)
                            else:
                                self.txt_scan.text = parsed_text
                            return
                except Exception as e:
                    print(f"QR İşleme Hatası: {e}")
                    
            btn_tara.text = "Tekrar Dene (Okunmadı)"

        btn_tara.bind(on_release=qr_tara_islem)
        btn_kapat.bind(on_release=popup.dismiss)
        popup.open()

    def parca_duzenle_git(self, urun_data):
        if not urun_data:
            return
        parca_ekrani = self.manager.get_screen('parca_ekle')
        parca_ekrani.duzenle_modu_ac(urun_data)
        self.manager.current = 'parca_ekle'

    def parca_ekle_sayfasina_git(self, instance):
        parca_ekrani = self.manager.get_screen('parca_ekle')
        parca_ekrani.yeni_ekle_modu_ac()
        self.manager.current = 'parca_ekle'


class ParcaEkleEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'parca_ekle'
        
        main_layout = BoxLayout(orientation='vertical', padding=[15, 10, 15, 10], spacing=8)
        
        self.lbl_title = Label(
            text="YENİ YEDEK PARÇA EKLE", 
            font_size='20sp', 
            bold=True, 
            color=(0.3, 0.65, 0.95, 1),
            size_hint_y=None, 
            height='45dp'
        )
        main_layout.add_widget(self.lbl_title)
        
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

    def duzenle_modu_ac(self, urun_data):
        self.lbl_title.text = "PARÇA DÜZENLE"
        self.txt_ad.text = str(urun_data.get('parca_adi') or urun_data.get('ad') or '')
        self.txt_kod.text = str(urun_data.get('parca_kodu') or urun_data.get('kod') or urun_data.get('doc_id') or '')
        self.txt_barkod.text = str(urun_data.get('barkod') or urun_data.get('barkod_no') or '')
        self.txt_kategori.text = str(urun_data.get('kategori') or 'Genel')
        self.txt_raf.text = str(urun_data.get('raf_konumu') or urun_data.get('raf') or '')
        
        stok_val = urun_data.get('stok') if urun_data.get('stok') is not None else urun_data.get('miktar', 0)
        self.txt_stok.text = str(stok_val)
        
        kritik_val = urun_data.get('kritik_stok') if urun_data.get('kritik_stok') is not None else urun_data.get('kritik_seviye', 5)
        self.txt_kritik.text = str(kritik_val)

    def yeni_ekle_modu_ac(self):
        self.lbl_title.text = "YENİ YEDEK PARÇA EKLE"
        self.formu_temizle()

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
        self.sm = ScreenManager(transition=FadeTransition(duration=0.4))
        
        self.splash_ekrani = SplashEkrani()
        self.stok_ekrani = AnaStokEkrani()
        self.parca_ekrani = ParcaEkleEkrani()
        
        self.sm.add_widget(self.splash_ekrani)
        self.sm.add_widget(self.stok_ekrani)
        self.sm.add_widget(self.parca_ekrani)
        return self.sm


if __name__ == '__main__':
    MobileApp().run()
