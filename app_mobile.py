import os
import sys
import json
import threading
import requests

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.uix.image import AsyncImage
from kivy.uix.widget import Widget
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Line

Window.clearcolor = (0.12, 0.15, 0.18, 1)
Window.softinput_mode = 'below_target'

# 🔥 FIREBASE WEB API KEY YAPILANDIRMASI
PROJECT_ID = "stok-takip-f061b"
API_KEY = "AIzaSyCxg29J4To7hVgXxHOhAY76oOwDcZqyvRY"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/stoklar"

VERITABANI = []
VERI_KILIDI = threading.Lock()


# --- FIREBASE ARKA PLAN REST İŞLEMLERİ ---
def REST_verileri_cek_async(on_success_callback=None):
    def run():
        global VERITABANI
        try:
            url = f"{BASE_URL}?key={API_KEY}&pageSize=300"
            res = requests.get(url, timeout=6)
            if res.status_code == 200:
                data = res.json()
                yeni_liste = []
                documents = data.get("documents", [])
                for doc in documents:
                    fields = doc.get("fields", {})
                    parca_kodu = fields.get("parca_kodu", {}).get("stringValue", "-")
                    barkod_no = fields.get("barkod_no", {}).get("stringValue", parca_kodu)
                    parca_adi = fields.get("parca_adi", {}).get("stringValue", "-")
                    kategori = fields.get("kategori", {}).get("stringValue", "Genel")
                    raf_konumu = fields.get("raf_konumu", {}).get("stringValue", "Belirtilmedi")
                    
                    m_raw = fields.get("miktar", {})
                    miktar = int(m_raw.get("integerValue", m_raw.get("doubleValue", 0)))
                    
                    k_raw = fields.get("kritik_seviye", {})
                    kritik = int(k_raw.get("integerValue", k_raw.get("doubleValue", 5)))

                    yeni_liste.append({
                        "parca_kodu": parca_kodu,
                        "barkod_no": barkod_no,
                        "parca_adi": parca_adi,
                        "kategori": kategori,
                        "raf_konumu": raf_konumu,
                        "miktar": miktar,
                        "kritik_seviye": kritik
                    })
                
                with VERI_KILIDI:
                    VERITABANI = yeni_liste
                
                if on_success_callback:
                    Clock.schedule_once(lambda dt: on_success_callback(), 0)
        except Exception as e:
            print("Arka Plan Veri Çekme Hatası:", e)

    threading.Thread(target=run, daemon=True).start()


def REST_stok_guncelle_async(doc_id, yeni_stok, callback=None):
    def run():
        url = f"{BASE_URL}/{doc_id}?key={API_KEY}&updateMask.fieldPaths=miktar"
        payload = {"fields": {"miktar": {"integerValue": int(yeni_stok)}}}
        try:
            requests.patch(url, json=payload, timeout=6)
            REST_verileri_cek_async(callback)
        except Exception as e:
            print("Stok Güncelleme Hatası:", e)
    threading.Thread(target=run, daemon=True).start()


def REST_parca_ekle_veya_guncelle_async(doc_id, p_data, callback=None):
    def run():
        url = f"{BASE_URL}/{doc_id}?key={API_KEY}"
        payload = {
            "fields": {
                "parca_kodu": {"stringValue": str(p_data.get("parca_kodu", "-"))},
                "barkod_no": {"stringValue": str(p_data.get("barkod_no", "-"))},
                "parca_adi": {"stringValue": str(p_data.get("parca_adi", "-"))},
                "kategori": {"stringValue": str(p_data.get("kategori", "Genel"))},
                "raf_konumu": {"stringValue": str(p_data.get("raf_konumu", "Belirtilmedi"))},
                "miktar": {"integerValue": int(p_data.get("miktar", 0))},
                "kritik_seviye": {"integerValue": int(p_data.get("kritik_seviye", 5))}
            }
        }
        try:
            requests.patch(url, json=payload, timeout=6)
            REST_verileri_cek_async(callback)
        except Exception as e:
            print("Parça Kayıt Hatası:", e)
    threading.Thread(target=run, daemon=True).start()


def REST_parca_sil_async(doc_id, callback=None):
    def run():
        url = f"{BASE_URL}/{doc_id}?key={API_KEY}"
        try:
            requests.delete(url, timeout=6)
            REST_verileri_cek_async(callback)
        except Exception as e:
            print("Silme Hatası:", e)
    threading.Thread(target=run, daemon=True).start()


def android_izinlerini_iste():
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.INTERNET,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print("İzin alma hatası:", e)


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


class AnaEkran(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)
        
        main_layout.add_widget(Label(
            text="STOK TAKİP SİSTEMİ", 
            font_size='18sp', 
            size_hint_y=0.08, 
            bold=True,
            color=(0.3, 0.7, 1, 1)
        ))

        arama_box = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=6)
        self.txt_barkod_ara = TextInput(
            hint_text='Barkod veya Parça Ara...', 
            multiline=False, 
            background_color=(0.9, 0.9, 0.9, 1),
            font_size='16sp',
            use_bubble=False,
            use_handles=False
        )
        btn_ara = Button(text='Ara', size_hint_x=0.22, background_color=(0.2, 0.5, 0.9, 1), background_normal='', bold=True)
        btn_ara.bind(on_release=self.barkod_ara)
        
        btn_kamera = Button(text='📷 Kamera', size_hint_x=0.28, background_color=(0.8, 0.4, 0.1, 1), background_normal='', bold=True)
        btn_kamera.bind(on_release=self.kamera_ac)

        arama_box.add_widget(self.txt_barkod_ara)
        arama_box.add_widget(btn_ara)
        arama_box.add_widget(btn_kamera)
        main_layout.add_widget(arama_box)

        self.scroll = ScrollView(size_hint=(1, 0.73))
        self.liste_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.liste_layout.bind(minimum_height=self.liste_layout.setter('height'))
        self.scroll.add_widget(self.liste_layout)
        main_layout.add_widget(self.scroll)

        alt_box = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        btn_yeni_ekle = Button(text='+ Yeni Yedek Parça Ekle', font_size='17sp', bold=True, background_color=(0.1, 0.7, 0.3, 1), background_normal='')
        btn_yeni_ekle.bind(on_release=lambda x: setattr(self.manager, 'current', 'ekle_ekrani'))
        alt_box.add_widget(btn_yeni_ekle)
        main_layout.add_widget(alt_box)

        self.add_widget(main_layout)

    def on_enter(self):
        REST_verileri_cek_async(self.listeyi_guncelle)

    def listeyi_guncelle(self, filtre=None):
        if filtre is None or not isinstance(filtre, str):
            filtre = self.txt_barkod_ara.text

        self.liste_layout.clear_widgets()
        
        with VERI_KILIDI:
            yerel_liste = list(VERITABANI)

        for item in yerel_liste:
            kod = str(item.get('parca_kodu', '-'))
            barkod = str(item.get('barkod_no', kod))
            ad = str(item.get('parca_adi', '-'))
            
            if filtre:
                f = filtre.lower()
                if (f not in kod.lower() and f not in barkod.lower() and f not in ad.lower()):
                    continue

            card = BoxLayout(orientation='horizontal', size_hint_y=None, height=120, spacing=6)
            stok_adedi = int(item.get('miktar', 0))
            kritik_sınıri = int(item.get('kritik_seviye', 5))
            is_kritik = stok_adedi <= kritik_sınıri

            bg_color = (0.55, 0.15, 0.15, 1) if is_kritik else (0.18, 0.22, 0.28, 1)
            uyari_metni = " [⚠️ KRİTİK!]" if is_kritik else ""

            btn_text = (f" Adı: {ad}{uyari_metni}\n Kod: {kod} | Barkod: {barkod}\n Raf: {item.get('raf_konumu', '-')} | Stok: {stok_adedi} Adet")
            
            btn_details = BasiliTutulanItem(text=btn_text, size_hint_x=0.74, halign='left', valign='middle', background_color=bg_color, background_normal='', font_size='13sp')
            btn_details.text_size = (btn_details.width, None)
            btn_details.bind(size=lambda s, w: setattr(s, 'text_size', (s.width - 15, None)))
            btn_details.item_data = item
            btn_details.on_long_press_callback = lambda btn: Clock.schedule_once(lambda dt: self.duzenleme_popup_ac(btn), 0.1)
            
            stok_box = BoxLayout(orientation='vertical', size_hint_x=0.26, spacing=4)
            btn_plus = Button(text='+', font_size='22sp', bold=True, background_color=(0.1, 0.7, 0.3, 1), background_normal='')
            btn_minus = Button(text='-', font_size='22sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), background_normal='')

            def make_arttir(d):
                def arttir(x):
                    d['miktar'] = int(d.get('miktar', 0)) + 1
                    doc_id = str(d.get('parca_kodu'))
                    REST_stok_guncelle_async(doc_id, d['miktar'], self.listeyi_guncelle)
                return arttir

            def make_eksilt(d):
                def eksilt(x):
                    curr = int(d.get('miktar', 0))
                    if curr > 0:
                        d['miktar'] = curr - 1
                        doc_id = str(d.get('parca_kodu'))
                        REST_stok_guncelle_async(doc_id, d['miktar'], self.listeyi_guncelle)
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

    def duzenleme_popup_ac(self, item_button):
        data = item_button.item_data
        
        main_popup_box = BoxLayout(orientation='vertical', spacing=8, padding=10)
        scroll_view = ScrollView(size_hint=(1, 0.78))
        content = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        
        txt_ad = TextInput(text=str(data.get('parca_adi', '')), multiline=False, size_hint_y=None, height=55, font_size='16sp')
        txt_parca_kodu = TextInput(text=str(data.get('parca_kodu', '')), multiline=False, size_hint_y=None, height=55, font_size='16sp')
        txt_barkod = TextInput(text=str(data.get('barkod_no', '')), multiline=False, size_hint_y=None, height=55, font_size='16sp')
        txt_raf = TextInput(text=str(data.get('raf_konumu', '')), multiline=False, size_hint_y=None, height=55, font_size='16sp')
        txt_stok = TextInput(text=str(data.get('miktar', 0)), multiline=False, input_filter='int', size_hint_y=None, height=55, font_size='16sp')
        txt_kritik_stok = TextInput(text=str(data.get('kritik_seviye', 5)), multiline=False, input_filter='int', size_hint_y=None, height=55, font_size='16sp')

        content.add_widget(Label(text="Parça Adı:", size_hint_y=None, height=25, bold=True))
        content.add_widget(txt_ad)
        content.add_widget(Label(text="Parça Kodu:", size_hint_y=None, height=25, bold=True))
        content.add_widget(txt_parca_kodu)
        content.add_widget(Label(text="Barkod / QR:", size_hint_y=None, height=25, bold=True))
        content.add_widget(txt_barkod)
        content.add_widget(Label(text="Raf Kodu:", size_hint_y=None, height=25, bold=True))
        content.add_widget(txt_raf)
        content.add_widget(Label(text="Kritik Stok Seviyesi:", size_hint_y=None, height=25, bold=True))
        content.add_widget(txt_kritik_stok)
        content.add_widget(Label(text="Mevcut Stok Adedi:", size_hint_y=None, height=25, bold=True))
        
        stok_box = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=55)
        btn_e = Button(text='-', size_hint_x=0.25, background_color=(0.7, 0.2, 0.2, 1), background_normal='', font_size='20sp', bold=True)
        btn_a = Button(text='+', size_hint_x=0.25, background_color=(0.2, 0.6, 0.2, 1), background_normal='', font_size='20sp', bold=True)
        
        btn_e.bind(on_release=lambda x: setattr(txt_stok, 'text', str(max(0, int(txt_stok.text or 0) - 1))))
        btn_a.bind(on_release=lambda x: setattr(txt_stok, 'text', str(int(txt_stok.text or 0) + 1)))
        
        stok_box.add_widget(btn_e)
        stok_box.add_widget(txt_stok)
        stok_box.add_widget(btn_a)
        content.add_widget(stok_box)

        scroll_view.add_widget(content)
        main_popup_box.add_widget(scroll_view)

        btn_qr_goster = Button(text='🖨️ QR Kod Göster', size_hint_y=0.10, background_color=(0.9, 0.5, 0.1, 1), background_normal='', bold=True)
        btn_qr_goster.bind(on_release=lambda x: self.qr_popup_goster(str(txt_barkod.text or txt_parca_kodu.text), txt_ad.text))
        main_popup_box.add_widget(btn_qr_goster)

        buton_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.12)
        btn_kaydet = Button(text='Güncelle', background_color=(0.1, 0.5, 0.9, 1), background_normal='', bold=True, font_size='16sp')
        btn_sil = Button(text='Sil', background_color=(0.8, 0.2, 0.2, 1), background_normal='', bold=True, font_size='16sp')
        popup = Popup(title='Parça Düzenle / Sil', content=main_popup_box, size_hint=(0.92, 0.92))

        def kaydet_action(x):
            eski_doc_id = str(data.get('parca_kodu'))
            yeni_doc_id = str(txt_parca_kodu.text.strip())
            
            data['parca_adi'] = txt_ad.text
            data['parca_kodu'] = yeni_doc_id
            data['barkod_no'] = txt_barkod.text
            data['raf_konumu'] = txt_raf.text
            data['miktar'] = int(txt_stok.text or 0)
            data['kritik_seviye'] = int(txt_kritik_stok.text or 5)

            if eski_doc_id != yeni_doc_id:
                REST_parca_sil_async(eski_doc_id)
            
            REST_parca_ekle_veya_guncelle_async(yeni_doc_id, data, self.listeyi_guncelle)
            popup.dismiss()

        def sil_action(x):
            doc_id = str(data.get('parca_kodu'))
            REST_parca_sil_async(doc_id, self.listeyi_guncelle)
            popup.dismiss()

        btn_kaydet.bind(on_release=kaydet_action)
        btn_sil.bind(on_release=sil_action)

        buton_box.add_widget(btn_kaydet)
        buton_box.add_widget(btn_sil)
        main_popup_box.add_widget(buton_box)
        
        popup.open()

    def qr_popup_goster(self, barkod_metni, parca_adi):
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={barkod_metni}"
        
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        box.add_widget(Label(text=f"{parca_adi}\nBarkod: {barkod_metni}", font_size='15sp', bold=True, size_hint_y=0.2, halign='center'))
        box.add_widget(AsyncImage(source=qr_url))

        qr_popup = Popup(title='QR Etiket', content=box, size_hint=(0.85, 0.65))
        qr_popup.open()


class ParcaEkleEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=8)
        
        main_layout.add_widget(Label(text="YENİ YEDEK PARÇA EKLE", font_size='20sp', bold=True, color=(0.3, 0.7, 1, 1), size_hint_y=0.08))

        form_layout = BoxLayout(orientation='vertical', spacing=6, size_hint_y=0.78)

        self.txt_ad = TextInput(hint_text='Örn: Rulman 6204', multiline=False, size_hint_y=None, height=55, font_size='16sp')
        self.txt_parca_kodu = TextInput(hint_text='Örn: PRC-001', multiline=False, size_hint_y=None, height=55, font_size='16sp')
        self.txt_barkod = TextInput(hint_text='Örn: 86900012345', multiline=False, size_hint_y=None, height=55, font_size='16sp')
        self.txt_raf = TextInput(hint_text='Örn: A-12', multiline=False, size_hint_y=None, height=55, font_size='16sp')
        self.txt_stok = TextInput(hint_text='Örn: 10', multiline=False, input_filter='int', size_hint_y=None, height=55, font_size='16sp')
        self.txt_kritik_stok = TextInput(hint_text='Örn: 5', multiline=False, input_filter='int', size_hint_y=None, height=55, font_size='16sp')

        form_layout.add_widget(Label(text="Parça Adı:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_ad)
        form_layout.add_widget(Label(text="Parça Kodu:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_parca_kodu)
        form_layout.add_widget(Label(text="Barkod / QR:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_barkod)
        form_layout.add_widget(Label(text="Raf Numarası:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_raf)
        form_layout.add_widget(Label(text="Mevcut Stok Adedi:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_stok)
        form_layout.add_widget(Label(text="Kritik Stok Uyarısı Sınırı:", size_hint_y=None, height=22, bold=True))
        form_layout.add_widget(self.txt_kritik_stok)

        main_layout.add_widget(form_layout)

        btn_box = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=0.14)
        btn_kaydet = Button(text='Kaydet', background_color=(0.1, 0.7, 0.3, 1), background_normal='', bold=True, font_size='18sp')
        btn_iptal = Button(text='İptal', background_color=(0.8, 0.2, 0.2, 1), background_normal='', bold=True, font_size='18sp')

        btn_kaydet.bind(on_release=self.kaydet)
        btn_iptal.bind(on_release=lambda x: setattr(self.manager, 'current', 'ana_ekran'))

        btn_box.add_widget(btn_kaydet)
        btn_box.add_widget(btn_iptal)
        main_layout.add_widget(btn_box)

        self.add_widget(main_layout)

    def otomatık_barkod_doldur(self, barkod_metni):
        self.txt_parca_kodu.text = barkod_metni
        self.txt_barkod.text = barkod_metni

    def kaydet(self, instance):
        if self.txt_ad.text and self.txt_parca_kodu.text:
            kod = self.txt_parca_kodu.text.strip()
            yeni_parca = {
                "parca_adi": self.txt_ad.text.strip(),
                "parca_kodu": kod,
                "barkod_no": self.txt_barkod.text.strip() or kod,
                "kategori": "Genel",
                "raf_konumu": self.txt_raf.text.strip() or "Belirtilmedi",
                "miktar": int(self.txt_stok.text or 0),
                "kritik_seviye": int(self.txt_kritik_stok.text or 5)
            }
            
            def donus():
                self.manager.current = 'ana_ekran'

            REST_parca_ekle_veya_guncelle_async(kod, yeni_parca, donus)
            
            self.txt_ad.text = ""
            self.txt_parca_kodu.text = ""
            self.txt_barkod.text = ""
            self.txt_raf.text = ""
            self.txt_stok.text = ""
            self.txt_kritik_stok.text = ""


class BarkodVizoru(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._ciz, size=self._ciz)

    def _ciz(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 1, 0, 0.9)
            w, h = self.size
            x, y = self.pos
            box_w = w * 0.75
            box_h = h * 0.45
            box_x = x + (w - box_w) / 2
            box_y = y + (h - box_h) / 2
            Line(rectangle=(box_x, box_y, box_w, box_h), width=3)


class KameraEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.lbl_baslik = Label(text="BARKOD / QR TARAMA VİZÖRÜ", font_size='18sp', size_hint_y=0.08, bold=True, color=(0.3, 0.7, 1, 1))
        self.layout.add_widget(self.lbl_baslik)

        self.cam_container = FloatLayout(size_hint=(1, 0.70))
        self.cam_container.bind(size=self._kamera_boyutlandir, pos=self._kamera_boyutlandir)
        self.layout.add_widget(self.cam_container)

        scan_box = BoxLayout(orientation='horizontal', size_hint_y=0.10, spacing=6)
        self.txt_manual_scan = TextInput(
            hint_text='Barkod / Parça Kodu Girin...', 
            multiline=False, 
            size_hint_x=0.7, 
            font_size='15sp',
            use_bubble=False,
            use_handles=False
        )
        self.txt_manual_scan.bind(on_text_validate=lambda x: self.barkod_isle(self.txt_manual_scan.text.strip()))

        btn_process_scan = Button(text='Tarat / Ara', size_hint_x=0.3, background_color=(0.1, 0.6, 0.3, 1), background_normal='', bold=True)
        btn_process_scan.bind(on_release=lambda x: self.barkod_isle(self.txt_manual_scan.text.strip()))
        
        scan_box.add_widget(self.txt_manual_scan)
        scan_box.add_widget(btn_process_scan)
        self.layout.add_widget(scan_box)

        btn_geri = Button(text='Geri Dön', size_hint_y=0.10, background_color=(0.5, 0.5, 0.5, 1), background_normal='', bold=True, font_size='18sp')
        btn_geri.bind(on_release=self.geri_don)
        self.layout.add_widget(btn_geri)

        self.camera = None
        self.add_widget(self.layout)

    def on_enter(self):
        try:
            if not self.camera:
                self.camera = Camera(
                    play=True, 
                    resolution=(1280, 720),
                    allow_stretch=True, 
                    keep_ratio=False
                )
                
                with self.camera.canvas.before:
                    PushMatrix()
                    self.rot = Rotate(angle=-90)
                with self.camera.canvas.after:
                    PopMatrix()

                vizor = BarkodVizoru(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
                
                self.cam_container.clear_widgets()
                self.cam_container.add_widget(self.camera)
                self.cam_container.add_widget(vizor)
                
                Clock.schedule_once(lambda dt: self._kamera_boyutlandir(), 0.1)
            else:
                self.camera.play = True
        except Exception as e:
            self.cam_container.clear_widgets()
            self.cam_container.add_widget(Label(text=f"Kamera Başlatılamadı:\n{e}"))

    def _kamera_boyutlandir(self, *args):
        if hasattr(self, 'camera') and self.camera and self.cam_container:
            cw, ch = self.cam_container.size
            cx, cy = self.cam_container.pos

            self.camera.size_hint = (None, None)
            self.camera.width = ch
            self.camera.height = cw
            self.camera.center = (cx + cw / 2, cy + ch / 2)

            if hasattr(self, 'rot'):
                self.rot.origin = self.camera.center

    def barkod_isle(self, okunan_barkod):
        if not okunan_barkod: 
            self.lbl_baslik.text = "⚠️ Lütfen Barkod / Kodu Girin"
            self.lbl_baslik.color = (1, 0.5, 0.2, 1)
            return

        bulunan_item = None
        with VERI_KILIDI:
            for item in VERITABANI:
                if str(item.get("barkod_no", "")).lower() == okunan_barkod.lower() or str(item.get("parca_kodu", "")).lower() == okunan_barkod.lower():
                    bulunan_item = item
                    break

        if bulunan_item:
            self.hizli_stok_popup_ac(bulunan_item)
        else:
            ekle_ekrani = self.manager.get_screen('ekle_ekrani')
            ekle_ekrani.otomatık_barkod_doldur(okunan_barkod)
            self.manager.current = 'ekle_ekrani'

    def hizli_stok_popup_ac(self, item):
        parca_kodu = str(item.get('parca_kodu'))
        parca_adi = str(item.get('parca_adi'))
        mevcut_stok = int(item.get('miktar', 0))

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=f"PARÇA BULUNDU!\n\n{parca_adi}\nKod: {parca_kodu}\nMevcut Stok: {mevcut_stok} Adet", font_size='16sp', bold=True, halign='center'))

        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        btn_arttir = Button(text='+1 Ekle', background_color=(0.1, 0.7, 0.3, 1), background_normal='', bold=True, font_size='18sp')
        btn_azalt = Button(text='-1 Düş', background_color=(0.8, 0.2, 0.2, 1), background_normal='', bold=True, font_size='18sp')

        popup = Popup(title='Hızlı Stok Güncelleme', content=content, size_hint=(0.85, 0.45))

        def arttir_action(x):
            item['miktar'] = mevcut_stok + 1
            REST_stok_guncelle_async(parca_kodu, item['miktar'])
            popup.dismiss()

        def azalt_action(x):
            if mevcut_stok > 0:
                item['miktar'] = mevcut_stok - 1
                REST_stok_guncelle_async(parca_kodu, item['miktar'])
            popup.dismiss()

        btn_arttir.bind(on_release=arttir_action)
        btn_azalt.bind(on_release=azalt_action)

        btn_box.add_widget(btn_arttir)
        btn_box.add_widget(btn_azalt)
        content.add_widget(btn_box)

        popup.open()

    def on_leave(self):
        if self.camera:
            self.camera.play = False
        self.lbl_baslik.text = "BARKOD / QR TARAMA VİZÖRÜ"
        self.lbl_baslik.color = (0.3, 0.7, 1, 1)

    def geri_don(self, instance):
        self.manager.current = 'ana_ekran'


class StokTakipApp(App):
    def build(self):
        android_izinlerini_iste()
        sm = ScreenManager()
        sm.add_widget(AnaEkran(name='ana_ekran'))
        sm.add_widget(ParcaEkleEkrani(name='ekle_ekrani'))
        sm.add_widget(KameraEkrani(name='kamera_ekrani'))
        return sm

    def on_start(self):
        REST_verileri_cek_async(lambda: self.root.get_screen('ana_ekran').listeyi_guncelle())
        
        def verileri_periyodik_cek(dt):
            REST_verileri_cek_async(lambda: self.root.get_screen('ana_ekran').listeyi_guncelle())

        Clock.schedule_interval(verileri_periyodik_cek, 4)


if __name__ == '__main__':
    StokTakipApp().run()
