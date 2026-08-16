import os
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

# --- BİLDİRİM KÜTÜPHANESİ ENTEGRASYONU ---
try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

Window.clearcolor = (0.0, 0.0, 0.0, 1)

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/stok-takip-f061b/databases/(default)/documents/stoklar"


def get_asset_path(filename):
    """Android ve PC ortamında görsel yolunu garantiye alan yardımcı fonksiyon"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)


class SplashEkrani(Screen):
    """Özel Tasarım Açılış ve Yükleme Ekranı"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'splash'
        
        layout = FloatLayout()
        
        center_box = BoxLayout(
            orientation='horizontal',
            size_hint=(0.85, None),
            height='90dp',
            pos_hint={'center_x': 0.5, 'center_y': 0.52},
            spacing=15
        )
        
        app_logo = KivyImage(
            source=get_asset_path('app_icon.png'),
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
        
        bottom_box = BoxLayout(
            orientation='vertical',
            size_hint=(0.8, None),
            height='100dp',
            pos_hint={'center_x': 0.5, 'y': 0.04},
            spacing=5
        )
        
        delikurt_logo = KivyImage(
            source=get_asset_path('delikurt_studyo.png'),
            size_hint=(1, None),
            height='55dp',
            allow_stretch=True,
            keep_ratio=True
        )
        
        delikurt_imza = KivyImage(
            source=get_asset_path('delikurt_imza.png'),
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

    @classmethod
    def urun_sil(cls, doc_id):
        try:
            url = f"{FIRESTORE_URL}/{doc_id}"
            res = requests.delete(url, timeout=5)
            return res.status_code == 200
        except Exception as e:
            print(f"Firestore Silme Hatası: {e}")
            return False


class AnaStokEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stok_liste'
        self.tum_stoklar_cache = {}
        self.eski_stoklar = {}  # Bildirimleri kıyaslamak için stok hafızası
        self.sync_event = None
        
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

    def bildirim_gonder(self, baslik, mesaj):
        """Android üst bildirim çubuğuna mesaj fırlatır"""
        if HAS_PLYER:
            try:
                notification.notify(
                    title=baslik,
                    message=mesaj,
                    app_name="Stok Takip",
                    timeout=4
                )
            except Exception as e:
                print(f"Android Bildirim Hatası: {e}")

    def stok_bildirim_kontrol_et(self, yeni_stok_dict):
        """Firestore'dan gelen verileri eski verilerle kıyaslayıp bildirim atar"""
        for doc_id, item in yeni_stok_dict.items():
            kod = str(item.get("parca_kodu") or item.get("kod") or doc_id or "")
            ad = str(item.get("parca_adi") or item.get("ad") or "Bilinmeyen Parça")

            stok_val = item.get("stok") if item.get("stok") is not None else item.get("miktar", 0)
            yeni_m = int(stok_val)

            kritik_val = item.get("kritik_stok") if item.get("kritik_stok") is not None else item.get("kritik_seviye", 5)
            kritik_m = int(kritik_val)

            if not kod:
                continue

            # İlk yüklemede hafızaya al
            if kod not in self.eski_stoklar:
                self.eski_stoklar[kod] = yeni_m
                continue

            eski_m = self.eski_stoklar[kod]

            # 1. Stok Artışı
            if yeni_m > eski_m:
                fark = yeni_m - eski_m
                self.bildirim_gonder(
                    "📦 Stok Artışı",
                    f"{ad}\n+{fark} adet eklendi. Yeni Stok: {yeni_m} Adet"
                )

            # 2. Stok Azalışı ve Kritik Seviye
            elif yeni_m < eski_m:
                fark = eski_m - yeni_m
                if yeni_m <= kritik_m:
                    self.bildirim_gonder(
                        "⚠️ KRİTİK STOK UYARISI!",
                        f"{ad}\n-{fark} adet düştü! Stok kritik seviyede: {yeni_m} Adet kaldı."
                    )
                else:
                    self.bildirim_gonder(
                        "📉 Stok Azaldı",
                        f"{ad}\n-{fark} adet düştü. Kalan Stok: {yeni_m} Adet"
                    )

            self.eski_stoklar[kod] = yeni_m

    def on_enter(self):
        self.stok_verilerini_yukle()
        if not self.sync_event:
            self.sync_event = Clock.schedule_interval(self.otomatik_canli_senkronize, 2.5)

    def on_leave(self):
        if self.sync_event:
            Clock.unschedule(self.sync_event)
            self.sync_event = None

    def otomatik_canli_senkronize(self, dt):
        import threading
        def arkaplan_fetch():
            yeni_veri = FirestoreManager.tum_stoklari_getir()
            if yeni_veri:
                self.tum_stoklar_cache = yeni_veri
                Clock.schedule_once(lambda x: self.filtrele_ve_goster(self.txt_scan.text.strip()), 0)
                Clock.schedule_once(lambda x: self.stok_bildirim_kontrol_et(yeni_veri), 0)

        threading.Thread(target=arkaplan_fetch, daemon=True).start()

    def stok_verilerini_yukle(self):
        import threading
        def arkaplan_yukle():
            yeni_veri = FirestoreManager.tum_stoklari_getir()
            if yeni_veri:
                self.tum_stoklar_cache = yeni_veri
                Clock.schedule_once(lambda x: self.filtrele_ve_goster(self.txt_scan.text.strip()), 0)
                Clock.schedule_once(lambda x: self.stok_bildirim_kontrol_et(yeni_veri), 0)

        threading.Thread(target=arkaplan_yukle, daemon=True).start()

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
        self.current_doc_id = None
        
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
        
        self.btn_box = BoxLayout(spacing=10, size_hint_y=None, height='60dp')
        
        self.btn_kaydet = Button(
            text="Kaydet", 
            background_normal='',
            background_color=(0.12, 0.68, 0.32, 1), 
            font_size='16sp',
            bold=True
        )
        self.btn_kaydet.bind(on_release=self.parca_kaydet)
        
        self.btn_sil = Button(
            text="🗑️ Parçayı Sil", 
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1), 
            font_size='16sp',
            bold=True
        )
        self.btn_sil.bind(on_release=self.parca_sil_onay_popup)
        
        self.btn_iptal = Button(
            text="İptal", 
            background_normal='',
            background_color=(0.5, 0.5, 0.5, 1), 
            font_size='16sp',
            bold=True
        )
        self.btn_iptal.bind(on_release=self.iptal_et)
        
        self.btn_box.add_widget(self.btn_kaydet)
        self.btn_box.add_widget(self.btn_iptal)
        main_layout.add_widget(self.btn_box)
        
        self.add_widget(main_layout)

    def duzenle_modu_ac(self, urun_data):
        self.lbl_title.text = "PARÇA DÜZENLE"
        self.txt_ad.text = str(urun_data.get('parca_adi') or urun_data.get('ad') or '')
        
        doc_id = str(urun_data.get('parca_kodu') or urun_data.get('kod') or urun_data.get('doc_id') or '')
        self.txt_kod.text = doc_id
        self.current_doc_id = doc_id
        
        self.txt_barkod.text = str(urun_data.get('barkod') or urun_data.get('barkod_no') or '')
        self.txt_kategori.text = str(urun_data.get('kategori') or 'Genel')
        self.txt_raf.text = str(urun_data.get('raf_konumu') or urun_data.get('raf') or '')
        
        stok_val = urun_data.get('stok') if urun_data.get('stok') is not None else urun_data.get('miktar', 0)
        self.txt_stok.text = str(stok_val)
        
        kritik_val = urun_data.get('kritik_stok') if urun_data.get('kritik_stok') is not None else urun_data.get('kritik_seviye', 5)
        self.txt_kritik.text = str(kritik_val)

        self.btn_box.clear_widgets()
        self.btn_box.add_widget(self.btn_kaydet)
        self.btn_box.add_widget(self.btn_sil)
        self.btn_box.add_widget(self.btn_iptal)

    def yeni_ekle_modu_ac(self):
        self.lbl_title.text = "YENİ YEDEK PARÇA EKLE"
        self.current_doc_id = None
        self.formu_temizle()
        
        self.btn_box.clear_widgets()
        self.btn_box.add_widget(self.btn_kaydet)
        self.btn_box.add_widget(self.btn_iptal)

    def parca_sil_onay_popup(self, instance):
        if not self.current_doc_id:
            return

        content = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        lbl = Label(
            text=f"'{self.txt_ad.text}' parçası silinecek.\nBu işlem geri alınamaz!",
            font_size='15sp',
            halign='center',
            bold=True
        )
        content.add_widget(lbl)

        btn_box = BoxLayout(spacing=10, size_hint_y=None, height='45dp')
        
        btn_evet = Button(
            text="Evet, Sil",
            background_normal='',
            background_color=(0.85, 0.22, 0.2, 1),
            bold=True
        )
        btn_hayir = Button(
            text="Vazgeç",
            background_normal='',
            background_color=(0.5, 0.5, 0.5, 1),
            bold=True
        )

        btn_box.add_widget(btn_evet)
        btn_box.add_widget(btn_hayir)
        content.add_widget(btn_box)

        popup = Popup(title="Parça Silme Onayı", content=content, size_hint=(0.88, 0.35))

        def sil_islem(btn):
            if FirestoreManager.urun_sil(self.current_doc_id):
                popup.dismiss()
                self.formu_temizle()
                self.manager.current = 'stok_liste'

        btn_evet.bind(on_release=sil_islem)
        btn_hayir.bind(on_release=popup.dismiss)
        popup.open()

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
