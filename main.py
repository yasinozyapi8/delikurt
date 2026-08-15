import os
import sys
import time
import requests
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.utils import platform

# 🚀 GITHUB'DAKİ CANLI KOD ADRESİNİZ
LIVE_CODE_URL = "https://raw.githubusercontent.com/yasinozyapi8/delikurt/refs/heads/main/app_mobile.py"

class LoaderApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20)
        self.lbl_status = Label(
            text="⏳ Güncel Sürüm Denetleniyor...", 
            font_size='18sp', 
            bold=True
        )
        self.layout.add_widget(self.lbl_status)
        return self.layout

    def on_start(self):
        Clock.schedule_once(lambda dt: self.kod_indir_ve_baslat(), 0.5)

    def kod_indir_ve_baslat(self):
        try:
            # Önbelleği (cache) kırmak için zaman damgası ekliyoruz
            url = f"{LIVE_CODE_URL}?t={int(time.time())}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                code_text = resp.text
                self.lbl_status.text = "✅ Başlatılıyor..."
                
                # İndirilen canlı Python kodunu sistem ortamında çalıştırıyoruz
                exec_globals = {
                    '__name__': '__main__',
                    '__file__': 'app_mobile.py'
                }
                exec(code_text, exec_globals)
            else:
                self.lbl_status.text = f"❌ Kod İndirilemedi (Hata: {resp.status_code})"
        except Exception as e:
            self.lbl_status.text = f"❌ Bağlantı Hatası:\n{str(e)}"

if __name__ == '__main__':
    LoaderApp().run()
