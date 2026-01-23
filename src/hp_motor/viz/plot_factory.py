import matplotlib.pyplot as plt
from mplsoccer import Pitch
import seaborn as sns

class HPPlotFactory:
    """HP Motor v5.0 - Görsel Karar Yüzeyi (Tenebrism Style)"""
    
    def __init__(self):
        # Tesla/Caravaggio estetiği için karanlık tema
        self.bg_color = '#000000'
        self.line_color = '#FFD700' # Altın sarısı sinyal

    def plot_trauma_zones(self, trauma_df):
        """Sapolsky/Mate: Hataların kümelendiği travma bölgelerini çizer."""
        pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                      pitch_color=self.bg_color, line_color=self.line_color)
        fig, ax = pitch.draw(figsize=(10, 7))
        
        if not trauma_df.empty:
            # Yoğunluk haritası (Karanlıkta parlayan hata bölgeleri)
            sns.kdeplot(x=trauma_df['pos_x'], y=trauma_df['pos_y'], 
                        ax=ax, fill=True, cmap='YlOrBr', alpha=0.5, levels=10)
            pitch.scatter(trauma_df['pos_x'], trauma_df['pos_y'], 
                          ax=ax, color='red', s=50, edgecolors='white', label='Trauma Loop')
            
        plt.title("Spatial Trauma Analysis (Sapolsky Loop)", color=self.line_color, family='monospace')
        return fig

    def plot_momentum_flow(self, momentum_df):
        """Temporal Engine: Maçın rejim değişimlerini gösterir."""
        fig, ax = plt.subplots(figsize=(10, 4), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)
        
        momentum_df.plot(ax=ax, color=self.line_color, linewidth=2)
        ax.axhline(0, color='white', linestyle='--', alpha=0.3)
        
        ax.tick_params(colors=self.line_color)
        plt.title("Regime Shift & Momentum Flow", color=self.line_color, family='monospace')
        return fig
