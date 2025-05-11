import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
from ctypes import windll
import pyodbc
from dotenv import load_dotenv
import os
import google.generativeai as genai
import threading
import json
import logging

# DPI ayarları
windll.shcore.SetProcessDpiAwareness(1)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


def get_db_connection():
    server = r'DESKTOP-DMG34IC\SQLEXPRESS'
    database = 'DERSHANE'
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'Trusted_Connection=yes;'
    )


def save_to_json(data, filename='quiz_results.json'):
    # StringVar gibi serileştirilemeyen objeleri dönüştür
    def serialize(obj):
        if isinstance(obj, tk.StringVar):
            return obj.get()
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize(i) for i in obj]
        return obj

    serializable_data = serialize(data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=4)


# Temalar
THEMES = {
    "light": {
        "bg": "#f9f9ff",
        "fg": "#003366",
        "accent": "#0055cc",
        "button_bg": "#e6f0ff",
        "button_fg": "#003366",
        "button_hover": "#ccf2e6",
        "optik_bg": "#f0f4ff",
        "highlight": "#dce9ff"
    },
    "dark": {
        "bg": "#121212",
        "fg": "#ffffff",
        "accent": "#00cc66",
        "button_bg": "#1e1e1e",
        "button_fg": "#00cc66",
        "button_hover": "#145c33",
        "optik_bg": "#1c1c1c",
        "highlight": "#2d2d2d"
    }
}


class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.current = "light"
        self._style = ttk.Style()
        self._configure_base_styles()
        self._is_generating_questions = False  # Soru oluşturma durumunu takip etmek için

    def _configure_base_styles(self):
        """Temel stil ayarlarını yapılandır"""
        self._style.configure(".", font=('Segoe UI', 10))
        self._style.configure("TFrame", background=THEMES[self.current]['bg'])
        self._style.configure("TLabel",
                              background=THEMES[self.current]['bg'],
                              foreground=THEMES[self.current]['fg'],
                              font=('Segoe UI', 10))

    def apply(self, theme_name: str) -> None:
        """Tema değişikliğini uygula"""
        if theme_name not in THEMES:
            logging.error(f"Geçersiz tema: {theme_name}")
            return

        try:
            # Soru oluşturma durumunu kontrol et
            if hasattr(self.app, 'generating') and self.app.generating:
                self._is_generating_questions = True
                logging.info("Soru oluşturma sırasında tema değişikliği yapılıyor")
                return

            self.current = theme_name
            theme = THEMES[theme_name]

            # Ana pencere temasını güncelle
            self.app.root.configure(bg=theme['bg'])

            # Temel stilleri güncelle
            self._configure_base_styles()

            # Buton stilleri
            self._style.configure("TButton",
                                  background=theme['button_bg'],
                                  foreground=theme['button_fg'],
                                  padding=8,
                                  relief="flat",
                                  font=('Segoe UI', 10),
                                  borderwidth=0)

            self._style.map("TButton",
                            background=[("active", theme['accent'])],
                            foreground=[("active", 'white')])

            # Radio buton stilleri
            active_bg = '#145c33' if theme_name == 'dark' else theme['highlight']
            active_fg = 'white' if theme_name == 'dark' else theme['fg']

            self._style.configure('Question.TRadiobutton',
                                  background=theme['bg'],
                                  foreground=theme['fg'],
                                  font=('Arial', 10),
                                  relief='flat',
                                  padding=3)

            self._style.map('Question.TRadiobutton',
                            background=[
                                ('active', active_bg),
                                ('selected', theme['highlight'])
                            ],
                            foreground=[
                                ('active', active_fg),
                                ('selected', theme['accent'])
                            ])

            # Diğer widget stilleri
            self._style.configure("TLabelframe",
                                  background=theme['bg'],
                                  foreground=theme['fg'])

            self._style.configure("TLabelframe.Label",
                                  background=theme['bg'],
                                  foreground=theme['accent'])

            self._style.configure('TCombobox',
                                  fieldbackground=theme['bg'],
                                  foreground=theme['fg'],
                                  background=theme['bg'])

            self._style.configure('TEntry',
                                  fieldbackground=theme['bg'],
                                  foreground=theme['fg'],
                                  insertcolor=theme['fg'])

            self._style.configure('Optik.TFrame', background=theme['optik_bg'])
            self._style.configure('Optik.TLabel',
                                  background=theme['accent'],
                                  foreground=theme['bg'])

            # Mevcut ekranı yenile
            if hasattr(self.app, 'current_screen'):
                self._refresh_current_screen()

            # Özel stilleri güncelle
            self.app.configure_styles()

            logging.info(f"Tema başarıyla değiştirildi: {theme_name}")

        except Exception as e:
            logging.error(f"Tema değiştirme hatası: {str(e)}")
            messagebox.showerror("Hata", "Tema değiştirilirken bir hata oluştu.")

    def _refresh_current_screen(self) -> None:
        """Mevcut ekranı yenile"""
        try:
            # Eğer soru oluşturuluyorsa ekranı yenileme
            if self._is_generating_questions:
                return

            if self.app.current_screen == 'results':
                if self.app.mode == 'test':
                    self.app.show_test_results()
                else:
                    self.app.show_results()
            elif self.app.current_screen == 'exam':
                self.app.show_exam_interface()
            elif self.app.current_screen == 'main':
                self.app.show_main_menu()
            elif self.app.current_screen == 'test' and self.app.test_questions:
                self.app.show_test_question_page()
            elif self.app.current_screen == 'test':
                self.app.show_test_setup()

        except Exception as e:
            logging.error(f"Ekran yenileme hatası: {str(e)}")
            messagebox.showerror("Hata", "Ekran yenilenirken bir hata oluştu.")

    def set_generating_state(self, is_generating: bool) -> None:
        """Soru oluşturma durumunu ayarla"""
        self._is_generating_questions = is_generating


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, theme_name="light", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.theme_name = theme_name

        # Canvas ve scrollbar oluştur
        self.canvas = tk.Canvas(self,
                                highlightthickness=0,
                                bg=THEMES[theme_name]['bg'])
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)

        # Inner frame oluştur
        self.inner = ttk.Frame(self.canvas, style='Custom.TFrame')

        # Canvas'ı yapılandır
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Widget'ları yerleştir
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        # Inner frame'i canvas'a ekle
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        # Event binding'leri
        self.inner.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # Tema değişikliği için event binding
        self.bind('<<ThemeChanged>>', self._on_theme_change)

    def _on_frame_configure(self, event=None):
        """Inner frame boyutu değiştiğinde scroll bölgesini güncelle"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        """Canvas boyutu değiştiğinde inner frame genişliğini güncelle"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_mousewheel(self, event):
        """Mouse tekerleği ile kaydırma"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_theme_change(self, event=None):
        """Tema değiştiğinde canvas arkaplan rengini güncelle"""
        self.canvas.configure(bg=THEMES[self.theme_name]['bg'])

    def update_theme(self, theme_name):
        """Tema değişikliğini uygula"""
        if self.winfo_exists():  # Frame hala mevcutsa
            self.theme_name = theme_name
            self.canvas.configure(bg=THEMES[theme_name]['bg'])
            self.inner.configure(style='Custom.TFrame')


class QuestionApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Star Soru Çözme Alanı')
        self.root.geometry('1366x768')
        self.style = ttk.Style()
        self.theme_manager = ThemeManager(self)
        ttk.Style().theme_use('clam')
        self.theme_manager.apply("light")

        self.conn = get_db_connection()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.font = Font(family='Segoe UI', size=12)
        self.title_font = Font(family='Segoe UI', size=18, weight='bold')
        self.mode = None
        self.test_type = None
        self.modules = []
        self.current_module = 0
        self.selected_answers = {}
        self.timer_label = None
        self.remaining_sec = 0
        self.sf = None

        self.cat_var = tk.StringVar()
        self.ders_var = tk.StringVar()
        self.konu_var = tk.StringVar()
        self.num_entry = None
        self.test_questions = []
        self.test_selected_answers = {}

        self.style.configure('Custom.TFrame',
                             background=THEMES[self.theme_manager.current]['bg'])
        self.style.configure('Custom.TLabel',
                             background=THEMES[self.theme_manager.current]['bg'],
                             foreground=THEMES[self.theme_manager.current]['fg'])
        self.create_menu()
        self.show_main_menu()

    def on_close(self):
        if self.conn: self.conn.close()
        self.root.destroy()

    def refresh_current_screen(self):
        """Mevcut ekranı yenile"""
        # Sadece widget'ların stillerini güncelle
        theme = THEMES[self.theme_manager.current]

        # Tüm widget'ları güncelle
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                widget.configure(style='Custom.TFrame')
            elif isinstance(widget, tk.Label):
                widget.configure(bg=THEMES[self.theme_manager.current]['bg'],
                                 fg=THEMES[self.theme_manager.current]['fg'])
            elif isinstance(widget, ttk.Button):
                widget.configure(style='TButton')
            elif isinstance(widget, ttk.Radiobutton):
                widget.configure(style='Question.TRadiobutton')
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style='TCombobox')
            elif isinstance(widget, ttk.Entry):
                widget.configure(style='TEntry')
            elif isinstance(widget, ttk.Labelframe):
                widget.configure(style='TLabelframe')

        # ScrollableFrame'i güncelle
        if hasattr(self, 'sf') and self.sf:
            self.sf.update_theme(self.theme_manager.current)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        theme_submenu = tk.Menu(settings_menu, tearoff=0)
        theme_submenu.add_command(label="Açık Tema (Lacivert)", command=lambda: self.theme_manager.apply('light'))
        theme_submenu.add_command(label="Koyu Tema (Siyah/Yeşil)", command=lambda: self.theme_manager.apply('dark'))
        settings_menu.add_cascade(label="Tema Ayarları", menu=theme_submenu)
        menu_bar.add_cascade(label="Ayarlar", menu=settings_menu)
        self.root.config(menu=menu_bar)

    def clear(self):
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Menu):
                w.destroy()

    def configure_styles(self):
        style = ttk.Style()
        theme = THEMES[self.theme_manager.current]

        # Mevcut stil ayarlarına ek olarak:
        style.configure('Custom.TFrame',
                        background=theme['bg'])
        style.configure('Custom.TLabel',
                        background=theme['bg'],
                        foreground=theme['fg'])

        style.configure('Optik.TRadiobutton',
                        width=3,
                        padding=5,
                        relief='flat',
                        font=('Arial', 9),
                        background=theme['optik_bg'],
                        foreground=theme['accent'])

        style.configure('Selected.TRadiobutton',
                        background=theme['highlight'],
                        relief='solid',
                        borderwidth=1)

        style.map('Optik.TRadiobutton',
                  background=[('active', theme['highlight'])],
                  foreground=[('selected', theme['accent']), ('!selected', theme['fg'])],
                  indicatorcolor=[('selected', theme['accent']), ('!selected', theme['fg'])])
        style.configure('Question.TRadioButton',
                        background=theme['bg'],
                        foreground=theme['fg'],
                        font=('Arial', 10))
        self.style.configure('Test.TRadiobutton',
                             background=THEMES[self.theme_manager.current]['bg'],
                             foreground=THEMES[self.theme_manager.current]['fg'],
                             font=('Arial', 10))

        self.style.map('Test.TRadiobutton',
                       background=[('active', THEMES[self.theme_manager.current]['highlight'])],
                       foreground=[('active', THEMES[self.theme_manager.current]['accent'])])

    def configure_mode(self, mode):
        self.mode = mode
        if mode == 'test':
            self.show_category_selection()
        else:
            self.show_exam_setup()

    def show_main_menu(self):
        self.clear()
        self.current_screen = 'main'
        ttk.Label(self.root, text='Star Soru Çözme Alanı', font=self.title_font).pack(pady=40)
        frame = ttk.Frame(self.root)
        frame.pack(pady=20)
        ttk.Button(frame, text='E-Sınav', command=lambda: self.configure_mode('exam'), width=20).grid(row=0, column=0,
                                                                                                      padx=10)
        ttk.Button(frame, text='Test', command=lambda: self.configure_mode('test'), width=20).grid(row=0, column=1,
                                                                                                   padx=10)

    def show_category_selection(self):
        self.clear()
        ttk.Label(self.root, text='Kategori Seçiniz (TYT/AYT)', font=self.title_font).pack(pady=20)
        self.cat_var = tk.StringVar()
        cat_cb = ttk.Combobox(self.root, textvariable=self.cat_var, state='readonly', values=self.get_categories())
        cat_cb.pack()
        ttk.Button(self.root, text='İleri', command=self.show_ders_selection).pack(pady=10)

    def get_categories(self):
        cur = self.conn.cursor()
        cur.execute('SELECT Adi FROM SinavKategorileri')
        return [row[0] for row in cur]

    def show_ders_selection(self):
        cat = self.cat_var.get()
        if not cat: return messagebox.showerror('Hata', 'Kategori seçin')
        self.test_type = cat
        self.clear()
        ttk.Label(self.root, text=f'{cat}: Ders Seçiniz', font=self.title_font).pack(pady=20)
        self.ders_var = tk.StringVar()
        ders_cb = ttk.Combobox(self.root, textvariable=self.ders_var, state='readonly', values=self.get_dersler(cat))
        ders_cb.pack()
        ttk.Button(self.root, text='İleri', command=self.show_konu_selection).pack(pady=10)

    def get_dersler(self, kategori):
        cur = self.conn.cursor()
        cur.execute(
            'SELECT d.Adi FROM SinavDersleri d JOIN SinavKategorileri k ON d.SinavKategoriId=k.Id WHERE k.Adi=?',
            kategori
        )
        return [r[0] for r in cur]

    def show_konu_selection(self):
        ders = self.ders_var.get()
        if not ders:
            messagebox.showerror('Hata', 'Ders seçin')
            return

        self.selected_ders = ders
        self.clear()
        ttk.Label(self.root, text=f'{ders}: Konu Seçiniz', font=self.title_font).pack(pady=20)

        self.konu_var = tk.StringVar()
        konu_cb = ttk.Combobox(self.root, textvariable=self.konu_var, state='readonly', values=self.get_konular(ders))
        konu_cb.pack()

        ttk.Label(self.root, text='Soru Sayısı:').pack(pady=5)
        self.num_entry = ttk.Entry(self.root)
        self.num_entry.insert(0, '4')
        self.num_entry.pack()

        ttk.Button(self.root, text='Soruları Getir', command=self.generate_questions).pack(pady=10)

    def get_konular(self, ders):
        cur = self.conn.cursor()
        cur.execute(
            'SELECT k.Adi FROM SinavDersKonulari k JOIN SinavDersleri d ON k.SinavDersId=d.Id WHERE d.Adi=?', ders
        )
        return [r[0] for r in cur]

    def show_test_question_page(self):
        self.clear()
        self.current_screen = 'test'

        # Ana frame oluştur
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # Üst çubuk
        top = ttk.Frame(main_frame)
        top.pack(fill='x', padx=10, pady=5)

        # Sınavı tamamla butonu
        complete_btn = ttk.Button(top, text="Testi Tamamla", command=self.show_test_results)
        complete_btn.pack(side='right', padx=10)

        # Soru alanı ve Optik Form için container
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True)

        # Soru alanı (Scrollable)
        self.sf = ScrollableFrame(content_frame, theme_name=self.theme_manager.current)
        self.sf.pack(side='left', fill='both', expand=True)

        # Optik Form (Sağda)
        opt_frame = ttk.Frame(content_frame, style='Optik.TFrame')
        opt_frame.pack(side='right', fill='y', padx=10, pady=10)

        ttk.Label(opt_frame, text="Optik Form", style='Optik.TLabel').pack(pady=5)

        # Optik formu oluştur
        self.test_optik_circles = []
        for i in range(len(self.test_questions)):
            cell_frame = ttk.Frame(opt_frame, style='Optik.TFrame')
            cell_frame.pack(pady=2, fill='x')

            ttk.Label(cell_frame, text=str(i + 1), width=3).pack(side='left', padx=5)
            circles_frame = ttk.Frame(cell_frame)
            circles_frame.pack(side='left', fill='x', expand=True)

            circles = []
            for opt in ['A', 'B', 'C', 'D']:
                rb = ttk.Radiobutton(
                    circles_frame,
                    text=opt,
                    style='Optik.TRadiobutton',
                    value=opt,
                    variable=self.test_selected_answers[i],
                    command=lambda idx=i: self.update_test_optic(idx)
                )
                rb.pack(side='left', expand=True)
                circles.append(rb)
            self.test_optik_circles.append(circles)
            cell_frame.bind('<Button-1>', lambda e, idx=i: self.scroll_to_test_question(idx))

        # Soruları göster
        for idx, q in enumerate(self.test_questions):
            fr = ttk.LabelFrame(self.sf.inner, text=f"Soru {idx + 1}", padding=10)
            fr.pack(fill='x', pady=5)

            # Soru metni
            ttk.Label(fr, text=q.get('question', 'Soru metni yok'), wraplength=800).pack(anchor='w', pady=5)

            # Şıklar
            options = q.get('options', {})
            for opt in ['A', 'B', 'C', 'D']:
                if opt in options:
                    ttk.Radiobutton(
                        fr,
                        text=f"{opt}) {options[opt]}",
                        value=opt,
                        variable=self.test_selected_answers[idx],
                        command=lambda qidx=idx: self.update_test_optic(qidx),
                        style='Question.TRadiobutton'
                    ).pack(anchor='w')

    def update_test_optic(self, idx):
        """Test modülü için optik form güncelleme"""
        selected = self.test_selected_answers[idx].get()
        for i, opt in enumerate(['A', 'B', 'C', 'D']):
            btn = self.test_optik_circles[idx][i]
            if opt == selected:
                btn.state(['selected'])
            else:
                btn.state(['!selected'])

    def scroll_to_test_question(self, idx):
        """Test modülü için soruya kaydırma"""
        if hasattr(self, 'sf') and self.sf:
            self.sf.canvas.yview_moveto(idx / len(self.test_questions))


    def generate_questions(self):
        self.current_screen = 'test'
        """Soruları oluştur"""
        self.generating = True
        self.theme_manager.set_generating_state(True)  # Tema yöneticisine soru oluşturma durumunu bildir
        self.test_selected_answers = {}

        try:
            self.num_questions = int(self.num_entry.get())
        except:
            self.num_questions = 4

        # Test modülü için özel işlemler
        if self.mode == 'test':
            if not hasattr(self, 'selected_konu'):
                self.selected_konu = self.konu_var.get()

            if not self.selected_konu:
                messagebox.showerror('Hata', 'Lütfen bir konu seçin')
                self.generating = False
                self.theme_manager.set_generating_state(False)
                return

            prompt = (
                f"{self.test_type} {self.selected_ders} "
                f"dersinin {self.selected_konu} konusundan {self.num_questions} adet test sorusu üret. "
                "Her soru şu formatta olsun:\n\n"
                "Soru 1: [soru metni]\nA) [şık A]\nB) [şık B]\nC) [şık C]\nD) [şık D]\n"
                "Cevap: [doğru şık]\nAçıklama: [açıklama metni]\n\nLütfen bu formata kesinlikle uyun!"
            )

            try:
                # Yükleniyor mesajı göster
                self.clear()
                ttk.Label(self.root, text='Sorular oluşturuluyor, lütfen bekleyin...',
                          font=self.title_font).pack(pady=200)
                self.root.update()

                res = model.generate_content(prompt)
                self.test_questions = self.parse_ai_questions(res.text)

                self.test_selected_answers = {}
                for idx, q in enumerate(self.test_questions):
                    self.test_selected_answers[idx] = tk.StringVar(value="")

                self.show_test_question_page()

                # Her soru için bir StringVar oluştur
                self.test_selected_answers = {}
                for idx in range(len(self.test_questions)):
                    self.test_selected_answers[idx] = tk.StringVar(value="")

                # Sonuçları kaydet
                save_to_json({
                    'mode': self.mode,
                    'kategori': self.test_type,
                    'questions': self.test_questions
                })

                # Test soru sayfasına git
                self.show_test_question_page()
                return

            except Exception as e:
                logging.error(f"Test soruları oluşturulurken hata: {str(e)}")
                messagebox.showerror("Hata", "Test soruları oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.")
                self.show_main_menu()
                return
            finally:
                self.generating = False
                self.theme_manager.set_generating_state(False)


    def show_test_setup(self):
        self.clear()
        self.current_screen = 'test'
        self.mode = 'test'  # Test modunu açıkça belirt

        ttk.Label(self.root, text='Test Modu: Kategori ve Konu Seçimi', font=self.title_font).pack(pady=20)

        # Kategori seçimi
        ttk.Label(self.root, text='Kategori Seçiniz (TYT/AYT)', font=self.font).pack(pady=10)
        self.cat_var = tk.StringVar()
        cat_cb = ttk.Combobox(self.root, textvariable=self.cat_var, state='readonly', values=self.get_categories())
        cat_cb.pack()

        # İleri butonu
        ttk.Button(self.root, text='İleri', command=self.show_ders_selection).pack(pady=10)

    def show_exam_setup(self):
        self.clear()
        self.current_screen = 'results'
        ttk.Label(self.root, text='E-Sınav Modu: TYT/AYT Seçiniz', font=self.title_font).pack(pady=20)
        frame = ttk.Frame(self.root)
        frame.pack()
        ttk.Button(frame, text='TYT', command=lambda: self.start_exam('TYT'), width=20).grid(row=0, column=0, padx=10)
        ttk.Button(frame, text='AYT', command=lambda: self.start_exam('AYT'), width=20).grid(row=0, column=1, padx=10)

    def show_test_results(self):
        self.clear()
        self.current_screen = 'results'

        # Başlık
        title_frame = ttk.Frame(self.root, style='Custom.TFrame')
        title_frame.pack(fill='x', pady=20)
        ttk.Label(title_frame,
                  text='Test Sonuçları',
                  font=self.title_font,
                  style='Custom.TLabel').pack()

        # Scrollable frame oluştur
        sf = ScrollableFrame(self.root, theme_name=self.theme_manager.current)
        sf.pack(fill='both', expand=True)

        # Soruları göster
        for idx, q in enumerate(self.test_questions):
            q_frame = ttk.Frame(sf.inner, style='Custom.TFrame')
            q_frame.pack(fill='x', pady=5, padx=5)

            # Soru numarası ve metni
            is_blank = self.test_selected_answers[idx].get() == ""
            question_title = f"Soru {idx + 1}: {q['question']}"
            if is_blank:
                question_title = f"🟠{question_title} | Boş "
            fg_color = 'orange' if is_blank else THEMES[self.theme_manager.current]['fg']

            # Soru etiketi
            tk.Label(q_frame,
                     text=question_title,
                     wraplength=800,
                     fg=fg_color,
                     bg=THEMES[self.theme_manager.current]['bg'],
                     font=('Arial', 10, 'bold')).pack(anchor='center', pady=(0, 10))

            # Şıkları gösterme
            options = q.get('options', {})
            for opt in ['A', 'B', 'C', 'D']:
                if opt in options:
                    # Doğru şık ise yeşil renk
                    is_correct = opt == q['answer']
                    # Kullanıcının seçtiği şık ise ve yanlışsa kırmızı renk
                    user_selected = self.test_selected_answers[idx].get() == opt
                    is_wrong_selection = user_selected and not is_correct

                    theme = THEMES[self.theme_manager.current]
                    # Renk belirleme
                    if is_correct:
                        bg_color = '#1f4025' if self.theme_manager.current == 'dark' else '#e6ffe6'
                        text_color = '#00ff88' if self.theme_manager.current == 'dark' else 'green'
                        prefix = ""
                        suffix = "✓ "
                    elif is_wrong_selection:
                        bg_color = '#402020' if self.theme_manager.current == 'dark' else '#ffe6e6'
                        text_color = '#ff6666' if self.theme_manager.current == 'dark' else 'red'
                        prefix = ""
                        suffix = "✗  (Sizin Cevabınız)"
                    else:
                        bg_color = theme['bg']
                        text_color = theme['fg']
                        prefix = ""
                        suffix = ""

                    # Şık frame'i
                    option_frame = tk.Frame(q_frame, bg=THEMES[self.theme_manager.current]['bg'])
                    option_frame.pack(fill='x', pady=1)

                    # Şık etiketi
                    tk.Label(
                        option_frame,
                        text=f"{prefix}{opt}) {options[opt]}{suffix}",
                        bg=bg_color,
                        fg=text_color,
                        wraplength=750,
                        font=('Arial', 9),
                        padx=5, pady=2
                    ).pack(side='left', fill='x', expand=True)

            # Açıklama
            explanation_color = '#7ecbff' if self.theme_manager.current == 'dark' else 'blue'
            tk.Label(q_frame,
                     text=f"Açıklama: {q.get('explanation', 'Açıklama yok')}",
                     fg=explanation_color,
                     bg=THEMES[self.theme_manager.current]['bg'],
                     wraplength=800,
                     font=('Arial', 9, 'italic')).pack(anchor='w', pady=(10, 5))

            # Ayırıcı çizgi
            ttk.Separator(q_frame, orient='horizontal').pack(fill='x', pady=5)

        # Ana menüye dön butonu
        ttk.Button(self.root, text="Ana Menü", command=self.show_main_menu).pack(pady=20)
        ttk.Button(self.root, text="Performans Değerlendirmesi", command=self.show_test_rating).pack(pady=10)

    def show_test_rating(self):
        self.clear()
        self.current_screen = 'test_report'

        correct = 0
        for idx, q in enumerate(self.test_questions):
            if self.test_selected_answers[idx].get() == q['answer']:
                correct += 1

        total = len(self.test_questions)
        wrong = total - correct
        ratio = correct / total if total else 0

        if ratio >= 0.9:
            grade = "S+ (Mükemmel)"
        elif ratio >= 0.75:
            grade = "A (İyi)"
        elif ratio >= 0.5:
            grade = "B (Orta)"
        else:
            grade = "C (Zayıf)"

        ttk.Label(self.root, text="Test Değerlendirme Raporu", font=self.title_font).pack(pady=20)
        ttk.Label(self.root, text=f"Toplam Soru: {total}").pack()
        ttk.Label(self.root, text=f"Doğru: {correct} | Yanlış: {wrong}").pack()
        ttk.Label(self.root, text=f"Başarı Notu: {grade}").pack(pady=10)
        ttk.Button(self.root, text="Sonuçlara Geri Dön", command=self.show_test_results).pack(pady=20)

    def start_exam(self, kind):
        self.test_type = kind
        if kind == 'TYT':
            self.modules = [
                {'name': 'Türkçe', 'num': 5},
                {'name': 'Matematik', 'num': 5},
                {'name': 'Fen', 'num': 5},
                {'name': 'Sosyal', 'num': 5}
            ]
            self.remaining_sec = 135 * 60
        else:
            self.modules = [
                {'name': 'Matematik', 'num': 6},
                {'name': 'Fen', 'num': 6},
                {'name': 'Edebiyat', 'num': 6},
                {'name': 'Sosyal', 'num': 6}
            ]
            self.remaining_sec = 120 * 60

        self.clear()
        ttk.Label(self.root, text='Sorular oluşturuluyor, lütfen bekleyin...', font=self.title_font).pack(pady=200)
        self.root.update()
        self.generate_questions()


        # E-sınav modülü için işlemler
        def thread_target():
            try:
                for m in self.modules:
                    prompt = f"{self.test_type} {m['name']} için {m['num']} test sorusu üret. Her soru şu formatta olsun:\n\nSoru 1: [soru metni]\nA) [şık A]\nB) [şık B]\nC) [şık C]\nD) [şık D]\nCevap: [doğru şık]\nAçıklama: [açıklama metni]\n\nLütfen bu formata kesinlikle uyun!"
                    res = model.generate_content(prompt)
                    parsed = self.parse_ai_questions(res.text)
                    m['questions'] = parsed
                    logging.info(f"{m['name']} için {len(parsed)} soru oluşturuldu")

                self.root.after(0, self.show_exam_interface)
                self.root.after(0, self.start_timer)
            except Exception as e:
                logging.error(f"Hata oluştu: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Hata",
                                                                "Sorular oluşturulurken bir hata oluştu. Lütfen tekrar deneyin."))
            finally:
                self.generating = False
                self.theme_manager.set_generating_state(False)

        threading.Thread(target=thread_target, daemon=True).start()

    def parse_ai_questions(self, text):
        questions = []
        current_q = {}
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('Soru'):
                if current_q:
                    questions.append(current_q)
                current_q = {
                    'question': line.split(':', 1)[-1].strip(),
                    'options': {},
                    'answer': '',
                    'explanation': '',
                    'selected_answer': tk.StringVar(value="")
                }
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                opt = line[0]
                if 'options' not in current_q:
                    current_q['options'] = {}
                current_q['options'][opt] = line[2:].strip()
            elif line.startswith('Cevap:'):
                current_q['answer'] = line.split(':', 1)[-1].strip()
            elif line.startswith('Açıklama:'):
                current_q['explanation'] = line.split(':', 1)[-1].strip()

        if current_q:
            questions.append(current_q)

        # Eksik verileri kontrol et
        valid_questions = []
        for q in questions:
            if 'question' in q and 'options' in q and len(q['options']) >= 4:
                valid_questions.append(q)

        return valid_questions

    def show_exam_interface(self):
        self.clear()

        self.current_screen = 'exam'
        # Üst çubuk
        top = ttk.Frame(self.root)
        top.pack(fill='x', padx=10, pady=5)

        # Modül butonları
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side='left')
        for idx, module in enumerate(self.modules):
            ttk.Button(btn_frame, text=module['name'],
                       command=lambda i=idx: self.switch_module(i)).pack(side='left', padx=5)

        # Timer
        self.timer_label = ttk.Label(top, text="00:00", font=self.font)
        self.timer_label.pack(side='right')

        # Sınavı tamamla butonu
        complete_btn = ttk.Button(top, text="Sınavı Tamamla", command=self.complete_exam)
        complete_btn.pack(side='right', padx=10)

        # Ana içerik
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # Optik Form (Sağda)
        opt_frame = ttk.Frame(main_frame, width=120, style='Optik.TFrame')
        opt_frame.pack(side='right', fill='y', padx=10, pady=10)

        ttk.Label(opt_frame, text="Optik Form", style='Optik.TLabel').pack(pady=5)

        self.optik_circles = []
        questions = self.modules[self.current_module]['questions']

        for i in range(len(questions)):
            cell_frame = ttk.Frame(opt_frame, style='Optik.TFrame')
            cell_frame.pack(pady=2, fill='x')

            ttk.Label(cell_frame, text=str(i + 1), width=3).pack(side='left', padx=5)
            circles_frame = ttk.Frame(cell_frame)
            circles_frame.pack(side='left', fill='x', expand=True)

            circles = []
            for opt in ['A', 'B', 'C', 'D']:
                circle = ttk.Radiobutton(
                    circles_frame,
                    text=opt,
                    style='Optik.TRadiobutton',
                    value=opt,
                    variable=self.modules[self.current_module]['questions'][i]['selected_answer'],
                    command=lambda idx=i: self.update_optik_display(idx),
                    state='disabled'
                )
                circle.pack(side='left', expand=True)
                circles.append(circle)

            self.optik_circles.append(circles)
            cell_frame.bind('<Button-1>', lambda e, idx=i: self.scroll_to_question(idx))

        # Sorular (Scrollable)
        self.sf = ScrollableFrame(main_frame, theme_name=self.theme_manager.current)
        self.sf.pack(fill='both', expand=True)

        self.q_frames = []
        self.explanation_labels = []  # Açıklama label'larını saklamak için liste
        questions = self.modules[self.current_module]['questions']

        for idx, q in enumerate(questions):
            module_name = self.modules[self.current_module]['name']
            unique_key = f"{self.test_type}_{module_name}_{idx}"

            # Daha önce işaretlenmiş şıkkı yükle
            q['selected_answer'] = tk.StringVar(value=self.selected_answers.get(unique_key, ""))

            fr = ttk.LabelFrame(self.sf.inner, text=f"Soru {idx + 1}", padding=10)
            fr.pack(fill='x', pady=5)

            # Soru metni
            ttk.Label(fr, text=q.get('question', 'Soru metni yok'), wraplength=800).pack(anchor='w', pady=5)

            # Şıklar
            options = q.get('options', {})
            for opt in ['A', 'B', 'C', 'D']:
                if opt in options:
                    bg_color = THEMES[self.theme_manager.current]['bg']
                    fg_color = THEMES[self.theme_manager.current]['fg']
                    ttk.Radiobutton(
                        fr,
                        text=f"{opt}) {options[opt]}",
                        value=opt,
                        variable=q['selected_answer'],
                        command=lambda qidx=idx: self.save_answer(qidx),
                        style='Question.TRadiobutton'
                    ).pack(anchor='w')

            # Açıklama (başlangıçta gizli)
            explanation = ttk.Label(
                fr,
                text=f"Açıklama: {q.get('explanation', 'Açıklama yok')}",
                foreground='blue',
                wraplength=800
            )
            # Açıklamayı hemen pack yapmıyoruz, sadece oluşturuyoruz
            self.explanation_labels.append(explanation)  # Listeye ekle

            self.q_frames.append(fr)

        # Stil ayarları
        ttk.Style().configure('Opt.TFrame', background='#f5f5f5')

    def update_optik_display(self, question_idx):
        """optik formdaki görünümü güncelleyen metod"""
        selected = self.modules[self.current_module]['questions'][question_idx]['selected_answer'].get()
        for i, opt in enumerate(['A', 'B', 'C', 'D']):
            btn = self.optik_circles[question_idx][i]
            if opt == selected:
                btn.state(['selected'])
            else:
                btn.state(['!selected'])

    def save_answer(self, question_idx):
        q = self.modules[self.current_module]['questions'][question_idx]
        selected = q['selected_answer'].get()

        # Seçimi kaydet
        module_name = self.modules[self.current_module]['name']
        unique_key = f"{self.test_type}_{module_name}_{question_idx}"
        self.selected_answers[unique_key] = selected

        # Optik formu güncelle
        self.update_optik_display(question_idx)

    def switch_module(self, idx):
        self.save_current_module_answers()
        self.current_module = idx
        self.show_exam_interface()
        # optik formu da güncelle
        for q_idx in range(len(self.modules[self.current_module]['questions'])):
            self.update_optik_display(q_idx)

    def save_current_module_answers(self):
        for q_idx, q in enumerate(self.modules[self.current_module]['questions']):
            self.save_answer(q_idx)

    def scroll_to_question(self, idx):
        if idx < len(self.q_frames):
            self.sf.canvas.yview_moveto(self.q_frames[idx].winfo_y() / self.sf.inner.winfo_height())

            # optik formda seçili hücreyi vurgula
            for i, circles in enumerate(self.optik_circles):
                for circle in circles:
                    if i == idx:
                        circle.config(style='Selected.TRadiobutton')
                    else:
                        circle.config(style='Optik.TRadiobutton')

    def start_timer(self):
        def tick():
            try:
                if self.remaining_sec > 0 and hasattr(self, 'timer_label') and self.timer_label:
                    m, s = divmod(self.remaining_sec, 60)
                    self.timer_label.config(text=f"Kalan Süre: {m:02d}:{s:02d}")
                    self.remaining_sec -= 1
                    self.root.after(1000, tick)
                elif self.remaining_sec <= 0:
                    if hasattr(self, 'timer_label') and self.timer_label:
                        self.timer_label.config(text="Süre Doldu!")
                    messagebox.showinfo("Bilgi", "Sınav süreniz doldu!")
                    self.show_results()
            except Exception as e:
                print(f"Timer hatası: {e}")  # Hata ayıklama için

        tick()

    def complete_exam(self):
        # Tüm cevapları kaydet
        self.save_current_module_answers()

        # Kullanıcıya onay sorusu göster
        if not messagebox.askyesno("Onay", "Sınavı tamamlamak istediğinize emin misiniz?"):
            return

        # Süreyi durdur
        self.remaining_sec = 0
        if hasattr(self, 'timer_label'):
            self.timer_label = None

        # Açıklamaları göster
        self.show_results()

    def show_results(self):

        self.current_screen = 'results'

        # Timer'ı tamamen durdur
        self.remaining_sec = 0
        self.clear()

        theme = THEMES[self.theme_manager.current]

        # Renkleri tema değişkenlerinden al
        theme = THEMES[self.theme_manager.current]
        correct_bg = theme['highlight'] if self.theme_manager.current == 'dark' else '#e6ffe6'
        correct_fg = '#00ff88' if self.theme_manager.current == 'dark' else 'green'

        # Başlık
        title_frame = ttk.Frame(self.root, style='Custom.TFrame')
        title_frame.pack(fill='x', pady=20)
        ttk.Label(title_frame,
                  text='Sınav Sonuçları',
                  font=self.title_font,
                  style='Custom.TLabel').pack()

        # Scrollable frame oluştur
        sf = ScrollableFrame(self.root, theme_name=self.theme_manager.current)
        sf.pack(fill='both', expand=True)

        # Tüm modülleri ve soruları göster
        for module_idx, module in enumerate(self.modules):
            module_frame = ttk.LabelFrame(sf.inner,
                                          text=module['name'],
                                          padding=10,
                                          style='Custom.TLabelframe')
            module_frame.pack(fill='x', pady=10, padx=5)

            for q_idx, q in enumerate(module['questions']):
                q_frame = ttk.Frame(module_frame, style='Custom.TFrame')
                q_frame.pack(fill='x', pady=5, padx=5)

                # Soru numarası ve metni
                is_blank = q['selected_answer'].get() == ""
                question_title = f"Soru {q_idx + 1}: {q['question']}"
                if is_blank:
                    question_title = f"🟠{question_title} | Boş "
                fg_color = 'orange' if is_blank else THEMES[self.theme_manager.current]['fg']

                # Soru etiketi
                tk.Label(q_frame,
                         text=question_title,
                         wraplength=800,
                         fg=fg_color,
                         bg=THEMES[self.theme_manager.current]['bg'],  # Arkaplan rengi
                         font=('Arial', 10, 'bold')).pack(anchor='center', pady=(0, 10))

                # Şıkları gösterme
                options = q.get('options', {})
                for opt in ['A', 'B', 'C', 'D']:
                    if opt in options:
                        # Doğru şık ise yeşil renk
                        is_correct = opt == q['answer']
                        # Kullanıcının seçtiği şık ise ve yanlışsa kırmızı renk
                        user_selected = q['selected_answer'].get() == opt
                        is_wrong_selection = user_selected and not is_correct
                        # eğer soru boş bırakıldıysa
                        is_blank = q['selected_answer'].get() == ""

                        theme = THEMES[self.theme_manager.current]
                        # Renk belirleme
                        if is_correct:
                            bg_color = '#1f4025' if self.theme_manager.current == 'dark' else '#e6ffe6'
                            text_color = '#00ff88' if self.theme_manager.current == 'dark' else 'green'
                            prefix = ""
                            suffix = "✓ "
                        elif is_wrong_selection:
                            bg_color = '#402020' if self.theme_manager.current == 'dark' else '#ffe6e6'
                            text_color = '#ff6666' if self.theme_manager.current == 'dark' else 'red'
                            prefix = ""
                            suffix = "✗  (Sizin Cevabınız)"
                        else:
                            bg_color = theme['bg']
                            text_color = theme['fg']
                            prefix = ""
                            suffix = ""

                        # Şık frame'i
                        option_frame = tk.Frame(q_frame, bg=THEMES[self.theme_manager.current]['bg'])
                        option_frame.pack(fill='x', pady=1)

                        # Şık etiketi
                        tk.Label(
                            option_frame,
                            text=f"{prefix}{opt}) {options[opt]}{suffix}",
                            bg=bg_color,  # THEMES[self.theme_manager.current]['bg'],  # Arkaplan rengi
                            fg=text_color,
                            wraplength=750,
                            font=('Arial', 9),
                            padx=5, pady=2
                        ).pack(side='left', fill='x', expand=True)

                # Açıklama
                bg = THEMES[self.theme_manager.current]['bg']
                explanation_color = '#7ecbff' if self.theme_manager.current == 'dark' else 'blue'
                tk.Label(q_frame,
                         text=f"Açıklama: {q.get('explanation', 'Açıklama yok')}",
                         fg=explanation_color,
                         bg=THEMES[self.theme_manager.current]['bg'],  # <-- Eksikti
                         wraplength=800,
                         font=('Arial', 9, 'italic')).pack(anchor='w', pady=(10, 5))

                # Ayırıcı çizgi
                ttk.Separator(q_frame, orient='horizontal').pack(fill='x', pady=5)

        # Ana menüye dön butonu
        ttk.Button(self.root, text="Ana Menü", command=self.show_main_menu).pack(pady=20)
        ttk.Button(self.root, text="Raporu Görüntüle", command=self.show_exam_report).pack(pady=10)

    def show_exam_report(self):
        self.clear()
        self.current_screen = 'exam_report'

        ttk.Label(self.root, text="Yapay Zeka Destekli Sınav Raporu", font=self.title_font).pack(pady=20)

        total = correct = incorrect = blank = 0
        for module in self.modules:
            for q in module['questions']:
                total += 1
                selected = q['selected_answer'].get()
                if selected == "":
                    blank += 1
                elif selected == q['answer']:
                    correct += 1
                else:
                    incorrect += 1

        accuracy = (correct / total) * 100 if total else 0

        yorum = model.generate_content(
            f"Kullanıcı {total} soruda {correct} doğru, {incorrect} yanlış ve {blank} boş yapmıştır. Performansı nasıl değerlendirirsin?"
        )

        ttk.Label(self.root, text=f"Toplam Soru: {total}").pack()
        ttk.Label(self.root, text=f"Doğru: {correct} | Yanlış: {incorrect} | Boş: {blank}").pack(pady=5)
        ttk.Label(self.root, text="Yorum:", font=('Segoe UI', 10, 'bold')).pack(pady=(10, 2))
        ttk.Label(self.root, text=yorum.text, wraplength=800, justify='center').pack(padx=10, pady=10)

        ttk.Button(self.root, text="Sonuçlara Geri Dön", command=self.show_results).pack(pady=20)


if __name__ == '__main__':
    root = tk.Tk()
    app = QuestionApp(root)
    root.mainloop()