import os
from kivy.app import App
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

# --- Basılı Tutma (Long Press) Özellikli Buton ---
class BasiliTutulanItem(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._long_press_event = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # 0.8 saniye basılı tutulursa uzun basma tetiklenir
            self._long_press_event = Clock.schedule_once(self._uzun_basildi, 0.8)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._long_press_event:
            self._long_press_event.cancel()
        return super().on_touch_up(touch)

    def _uzun_basildi(self, dt):
        if hasattr(self, 'on_long_press_callback') and self.on_long_press_callback:
            self.on_long_press_callback(self)


# --- Örnek Veritabanı / Liste Verisi ---
VERITABANI = [
    {"kod": "BRK-001", "ad": "Rulman 6204", "raf": "A-12", "stok": 15},
    {"kod": "BRK-002", "ad": "V-Kayışı A-42", "raf": "B-03", "stok": 8},
]


# --- Ana Liste Ekranı ---
class AnaEkran(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 1. Üst Başlık
        main_layout.add_widget(Label(text="STOK TAKİP SİSTEMİ", font_size='20sp', size_hint_y=0.08, bold=True))

        # 2. Barkod Arama & Kamera & Elle Girdi Alanı
        arama_box = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=5)
        
        self.txt_barkod_ara = TextInput(hint_text='Barkod / Parça Ara veya Gir...', multiline=False)
        btn_ara = Button(text='🔍 Ara', size_hint_x=0.25)
        btn_ara.bind(on_release=self.barkod_ara)
        
        btn_kamera = Button(text='📷', size_hint_x=0.2)
        btn_kamera.bind(on_release=self.kamera_ac)

        arama_box.add_widget(self.txt_barkod_ara)
        arama_box.add_widget(btn_ara)
        arama_box.add_widget(btn_kamera)
        main_layout.add_widget(arama_box)

        # 3. Parça Listesi (ScrollView)
        self.scroll = ScrollView(size_hint=(1, 0.72))
        self.liste_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.liste_layout.bind(minimum_height=self.liste_layout.setter('height'))
        self.scroll.add_widget(self.liste_layout)
        main_layout.add_widget(self.scroll)

        # 4. Alt Menü (Yedek Parça Ekle Butonu)
        alt_box = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        btn_yeni_ekle = Button(text='➕ Yeni Yedek Parça Ekle', background_color=(0.2, 0.7, 0.2, 1))
        btn_yeni_ekle.bind(on_release=lambda x: setattr(self.manager, 'current', 'ekle_ekrani'))
        alt_box.add_widget(btn_yeni_ekle)
        main_layout.add_widget(alt_box)

        self.add_widget(main_layout)
        self.listeyi_guncelle()

    def listeyi_guncelle(self, filtre=""):
        self.liste_layout.clear_widgets()
        
        for item in VERITABANI:
            if filtre and (filtre.lower() not in item['kod'].lower() and filtre.lower() not in item['ad'].lower()):
                continue

            btn_text = f"📦 {item['ad']}\nKod: {item['kod']} | Raf: {item['raf']} | Stok: {item['stok']} Adet"
            
            btn = BasiliTutulanItem(
                text=btn_text,
                size_hint_y=None,
                height=70,
                halign='left',
                valign='middle'
            )
            btn.text_size = (btn.width, None)
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (s.width - 20, None)))
            
            # Veriyi butona bağla
            btn.item_data = item
            btn.on_long_press_callback = self.duzenleme_popup_ac
            
            self.liste_layout.add_widget(btn)

    def barkod_ara(self, instance):
        self.listeyi_guncelle(self.txt_barkod_ara.text)

    def kamera_ac(self, instance):
        # Kamera Ekranına Geçiş
        self.manager.current = 'kamera_ekrani'

    # Uzun basılınca açılacak Düzenleme / Silme Menüsü
    def duzenleme_popup_ac(self, item_button):
        data = item_button.item_data

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Alanlar
        txt_ad = TextInput(text=data['ad'], multiline=False)
        txt_kod = TextInput(text=data['kod'], multiline=False)
        txt_raf = TextInput(text=data['raf'], multiline=False)
        txt_stok = TextInput(text=str(data['stok']), multiline=False, input_filter='int')

        content.add_widget(Label(text="Parça Adı:"))
        content.add_widget(txt_ad)
        content.add_widget(Label(text="Barkod / Kod:"))
        content.add_widget(txt_kod)
        content.add_widget(Label(text="Raf Kodu:"))
        content.add_widget(txt_raf)
        content.add_widget(Label(text="Stok Adedi:"))
        
        # Stok arttır / azalt butonlu alan
        stok_box = BoxLayout(orientation='horizontal', spacing=5)
        btn_e = Button(text='➖', size_hint_x=0.2)
        btn_a = Button(text='➕', size_hint_x=0.2)
        
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

        # Kaydet ve Sil Butonları
        buton_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        btn_kaydet = Button(text='✏️ Güncelle', background_color=(0, 0.6, 1, 1))
        btn_sil = Button(text='🗑️ Sil', background_color=(1, 0.2, 0.2, 1))
        
        popup = Popup(title='Parça Düzenle / Sil', content=content, size_hint=(0.9, 0.85))

        def kaydet_action(x):
            data['ad'] = txt_ad.text
            data['kod'] = txt_kod.text
            data['raf'] = txt_raf.text
            data['stok'] = int(txt_stok.text or 0)
            self.listeyi_guncelle()
            popup.dismiss()

        def sil_action(x):
            VERITABANI.remove(data)
            self.listeyi_guncelle()
            popup.dismiss()

        btn_kaydet.bind(on_release=kaydet_action)
        btn_sil.bind(on_release=sil_action)

        buton_box.add_widget(btn_kaydet)
        buton_box.add_widget(btn_sil)
        content.add_widget(buton_box)

        popup.open()


# --- Parça Ekleme Ekranı (Raf Girişi Dahil) ---
class ParcaEkleEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        layout.add_widget(Label(text="YENİ YEDEK PARÇA EKLE", font_size='18sp', bold=True))

        self.txt_ad = TextInput(hint_text='Parça Adı', multiline=False)
        self.txt_kod = TextInput(hint_text='Barkod / Parça Kodu', multiline=False)
        self.txt_raf = TextInput(hint_text='Raf / Lokasyon Kodu (Örn: A-12)', multiline=False)
        self.txt_stok = TextInput(hint_text='Başlangıç Stok Adedi', multiline=False, input_filter='int')

        layout.add_widget(Label(text="Parça Adı:"))
        layout.add_widget(self.txt_ad)
        layout.add_widget(Label(text="Barkod:"))
        layout.add_widget(self.txt_kod)
        layout.add_widget(Label(text="Raf Numarası:"))
        layout.add_widget(self.txt_raf)
        layout.add_widget(Label(text="Stok Adedi:"))
        layout.add_widget(self.txt_stok)

        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.3)
        btn_kaydet = Button(text='💾 Kaydet', background_color=(0.2, 0.8, 0.2, 1))
        btn_iptal = Button(text='❌ İptal', background_color=(0.8, 0.2, 0.2, 1))

        btn_kaydet.bind(on_release=self.kaydet)
        btn_iptal.bind(on_release=lambda x: setattr(self.manager, 'current', 'ana_ekran'))

        btn_box.add_widget(btn_kaydet)
        btn_box.add_widget(btn_iptal)
        layout.add_widget(btn_box)

        self.add_widget(layout)

    def kaydet(self, instance):
        if self.txt_ad.text and self.txt_kod.text:
            yeni_parca = {
                "kod": self.txt_kod.text,
                "ad": self.txt_ad.text,
                "raf": self.txt_raf.text or "-",
                "stok": int(self.txt_stok.text or 0)
            }
            VERITABANI.append(yeni_parca)
            
            # Ana ekrandaki listeyi yenile
            self.manager.get_screen('ana_ekran').listeyi_guncelle()
            
            # Formu temizle
            self.txt_ad.text = ""
            self.txt_kod.text = ""
            self.txt_raf.text = ""
            self.txt_stok.text = ""
            
            self.manager.current = 'ana_ekran'


# --- Kamera Ekranı (Placeholder / Entegrasyon) ---
class KameraEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        layout.add_widget(Label(text="📷 BARKO TARA", font_size='18sp'))
        layout.add_widget(Label(text="[Kamera Görünümü]\n(Cihaz kamerasını barkoda tutun)", halign='center'))

        btn_geri = Button(text='🔙 Geri Dön', size_hint_y=0.15)
        btn_geri.bind(on_release=lambda x: setattr(self.manager, 'current', 'ana_ekran'))
        layout.add_widget(btn_geri)

        self.add_widget(layout)


# --- Uygulama Sınıfı ---
class StokTakipApp(App):
    def build(self):
        # Android İzinlerini Başlangıçta İste
        android_izinlerini_iste()

        sm = ScreenManager()
        sm.add_widget(AnaEkran(name='ana_ekran'))
        sm.add_widget(ParcaEkleEkrani(name='ekle_ekrani'))
        sm.add_widget(KameraEkrani(name='kamera_ekrani'))
        return sm


if __name__ == '__main__':
    StokTakipApp().run()
