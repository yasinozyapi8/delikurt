import os
import json
from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.graphics import PushMatrix, PopMatrix, Rotate

# --- Arka Plan Rengini Ayarla (Modern Koyu Antrasit) ---
Window.clearcolor = (0.12, 0.15, 0.18, 1)

# Global Veritabanı Değişkeni
VERITABANI = []


# --- Kalıcı Veri Yükleme ve Kaydetme Fonksiyonları ---
def dosya_yolunu_al():
    app = App.get_running_app()
    if app and hasattr(app, 'user_data_dir'):
        return os.path.join(app.user_data_dir, 'stok_verileri.json')
    return 'stok_verileri.json'


def verileri_yukle():
    global VERITABANI
    dosya = dosya_yolunu_al()
    if os.path.exists(dosya):
        try:
            with open(dosya, 'r', encoding='utf-8') as f:
                VERITABANI = json.load(f)
                return
        except Exception as e:
            print("Veri okuma hatası:", e)

    # Varsayılan Örnek Veriler
    VERITABANI = [
        {"parca_kodu": "BV-1430", "barkod": "869000111", "ad": "Blok Vidası 1,4x3,0mm", "raf": "A-12", "stok": 3, "kritik_stok": 5},
        {"parca_kodu": "PRC-002", "barkod": "869000222", "ad": "V-Kayışı A-42", "raf": "B-03", "stok": 8, "kritik_stok": 3},
    ]


def verileri_kaydet():
    dosya = dosya_yolunu_al()
    try:
        with open(dosya, 'w', encoding='utf-8') as f:
            json.dump(VERITABANI, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Veri kaydetme hatası:", e)


# --- Android İzin Kontrolü ---
def android_izinlerini_iste():
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print("İzin alma hatası:", e)


# --- Basılı Tutulan (Long Press) Buton ---
class BasiliTutulanItem(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._long_press_event = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_event = Clock.schedule_once(self._uzun_basildi, 0.8)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._long_press_event:
            self._long_press_event.cancel()
        return super().on_touch_up(touch)

    def _uzun_basildi(self, dt):
        if hasattr(self, 'on_long_press_callback') and self.on_long_press_callback:
            self.on_long_press_callback(self)


# --- Ana Liste Ekranı ---
class AnaEkran(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)
        
        # Üst Başlık
        main_layout.add_widget(Label(
            text="STOK TAKİP SİSTEMİ", 
            font_size='20sp', 
            size_hint_y=0.08, 
            bold=True,
            color=(0.3, 0.7, 1, 1)
        ))

        # Arama ve Kamera
        arama_box = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=6)
        
        self.txt_barkod_ara = TextInput(
            hint_text='Barkod, Parça Kodu veya Adı Ara...', 
            multiline=False,
            background_color=(0.9, 0.9, 0.9, 1)
        )
        btn_ara = Button(text='Ara', size_hint_x=0.22, background_color=(0.2, 0.5, 0.9, 1), background_normal='', bold=True)
        btn_ara.bind(on_release=self.barkod_ara)
        
        btn_kamera = Button(text='Kamera', size_hint_x=0.28, background_color=(0.8, 0.4, 0.1, 1), background_normal='', bold=True)
        btn_kamera.bind(on_release=self.kamera_ac)

        arama_box.add_widget(self.txt_barkod_ara)
        arama_box.add_widget(btn_ara)
        arama_box.add_widget(btn_kamera)
        main_layout.add_widget(arama_box)

        # Liste Alanı
        self.scroll = ScrollView(size_hint=(1, 0.73))
        self.liste_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.liste_layout.bind(minimum_height=self.liste_layout.setter('height'))
        self.scroll.add_widget(self.liste_layout)
        main_layout.add_widget(self.scroll)

        # Alt Ekleme Butonu
        alt_box = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        btn_yeni_ekle = Button(
            text='+ Yeni Yedek Parça Ekle', 
            font_size='17sp',
            bold=True,
            background_color=(0.1, 0.7, 0.3, 1),
            background_normal=''
        )
        btn_yeni_ekle.bind(on_release=lambda x: setattr(self.manager, 'current', 'ekle_ekrani'))
        alt_box.add_widget(btn_yeni_ekle)
        main_layout.add_widget(alt_box)

        self.add_widget(main_layout)

    def on_enter(self):
        self.listeyi_guncelle(self.txt_barkod_ara.text)

    def listeyi_guncelle(self, filtre=""):
        self.liste_layout.clear_widgets()
        
        for item in VERITABANI:
            if filtre:
                f = filtre.lower()
                if (f not in item['parca_kodu'].lower() and 
                    f not in item['barkod'].lower() and 
                    f not in item['ad'].lower()):
                    continue

            card = BoxLayout(orientation='horizontal', size_hint_y=None, height=120, spacing=6)

            stok_adedi = item.get('stok', 0)
            kritik_sınıri = item.get('kritik_stok', 0)
            is_kritik = stok_adedi <= kritik_sınıri

            bg_color = (0.55, 0.15, 0.15, 1) if is_kritik else (0.18, 0.22, 0.28, 1)
            uyari_metni = " [⚠️ KRİTİK STOK!]" if is_kritik else ""

            btn_text = (
                f" Parça Adı: {item['ad']}{uyari_metni}\n"
                f" Kod: {item['parca_kodu']} | Barkod: {item['barkod']}\n"
                f" Raf: {item['raf']} | Stok: {stok_adedi} Adet (Kritik: {kritik_sınıri})"
            )
            
            btn_details = BasiliTutulanItem(
                text=btn_text,
                size_hint_x=0.74,
                halign='left',
                valign='middle',
                background_color=bg_color,
                background_normal='',
                font_size='13sp'
            )
            btn_details.text_size = (btn_details.width, None)
            btn_details.bind(size=lambda s, w: setattr(s, 'text_size', (s.width - 15, None)))
            
            btn_details.item_data = item
            btn_details.on_long_press_callback = self.duzenleme_popup_ac
            
            # Hızlı Stok Arttırma / Eksiltme
            stok_box = BoxLayout(orientation='vertical', size_hint_x=0.26, spacing=4)
            btn_plus = Button(text='+', font_size='22sp', bold=True, background_color=(0.1, 0.7, 0.3, 1), background_normal='')
            btn_minus = Button(text='-', font_size='22sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), background_normal='')

            def make_arttir(d):
                def arttir(x):
                    d['stok'] += 1
                    verileri_kaydet()
                    self.listeyi_guncelle(self.txt_barkod_ara.text)
                return arttir

            def make_eksilt(d):
                def eksilt(x):
                    if d['stok'] > 0:
                        d['stok'] -= 1
                        verileri_kaydet()
                        self.listeyi_guncelle(self.txt_barkod_ara.text)
                return eksilt

            btn_plus.bind(on_release=make_arttir(item))
            btn_minus.bind(on_release=make_eksilt(item))

            stok_box.add_widget(btn_plus)
            stok_box.add_widget(btn_minus)

            card.add_widget(btn_details)
            card.add_widget(stok_box)
            self.liste_layout.add_widget(card)

    def barkod_ara(self, instance):
        self.listeyi_guncelle(self.txt_barkod_ara.text)

    def kamera_ac(self, instance):
        self.manager.current = 'kamera_ekrani'

    # Detaylı Düzenleme / Silme Menüsü
    def duzenleme_popup_ac(self, item_button):
        data = item_button.item_data

        content = BoxLayout(orientation='vertical', spacing=6, padding=10)
        
        txt_ad = TextInput(text=data['ad'], multiline=False)
        txt_parca_kodu = TextInput(text=data['parca_kodu'], multiline=False)
        txt_barkod = TextInput(text=data['barkod'], multiline=False)
        txt_raf = TextInput(text=data['raf'], multiline=False)
        txt_stok = TextInput(text=str(data.get('stok', 0)), multiline=False, input_filter='int')
        txt_kritik_stok = TextInput(text=str(data.get('kritik_stok', 5)), multiline=False, input_filter='int')

        content.add_widget(Label(text="Parça Adı:"))
        content.add_widget(txt_ad)
        content.add_widget(Label(text="Parça Kodu:"))
        content.add_widget(txt_parca_kodu)
        content.add_widget(Label(text="Barkod:"))
        content.add_widget(txt_barkod)
        content.add_widget(Label(text="Raf Kodu:"))
        content.add_widget(txt_raf)
        content.add_widget(Label(text="Kritik Stok Seviyesi:"))
        content.add_widget(txt_kritik_stok)
        
        content.add_widget(Label(text="Mevcut Stok Adedi:"))
        stok_box = BoxLayout(orientation='horizontal', spacing=5)
        btn_e = Button(text='-', size_hint_x=0.2, background_color=(0.7, 0.2, 0.2, 1), background_normal='')
        btn_a = Button(text='+', size_hint_x=0.2, background_color=(0.2, 0.6, 0.2, 1), background_normal='')
        
        def eksilt(x):
            val = int(txt_stok.text or 0)
            if val > 0: txt_stok.text = str(val - 1)
        def arttir(x):
            val = int(txt_stok.text or 0)
            txt_stok.text = str(val + 1)
            
        btn_e.bind(on_release=eksilt)
        btn_a.bind(on_release=arttir)
        
        stok_box.add_widget(btn_e)
        stok_box.add_widget(txt_stok)
        stok_box.add_widget(btn_a)
        content.add_widget(stok_box)

        buton_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        btn_kaydet = Button(text='Guncelle', background_color=(0.1, 0.5, 0.9, 1), background_normal='')
        btn_sil = Button(text='Sil', background_color=(0.8, 0.2, 0.2, 1), background_normal='')
        
        popup = Popup(title='Parça Düzenle / Sil', content=content, size_hint=(0.92, 0.95))

        def kaydet_action(x):
            data['ad'] = txt_ad.text
            data['parca_kodu'] = txt_parca_kodu.text
            data['barkod'] = txt_barkod.text
            data['raf'] = txt_raf.text
            data['stok'] = int(txt_stok.text or 0)
            data['kritik_stok'] = int(txt_kritik_stok.text or 0)
            verileri_kaydet()
            self.listeyi_guncelle(self.txt_barkod_ara.text)
            popup.dismiss()

        def sil_action(x):
            VERITABANI.remove(data)
            verileri_kaydet()
            self.listeyi_guncelle(self.txt_barkod_ara.text)
            popup.dismiss()

        btn_kaydet.bind(on_release=kaydet_action)
        btn_sil.bind(on_release=sil_action)

        buton_box.add_widget(btn_kaydet)
        buton_box.add_widget(btn_sil)
        content.add_widget(buton_box)

        popup.open()


# --- Parça Ekleme Ekranı (İdeal Boyutlandırılmış ve Dengeli Form) ---
class ParcaEkleEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical', padding=18, spacing=10)
        
        main_layout.add_widget(Label(
            text="YENİ YEDEK PARÇA EKLE", 
            font_size='20sp', 
            bold=True, 
            color=(0.3, 0.7, 1, 1),
            size_hint_y=None,
            height=35
        ))

        form_layout = BoxLayout(orientation='vertical', spacing=6, size_hint_y=0.78)

        form_layout.add_widget(Label(text="Parça Adı:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_ad = TextInput(hint_text='Örn: Rulman 6204', multiline=False, size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_ad)

        form_layout.add_widget(Label(text="Parça Kodu:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_parca_kodu = TextInput(hint_text='Örn: PRC-001', multiline=False, size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_parca_kodu)

        form_layout.add_widget(Label(text="Barkod:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_barkod = TextInput(hint_text='Örn: 86900012345', multiline=False, size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_barkod)

        form_layout.add_widget(Label(text="Raf Numarası:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_raf = TextInput(hint_text='Örn: A-12', multiline=False, size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_raf)

        form_layout.add_widget(Label(text="Mevcut Stok Adedi:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_stok = TextInput(hint_text='Örn: 10', multiline=False, input_filter='int', size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_stok)

        form_layout.add_widget(Label(text="Kritik Stok Uyarısı Sınırı:", font_size='14sp', size_hint_y=None, height=22, halign='left'))
        self.txt_kritik_stok = TextInput(hint_text='Örn: 5', multiline=False, input_filter='int', size_hint_y=None, height=48, font_size='15sp')
        form_layout.add_widget(self.txt_kritik_stok)

        main_layout.add_widget(form_layout)

        # Büyütülmüş Alt Kaydet / İptal Butonları
        btn_box = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=70)
        btn_kaydet = Button(text='Kaydet', background_color=(0.1, 0.7, 0.3, 1), background_normal='', bold=True, font_size='20sp')
        btn_iptal = Button(text='İptal', background_color=(0.8, 0.2, 0.2, 1), background_normal='', bold=True, font_size='20sp')

        btn_kaydet.bind(on_release=self.kaydet)
        btn_iptal.bind(on_release=lambda x: setattr(self.manager, 'current', 'ana_ekran'))

        btn_box.add_widget(btn_kaydet)
        btn_box.add_widget(btn_iptal)
        main_layout.add_widget(btn_box)

        self.add_widget(main_layout)

    def kaydet(self, instance):
        if self.txt_ad.text and (self.txt_parca_kodu.text or self.txt_barkod.text):
            yeni_parca = {
                "ad": self.txt_ad.text,
                "parca_kodu": self.txt_parca_kodu.text or "-",
                "barkod": self.txt_barkod.text or "-",
                "raf": self.txt_raf.text or "-",
                "stok": int(self.txt_stok.text or 0),
                "kritik_stok": int(self.txt_kritik_stok.text or 5)
            }
            VERITABANI.append(yeni_parca)
            verileri_kaydet()
            
            self.txt_ad.text = ""
            self.txt_parca_kodu.text = ""
            self.txt_barkod.text = ""
            self.txt_raf.text = ""
            self.txt_stok.text = ""
            self.txt_kritik_stok.text = ""
            
            self.manager.current = 'ana_ekran'


# --- Doğal Oranını Koruyan Dikey Kamera Ekranı ---
class KameraEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.layout.add_widget(Label(text="BARKOD TARA", font_size='18sp', size_hint_y=0.08, bold=True))

        # keep_ratio=True ile kameranın basılması/yayılması engellendi
        self.camera = Camera(
            play=False, 
            resolution=(640, 480), 
            allow_stretch=True, 
            keep_ratio=True, 
            size_hint=(1, 0.80)
        )
        
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self._rotation_merkezini_guncelle, size=self._rotation_merkezini_guncelle)
        self.layout.add_widget(self.camera)

        btn_geri = Button(
            text='Geri Dön', 
            size_hint_y=0.12, 
            background_color=(0.5, 0.5, 0.5, 1), 
            background_normal='', 
            bold=True,
            font_size='18sp'
        )
        btn_geri.bind(on_release=self.geri_don)
        self.layout.add_widget(btn_geri)

        self.add_widget(self.layout)

    def _rotation_merkezini_guncelle(self, instance, value):
        self.rot.origin = self.camera.center

    def on_enter(self):
        self.camera.play = True

    def on_leave(self):
        self.camera.play = False

    def geri_don(self, instance):
        self.manager.current = 'ana_ekran'


# --- Uygulama Sınıfı ---
class StokTakipApp(App):
    def build(self):
        android_izinlerini_iste()

        sm = ScreenManager()
        sm.add_widget(AnaEkran(name='ana_ekran'))
        sm.add_widget(ParcaEkleEkrani(name='ekle_ekrani'))
        sm.add_widget(KameraEkrani(name='kamera_ekrani'))
        return sm

    def on_start(self):
        verileri_yukle()
        self.root.get_screen('ana_ekran').listeyi_guncelle()


if __name__ == '__main__':
    StokTakipApp().run()
