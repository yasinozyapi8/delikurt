import os
import sys
import time
import requests

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage

Window.clearcolor = (0.07, 0.09, 0.11, 1)

LIVE_CODE_URL = "https://raw.githubusercontent.com/yasinozyapi8/delikurt/refs/heads/main/app_mobile.py"
LOGO_STUDYO_URL = "https://raw.githubusercontent.com/yasinozyapi8/delikurt/refs/heads/main/delikurt_studyo.png"
LOGO_IMZA_URL = "https://raw.githubusercontent.com/yasinozyapi8/delikurt/refs/heads/main/delikurt_imza.png"

class LoaderApp(App):
    def build(self):
        root = FloatLayout()

        center_box = BoxLayout(
            orientation='vertical',
            size_hint=(0.8, 0.2),
            pos_hint={'center_x': 0.5, 'center_y': 0.55},
            spacing=10
        )
        
        self.lbl_status = Label(
            text="⏳ Yükleniyor...", 
            font_size='20sp', 
            bold=True,
            color=(0.9, 0.9, 0.9, 1)
        )
        center_box.add_widget(self.lbl_status)
        root.add_widget(center_box)

        footer_box = BoxLayout(
            orientation='horizontal',
            size_hint=(0.80, 0.10),
            pos_hint={'center_x': 0.5, 'y': 0.04},
            spacing=15
        )

        img_studyo = AsyncImage(
            source=LOGO_STUDYO_URL,
            size_hint=(0.5, 1),
            allow_stretch=True,
            keep_ratio=True
        )
        img_imza = AsyncImage(
            source=LOGO_IMZA_URL,
            size_hint=(0.5, 1),
            allow_stretch=True,
            keep_ratio=True
        )

        footer_box.add_widget(img_studyo)
        footer_box.add_widget(img_imza)
        root.add_widget(footer_box)

        return root

    def on_start(self):
        Clock.schedule_once(lambda dt: self.kod_indir_ve_baslat(), 0.5)

    def kod_indir_ve_baslat(self):
        try:
            url = f"{LIVE_CODE_URL}?t={int(time.time())}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                code_text = resp.text
                self.lbl_status.text = "✅ Başlatılıyor..."
                
                # 🧹 Loader bileşenlerini pencereden tamamen temizle
                Window.clear_widgets()
                
                exec_globals = {
                    '__name__': '__main__',
                    '__file__': 'app_mobile.py'
                }
                exec(code_text, exec_globals)
            else:
                self.lbl_status.text = f"❌ Kod İndirilemedi ({resp.status_code})"
        except Exception as e:
            self.lbl_status.text = f"❌ Bağlantı Hatası:\n{str(e)}"

if __name__ == '__main__':
    LoaderApp().run()
