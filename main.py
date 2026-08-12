import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window

# Mobil ekran arka plan rengi
Window.clearcolor = (0.95, 0.96, 0.98, 1)

def veritabani_kur():
    conn = sqlite3.connect("yedek_parca.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parca_kodu TEXT UNIQUE NOT NULL,
            barkod_no TEXT UNIQUE,
            parca_adi TEXT NOT NULL,
            kategori TEXT,
            miktar INTEGER DEFAULT 0,
            kritik_seviye INTEGER DEFAULT 5,
            raf_konumu TEXT DEFAULT 'Belirtilmedi'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stok_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parca_kodu TEXT NOT NULL,
            islem_tipi TEXT NOT NULL,
            miktar INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            aciklama TEXT
        )
    ''')
    conn.commit()
    conn.close()

class StokMobilApp(App):
    def build(self):
        veritabani_kur()
        self.title = "Stok Takip Mobile"

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Üst Başlık Barı
        header = Label(
            text="📱 YEDEK PARÇA STOK TAKİP",
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=50,
            color=(0.17, 0.24, 0.31, 1)
        )
        main_layout.add_widget(header)

        # Arama ve Aksiyon Barı
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=8)
        
        self.txt_arama = TextInput(
            hint_text='Ara / Barkod...',
            multiline=False,
            font_size='15sp'
        )
        self.txt_arama.bind(text=self.stok_listele)
        top_bar.add_widget(self.txt_arama)

        # Kamera / Barkod Butonu
        btn_kamera = Button(
            text='📷 Kamera',
            background_color=(0.2, 0.6, 0.86, 1),
            size_hint_x=0.3,
            bold=True
        )
        btn_kamera.bind(on_press=self.kamera_ac)
        top_bar.add_widget(btn_kamera)

        # Yeni Parça Ekle Butonu
        btn_ekle = Button(
            text='+ Yeni',
            background_color=(0.15, 0.68, 0.37, 1),
            size_hint_x=0.25,
            bold=True
        )
        btn_ekle.bind(on_press=self.yeni_parca_popup)
        top_bar.add_widget(btn_ekle)

        main_layout.add_widget(top_bar)

        # Stok Listesi
        scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)

        main_layout.add_widget(scroll)

        self.stok_listele()
        return main_layout

    def stok_listele(self, *args):
        self.list_layout.clear_widgets()
        arama = self.txt_arama.text.strip()

        conn = sqlite3.connect("yedek_parca.db")
        cursor = conn.cursor()

        if arama:
            query = "SELECT parca_kodu, barkod_no, parca_adi, miktar, kritik_seviye, raf_konumu FROM stok WHERE parca_kodu LIKE ? OR parca_adi LIKE ? OR barkod_no LIKE ?"
            cursor.execute(query, (f"%{arama}%", f"%{arama}%", f"%{arama}%"))
        else:
            cursor.execute("SELECT parca_kodu, barkod_no, parca_adi, miktar, kritik_seviye, raf_konumu FROM stok")

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            kod, barkod, ad, miktar, kritik, raf = row
            durum_renk = (0.92, 0.11, 0.14, 1) if miktar <= kritik else (0.1, 0.7, 0.3, 1)

            card = BoxLayout(orientation='vertical', size_hint_y=None, height=110, padding=8, spacing=5)
            
            row1 = BoxLayout(orientation='horizontal')
            lbl_ad = Label(text=f"[b]{ad}[/b] ({kod})", markup=True, font_size='16sp', color=(0.1, 0.1, 0.1, 1), halign='left')
            lbl_ad.bind(size=lbl_ad.setter('text_size'))
            
            lbl_miktar = Label(text=f"Stok: [b]{miktar}[/b]", markup=True, font_size='18sp', color=durum_renk, size_hint_x=0.4)
            row1.add_widget(lbl_ad)
            row1.add_widget(lbl_miktar)

            row2 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
            lbl_raf = Label(text=f"Raf: {raf}\nBarkod: {barkod}", font_size='11sp', color=(0.5, 0.5, 0.5, 1))
            
            btn_arttir = Button(text='➕ 1 Ekle', background_color=(0.15, 0.68, 0.37, 1), bold=True)
            btn_arttir.bind(on_press=lambda x, k=kod: self.stok_degistir(k, 1))

            btn_azalt = Button(text='➖ 1 Düş', background_color=(0.75, 0.22, 0.17, 1), bold=True)
            btn_azalt.bind(on_press=lambda x, k=kod: self.stok_degistir(k, -1))

            row2.add_widget(lbl_raf)
            row2.add_widget(btn_arttir)
            row2.add_widget(btn_azalt)

            card.add_widget(row1)
            card.add_widget(row2)

            self.list_layout.add_widget(card)

    def stok_degistir(self, parca_kodu, miktar_degisimi):
        conn = sqlite3.connect("yedek_parca.db")
        cursor = conn.cursor()
        cursor.execute("SELECT miktar FROM stok WHERE parca_kodu = ?", (parca_kodu,))
        res = cursor.fetchone()

        if res:
            mevcut = res[0]
            yeni = mevcut + miktar_degisimi
            if yeni >= 0:
                cursor.execute("UPDATE stok SET miktar = ? WHERE parca_kodu = ?", (yeni, parca_kodu))
                
                tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_tipi = 'GİRİŞ' if miktar_degisimi > 0 else 'ÇIKIŞ'
                cursor.execute("INSERT INTO stok_hareketleri (parca_kodu, islem_tipi, miktar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)",
                               (parca_kodu, log_tipi, abs(miktar_degisimi), tarih, 'Mobil Arayüz İşlemi'))
                conn.commit()

        conn.close()
        self.stok_listele()

    def kamera_ac(self, instance):
        """Kamera / Barkod okuyucu modülünü çalıştırır."""
        try:
            from plyer import barcode
            barcode.scan(on_complete=self.barkod_okundu)
        except Exception:
            popup = Popup(
                title='Kamera Bilgisi',
                content=Label(text='Barkod okutmak için arama alanına\nel terminali ile de barkod girebilirsiniz.'),
                size_hint=(0.8, 0.4)
            )
            popup.open()

    def barkod_okundu(self, result):
        if result and not result.cancelled:
            self.txt_arama.text = result.data.strip()

    def yeni_parca_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        txt_kod = TextInput(hint_text='Parça Kodu*', multiline=False)
        txt_ad = TextInput(hint_text='Parça Adı*', multiline=False)
        txt_kat = TextInput(hint_text='Kategori', multiline=False)
        txt_mkt = TextInput(hint_text='Başlangıç Miktarı (0)', input_filter='int', multiline=False)
        
        content.add_widget(txt_kod)
        content.add_widget(txt_ad)
        content.add_widget(txt_kat)
        content.add_widget(txt_mkt)

        popup = Popup(title='Yeni Parça Ekle', content=content, size_hint=(0.9, 0.6))

        def kaydet(btn):
            kod = txt_kod.text.strip()
            ad = txt_ad.text.strip()
            if kod and ad:
                kat = txt_kat.text.strip() or 'Genel'
                mkt = int(txt_mkt.text.strip() or 0)
                try:
                    conn = sqlite3.connect("yedek_parca.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO stok (parca_kodu, barkod_no, parca_adi, kategori, miktar) VALUES (?, ?, ?, ?, ?)",
                                   (kod, kod, ad, kat, mkt))
                    conn.commit()
                    conn.close()
                    popup.dismiss()
                    self.stok_listele()
                except sqlite3.IntegrityError:
                    pass

        btn_kaydet = Button(text='Kaydet', background_color=(0.15, 0.68, 0.37, 1), size_hint_y=None, height=45)
        btn_kaydet.bind(on_press=kaydet)
        content.add_widget(btn_kaydet)

        popup.open()

if __name__ == '__main__':
    StokMobilApp().run()