import os
import sys
import json
import threading
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from datetime import datetime
import qrcode
from PIL import Image, ImageTk

# --- FIREBASE WEB API KEY YAPILANDIRMASI ---
PROJECT_ID = "stok-takip-f061b"
API_KEY = "AIzaSyCxg29J4To7hVgXxHOhAY76oOwDcZqyvRY"


def dosya_yolu(goreceli_yol):
    olasi_yollar = [
        os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None,
        os.path.abspath("."),
        getattr(sys, '_MEIPASS', None)
    ]
    for yol in olasi_yollar:
        if yol:
            tam_yol = os.path.join(yol, goreceli_yol)
            if os.path.exists(tam_yol):
                return tam_yol
    return os.path.join(os.path.abspath("."), goreceli_yol)


# --- FIRESTORE REST API MİMARİSİ ---
def parse_firestore_fields(fields):
    data = {}
    for key, val_dict in fields.items():
        if "stringValue" in val_dict:
            data[key] = str(val_dict["stringValue"])
        elif "integerValue" in val_dict:
            data[key] = int(val_dict["integerValue"])
        elif "doubleValue" in val_dict:
            data[key] = float(val_dict["doubleValue"])
        elif "booleanValue" in val_dict:
            data[key] = bool(val_dict["booleanValue"])
        else:
            data[key] = list(val_dict.values())[0] if val_dict else ""
    return data


def build_firestore_fields(data):
    fields = {}
    for key, val in data.items():
        if isinstance(val, int):
            fields[key] = {"integerValue": str(val)}
        elif isinstance(val, float):
            fields[key] = {"doubleValue": val}
        elif isinstance(val, bool):
            fields[key] = {"booleanValue": val}
        else:
            fields[key] = {"stringValue": str(val)}
    return fields


class FirestoreRESTClient:
    def __init__(self):
        self.project_id = PROJECT_ID
        self.api_key = API_KEY

    def get_all(self, collection_name="stoklar"):
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection_name}?key={self.api_key}&pageSize=300"
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
        
        docs = res_data.get("documents", [])
        result = []
        for doc in docs:
            fields = doc.get("fields", {})
            parsed = parse_firestore_fields(fields)
            doc_id = doc.get("name", "").split("/")[-1]
            parsed["doc_id"] = doc_id
            result.append(parsed)
        return result

    def set_doc(self, collection_name, doc_id, data):
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection_name}/{doc_id}?key={self.api_key}"
        body = json.dumps({"fields": build_firestore_fields(data)}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PATCH")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def delete_doc(self, collection_name, doc_id):
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection_name}/{doc_id}?key={self.api_key}"
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="DELETE")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200


# --- MASAÜSTÜ ARAYÜZ SINIFI ---
class StokUygulamasi:
    def __init__(self, root):
        self.root = root
        self.root.title("Yedek Parça Stok Takip Sistemi")
        self.root.geometry("1100x690")
        self.root.configure(bg="#f4f6f9")

        self.root.protocol("WM_DELETE_WINDOW", self.uygulamayi_kapat)

        try:
            self.root.iconbitmap(dosya_yolu("app.ico"))
        except Exception:
            pass

        self.client = None
        self.tum_stoklar = []
        
        self.arayuz_olustur()
        self.baglantiyi_ve_verileri_baslat()
        
        # Telefon değişikliklerini anlık çekebilmek için 10 saniyede bir otomatik senkronizasyon başlatılır
        self.root.after(10000, self.otomatik_canli_senkronizasyon)

    def uygulamayi_kapat(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def baglantiyi_ve_verileri_baslat(self, sessiz=False):
        def arkaplan_islem():
            try:
                if not sessiz:
                    self.durum_guncelle("⏳ Veriler indiriliyor...", "#2980b9")
                
                if not self.client:
                    self.client = FirestoreRESTClient()

                self.tum_stoklar = self.client.get_all("stoklar")

                self.root.after(0, self.stok_listele)
                
                toplam = len(self.tum_stoklar)
                if not sessiz:
                    if toplam == 0:
                        self.durum_guncelle("ℹ️ Veritabanı bağlı fakat stok verisi yok.", "#e67e22")
                    else:
                        self.durum_guncelle(f"✅ Başarılı! Toplam {toplam} parça listelendi.", "#27ae60")

            except Exception as e:
                if not sessiz:
                    err_msg = str(e)
                    self.durum_guncelle("❌ Bağlantı Hatası!", "red")
                    self.root.after(0, lambda: messagebox.showerror("Veri Hatası", f"Hata Detayı:\n\n{err_msg}"))

        threading.Thread(target=arkaplan_islem, daemon=True).start()

    def otomatik_canli_senkronizasyon(self):
        """Telefondan yapılan güncellemeleri 10 saniyede bir arka planda sessizce çeker"""
        self.baglantiyi_ve_verileri_baslat(sessiz=True)
        self.root.after(10000, self.otomatik_canli_senkronizasyon)

    def durum_guncelle(self, metin, renk="#333333"):
        def guncelle():
            self.lbl_durum.config(text=metin, fg=renk)
        self.root.after(0, guncelle)

    def arayuz_olustur(self):
        baslik_frame = tk.Frame(self.root, bg="#2c3e50", pady=10)
        baslik_frame.pack(fill="x")
        tk.Label(baslik_frame, text="YEDEK PARÇA STOK TAKİP SİSTEMİ", font=("Arial", 16, "bold"), fg="white", bg="#2c3e50").pack()

        ust_bar = tk.Frame(self.root, bg="#f4f6f9", pady=10, padx=10)
        ust_bar.pack(fill="x")

        tk.Label(ust_bar, text="Arama:", font=("Arial", 10, "bold"), bg="#f4f6f9").pack(side="left", padx=5)
        self.ent_arama = tk.Entry(ust_bar, width=22, font=("Arial", 10))
        self.ent_arama.pack(side="left", padx=5)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.stok_listele())

        btn_ekle = tk.Button(ust_bar, text="+ Yeni Parça Ekle", bg="#27ae60", fg="white", font=("Arial", 9, "bold"), command=self.parca_ekle_penceresi)
        btn_ekle.pack(side="left", padx=10)

        btn_excel_yukle = tk.Button(ust_bar, text="📁 Excel'den Yükle", bg="#2980b9", fg="white", font=("Arial", 9), command=self.excel_yukle)
        btn_excel_yukle.pack(side="left", padx=5)

        btn_excel_rapor = tk.Button(ust_bar, text="📊 Excel Raporu Al", bg="#8e44ad", fg="white", font=("Arial", 9), command=self.excel_rapor_al)
        btn_excel_rapor.pack(side="left", padx=5)

        tablo_frame = tk.Frame(self.root, padx=10, pady=5)
        tablo_frame.pack(fill="both", expand=True)

        sutunlar = ("parca_kodu", "barkod_no", "parca_adi", "kategori", "miktar", "raf_konumu", "durum")
        self.tablo = ttk.Treeview(tablo_frame, columns=sutunlar, show="headings")
        
        self.tablo.heading("parca_kodu", text="Parça Kodu")
        self.tablo.heading("barkod_no", text="Barkod / QR No")
        self.tablo.heading("parca_adi", text="Parça Adı")
        self.tablo.heading("kategori", text="Kategori")
        self.tablo.heading("miktar", text="Miktar")
        self.tablo.heading("raf_konumu", text="Raf Konumu")
        self.tablo.heading("durum", text="Stok Durumu")

        self.tablo.column("parca_kodu", width=110, anchor="center")
        self.tablo.column("barkod_no", width=120, anchor="center")
        self.tablo.column("parca_adi", width=220)
        self.tablo.column("kategori", width=110, anchor="center")
        self.tablo.column("miktar", width=80, anchor="center")
        self.tablo.column("raf_konumu", width=110, anchor="center")
        self.tablo.column("durum", width=120, anchor="center")

        self.tablo.pack(fill="both", expand=True)
        self.tablo.bind("<Button-3>", self.sag_tik_menusu_goster)

        alt_bar = tk.Frame(self.root, bg="#f4f6f9", pady=5, padx=10)
        alt_bar.pack(fill="x")

        tk.Button(alt_bar, text="➕ Stok Artır", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=lambda: self.stok_islem_penceresi("arttir")).pack(side="left", padx=5)
        tk.Button(alt_bar, text="➖ Stok Azalt", bg="#c0392b", fg="white", font=("Arial", 10, "bold"), command=lambda: self.stok_islem_penceresi("azalt")).pack(side="left", padx=5)
        tk.Button(alt_bar, text="✏️ Düzenle", bg="#2980b9", fg="white", font=("Arial", 10, "bold"), command=self.parca_duzenle_penceresi).pack(side="left", padx=5)
        tk.Button(alt_bar, text="🖨️ QR Etiket Yazdır", bg="#e67e22", fg="white", font=("Arial", 10, "bold"), command=self.qr_etiket_penceresi).pack(side="left", padx=10)
        tk.Button(alt_bar, text="🔄 Yenile", bg="#7f8c8d", fg="white", font=("Arial", 10), command=self.baglantiyi_ve_verileri_baslat).pack(side="right", padx=5)

        durum_bar = tk.Frame(self.root, bg="#e2e8f0", pady=3, padx=10)
        durum_bar.pack(fill="x", side="bottom")
        self.lbl_durum = tk.Label(durum_bar, text="Sistem Başlatılıyor...", font=("Arial", 9), bg="#e2e8f0", fg="#333333", anchor="w")
        self.lbl_durum.pack(fill="x")

    def sag_tik_menusu_goster(self, event):
        row_id = self.tablo.identify_row(event.y)
        if row_id:
            self.tablo.selection_set(row_id)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="🖨️ QR Etiket Yazdır", command=self.qr_etiket_penceresi)
            menu.add_separator()
            menu.add_command(label="✏️ Parça Bilgilerini Düzenle", command=self.parca_duzenle_penceresi)
            menu.add_command(label="🏷️ Barkod / Raf Düzenle", command=self.barkod_guncelle_penceresi)
            menu.add_separator()
            menu.add_command(label="➕ Stok Artır", command=lambda: self.stok_islem_penceresi("arttir"))
            menu.add_command(label="➖ Stok Azalt", command=lambda: self.stok_islem_penceresi("azalt"))
            menu.add_separator()
            menu.add_command(label="🗑️ Parçayı Sil", command=self.parca_sil)
            menu.post(event.x_root, event.y_root)

    def stok_listele(self):
        for row in self.tablo.get_children():
            self.tablo.delete(row)

        arama = self.ent_arama.get().strip().lower()

        for item in self.tum_stoklar:
            kod = str(item.get("parca_kodu") or item.get("doc_id") or "-")
            barkod = str(item.get("barkod_no") or item.get("barkod") or kod)
            ad = str(item.get("parca_adi") or item.get("ad") or "-")
            kat = str(item.get("kategori", "Genel"))
            
            # Telefon ve PC veri isimlerinin ortak uyumu (stok / miktar)
            miktar = item.get("miktar") if item.get("miktar") is not None else item.get("stok", 0)
            miktar = int(miktar)
            
            kritik = item.get("kritik_seviye") if item.get("kritik_seviye") is not None else item.get("kritik_stok", 5)
            kritik = int(kritik)
            
            raf = str(item.get("raf_konumu") or item.get("raf") or "Belirtilmedi")

            if arama:
                if (arama not in kod.lower() and arama not in ad.lower() and arama not in barkod.lower()):
                    continue

            durum = "⚠️ KRİTİK" if miktar <= kritik else "OK"
            self.tablo.insert("", "end", values=(kod, barkod, ad, kat, miktar, raf, durum))

    def qr_etiket_penceresi(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen bir parça seçin!")
            return

        item_values = self.tablo.item(secili[0])["values"]
        parca_kodu = str(item_values[0])
        barkod = str(item_values[1])
        parca_adi = str(item_values[2])
        raf = str(item_values[5])

        pencere = tk.Toplevel(self.root)
        pencere.title(f"QR Etiket: {parca_adi}")
        pencere.geometry("380x420")

        tk.Label(pencere, text=f"{parca_adi}\nKod: {parca_kodu} | Raf: {raf}", font=("Arial", 10, "bold")).pack(pady=10)

        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(barkod)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_tk = ImageTk.PhotoImage(img)
        lbl_img = tk.Label(pencere, image=img_tk)
        lbl_img.image = img_tk
        lbl_img.pack(pady=5)

        def resmi_kaydet():
            dosya = filedialog.asksaveasfilename(defaultextension=".png", initialfile=f"QR_{parca_kodu}.png", filetypes=[("PNG Görseli", "*.png")])
            if dosya:
                img.save(dosya)
                messagebox.showinfo("Başarılı", f"QR etiket kaydedildi:\n{dosya}")

        tk.Button(pencere, text="💾 QR Etiket Görselini Kaydet", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=resmi_kaydet).pack(pady=15)

    def parca_duzenle_penceresi(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek istediğiniz parçayı seçin!")
            return

        item_values = self.tablo.item(secili[0])["values"]
        parca_kodu = str(item_values[0])
        mevcut_data = next((x for x in self.tum_stoklar if str(x.get("parca_kodu") or x.get("doc_id")) == parca_kodu), None)
        if not mevcut_data: return

        pencere = tk.Toplevel(self.root)
        pencere.title(f"Parça Düzenle: {parca_kodu}")
        pencere.geometry("380x280")

        tk.Label(pencere, text=f"Parça Kodu: {parca_kodu}", font=("Arial", 10, "bold")).pack(pady=10)
        tk.Label(pencere, text="Parça Adı:").pack()
        ent_ad = tk.Entry(pencere, width=30)
        ent_ad.insert(0, mevcut_data.get("parca_adi") or mevcut_data.get("ad") or "")
        ent_ad.pack(pady=5)

        tk.Label(pencere, text="Kategori:").pack()
        ent_kat = tk.Entry(pencere, width=30)
        ent_kat.insert(0, mevcut_data.get("kategori", "Genel"))
        ent_kat.pack(pady=5)

        tk.Label(pencere, text="Kritik Stok Seviyesi:").pack()
        ent_kritik = tk.Entry(pencere, width=30)
        ent_kritik.insert(0, str(mevcut_data.get("kritik_seviye") or mevcut_data.get("kritik_stok") or 5))
        ent_kritik.pack(pady=5)

        def kaydet():
            yeni_ad = ent_ad.get().strip()
            yeni_kat = ent_kat.get().strip() or "Genel"
            try:
                yeni_kritik = int(ent_kritik.get().strip())
            except ValueError:
                messagebox.showerror("Hata", "Geçerli bir kritik seviye girin!")
                return

            if not yeni_ad:
                messagebox.showerror("Hata", "Parça Adı boş olamaz!")
                return

            try:
                mevcut_data["parca_adi"] = yeni_ad
                mevcut_data["ad"] = yeni_ad
                mevcut_data["kategori"] = yeni_kat
                mevcut_data["kritik_seviye"] = yeni_kritik
                mevcut_data["kritik_stok"] = yeni_kritik

                self.client.set_doc("stoklar", parca_kodu, mevcut_data)
                messagebox.showinfo("Başarılı", "Güncellendi.")
                pencere.destroy()
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Güncelleme hatası: {e}")

        tk.Button(pencere, text="Kaydet", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=kaydet).pack(pady=15)

    def parca_sil(self):
        secili = self.tablo.selection()
        if not secili: return
        item_values = self.tablo.item(secili[0])["values"]
        parca_kodu = str(item_values[0])
        parca_adi = str(item_values[2])

        if messagebox.askyesno("Silme Onayı", f"'{parca_adi}' silinecek, onaylıyor musunuz?"):
            try:
                self.client.delete_doc("stoklar", parca_kodu)
                messagebox.showinfo("Başarılı", "Silindi.")
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Silme hatası: {e}")

    def parca_ekle_penceresi(self):
        pencere = tk.Toplevel(self.root)
        pencere.title("Yeni Parça Ekle")
        pencere.geometry("350x400")

        fields = [("Parça Kodu:", "kod"), ("Barkod / QR No:", "barkod"), ("Parça Adı:", "ad"), 
                  ("Kategori:", "kat"), ("Başlangıç Miktarı:", "miktar"), 
                  ("Kritik Stok Seviyesi:", "kritik"), ("Raf Konumu:", "raf")]
        
        entries = {}
        for i, (label_text, key) in enumerate(fields):
            tk.Label(pencere, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            ent = tk.Entry(pencere, width=25)
            ent.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = ent

        def kaydet():
            kod = entries["kod"].get().strip()
            ad = entries["ad"].get().strip()
            if not kod or not ad:
                messagebox.showerror("Hata", "Kodu ve Adı boş bırakmayın!")
                return
            
            m_val = int(entries["miktar"].get().strip() or 0)
            k_val = int(entries["kritik"].get().strip() or 5)
            barkod_val = entries["barkod"].get().strip() or kod
            raf_val = entries["raf"].get().strip() or "Belirtilmedi"
            kat_val = entries["kat"].get().strip() or "Genel"

            data = {
                "parca_kodu": kod,
                "barkod_no": barkod_val,
                "barkod": barkod_val,
                "parca_adi": ad,
                "ad": ad,
                "kategori": kat_val,
                "miktar": m_val,
                "stok": m_val,
                "kritik_seviye": k_val,
                "kritik_stok": k_val,
                "raf_konumu": raf_val,
                "raf": raf_val
            }

            try:
                self.client.set_doc("stoklar", kod, data)
                messagebox.showinfo("Başarılı", "Kaydedildi.")
                pencere.destroy()
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Hata: {e}")

        tk.Button(pencere, text="Kaydet", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=kaydet).grid(row=len(fields), column=0, columnspan=2, pady=15)

    def barkod_guncelle_penceresi(self):
        secili = self.tablo.selection()
        if not secili: return
        item_values = self.tablo.item(secili[0])["values"]
        parca_kodu = str(item_values[0])
        mevcut_data = next((x for x in self.tum_stoklar if str(x.get("parca_kodu") or x.get("doc_id")) == parca_kodu), None)
        if not mevcut_data: return

        pencere = tk.Toplevel(self.root)
        pencere.title("Barkod ve Raf Düzenle")
        pencere.geometry("380x250")

        parca_adi_val = mevcut_data.get('parca_adi') or mevcut_data.get('ad')
        tk.Label(pencere, text=f"Parça: {parca_adi_val}\nKod: {parca_kodu}", font=("Arial", 9, "bold")).pack(pady=10)
        tk.Label(pencere, text="Barkod / QR No:").pack()
        ent_barkod = tk.Entry(pencere, width=28)
        ent_barkod.insert(0, mevcut_data.get("barkod_no") or mevcut_data.get("barkod") or parca_kodu)
        ent_barkod.pack(pady=5)

        tk.Label(pencere, text="Raf Konumu:").pack(pady=(5, 0))
        ent_raf = tk.Entry(pencere, width=28)
        ent_raf.insert(0, mevcut_data.get("raf_konumu") or mevcut_data.get("raf") or "")
        ent_raf.pack(pady=5)

        def kaydet():
            try:
                b_val = ent_barkod.get().strip() or parca_kodu
                r_val = ent_raf.get().strip() or "Belirtilmedi"
                
                mevcut_data["barkod_no"] = b_val
                mevcut_data["barkod"] = b_val
                mevcut_data["raf_konumu"] = r_val
                mevcut_data["raf"] = r_val

                self.client.set_doc("stoklar", parca_kodu, mevcut_data)
                messagebox.showinfo("Başarılı", "Güncellendi.")
                pencere.destroy()
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Hata: {e}")

        tk.Button(pencere, text="Kaydet", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=kaydet).pack(pady=15)

    def stok_islem_penceresi(self, islem_tipi):
        secili = self.tablo.selection()
        if not secili: return
        item_values = self.tablo.item(secili[0])["values"]
        parca_kodu = str(item_values[0])
        mevcut_data = next((x for x in self.tum_stoklar if str(x.get("parca_kodu") or x.get("doc_id")) == parca_kodu), None)
        if not mevcut_data: return

        parca_adi = mevcut_data.get("parca_adi") or mevcut_data.get("ad")
        mevcut_miktar = mevcut_data.get("miktar") if mevcut_data.get("miktar") is not None else mevcut_data.get("stok", 0)
        mevcut_miktar = int(mevcut_miktar)

        pencere = tk.Toplevel(self.root)
        pencere.title(f"Stok {'Artır' if islem_tipi == 'arttir' else 'Azalt'}")
        pencere.geometry("300x180")

        tk.Label(pencere, text=f"Parça: {parca_adi}", font=("Arial", 9, "bold")).pack(pady=10)
        tk.Label(pencere, text="Miktar:").pack()
        ent_miktar = tk.Entry(pencere, width=15)
        ent_miktar.pack(pady=5)

        def uygula():
            try:
                m = int(ent_miktar.get().strip())
                if m <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Hata", "Geçerli miktar girin!")
                return

            if islem_tipi == "azalt" and mevcut_miktar < m:
                messagebox.showerror("Hata", "Yetersiz stok!")
                return

            yeni_miktar = mevcut_miktar + m if islem_tipi == "arttir" else mevcut_miktar - m

            try:
                mevcut_data["miktar"] = yeni_miktar
                mevcut_data["stok"] = yeni_miktar
                
                self.client.set_doc("stoklar", parca_kodu, mevcut_data)
                
                hareket_id = datetime.now().strftime("%Y%m%d%H%M%S")
                self.client.set_doc("stok_hareketleri", hareket_id, {
                    "parca_kodu": parca_kodu,
                    "islem_tipi": "GİRİŞ" if islem_tipi == "arttir" else "ÇIKIŞ",
                    "miktar": m,
                    "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "aciklama": "Masaüstü İşlemi"
                })

                messagebox.showinfo("Başarılı", "Stok güncellendi.")
                pencere.destroy()
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Hata: {e}")

        tk.Button(pencere, text="Onayla", bg="#27ae60" if islem_tipi == "arttir" else "#c0392b", fg="white", font=("Arial", 10, "bold"), command=uygula).pack(pady=10)

    def excel_yukle(self):
        dosya = filedialog.askopenfilename(filetypes=[("Excel Dosyaları", "*.xlsx")])
        if dosya:
            try:
                df = pd.read_excel(dosya)
                eklenen = 0
                for _, row in df.iterrows():
                    kod = str(row['parca_kodu'])
                    ad = str(row['parca_adi'])
                    m_val = int(row.get('miktar', 0))
                    k_val = int(row.get('kritik_seviye', 5))
                    b_val = str(row.get('barkod_no', kod))
                    r_val = str(row.get('raf_konumu', 'Belirtilmedi'))
                    kat_val = str(row.get('kategori', 'Genel'))

                    data = {
                        "parca_kodu": kod,
                        "barkod_no": b_val,
                        "barkod": b_val,
                        "parca_adi": ad,
                        "ad": ad,
                        "kategori": kat_val,
                        "miktar": m_val,
                        "stok": m_val,
                        "kritik_seviye": k_val,
                        "kritik_stok": k_val,
                        "raf_konumu": r_val,
                        "raf": r_val
                    }
                    self.client.set_doc("stoklar", kod, data)
                    eklenen += 1
                messagebox.showinfo("Başarılı", f"{eklenen} parça aktarıldı.")
                self.baglantiyi_ve_verileri_baslat()
            except Exception as e:
                messagebox.showerror("Hata", f"Excel hatası: {e}")

    def excel_rapor_al(self):
        try:
            df = pd.DataFrame(self.tum_stoklar)
            dosya = f"Stok_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            df.to_excel(dosya, index=False)
            messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{os.path.abspath(dosya)}")
        except Exception as e:
            messagebox.showerror("Hata", f"Rapor hatası: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = StokUygulamasi(root)
    root.mainloop()
