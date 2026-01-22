import matplotlib.pyplot as plt

class TenebrismRenderer:
    """Caravaggio Standardı: Koyu Arka Plan, Güçlü Sinyal, Tesla Renkleri"""
    
    def __init__(self):
        self.bg_color = "#000000" # Pure Void
        self.accent_color = "#FFD700" # Tesla Gold
        self.error_color = "#FF0000" # Electric Red

    def finalize_plot(self, ax, title, confidence):
        ax.set_facecolor(self.bg_color)
        plt.title(f"{title} | Güven: %{confidence}", color=self.accent_color, loc='left', pad=20)
        # Lejant kuralları (Örneklem, Kaynak, Filtre) otomatik eklenir.
        plt.figtext(0.1, 0.02, "Kaynak: HP-CDL | n=411 | Filtre: F4 Incision", color='gray', fontsize=8)
