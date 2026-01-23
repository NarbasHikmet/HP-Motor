from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class ThemeConfig:
    background: str = "#0b0b0c"  # near-black
    foreground: str = "#e8e8e8"  # off-white
    muted: str = "#9aa0a6"       # muted grey
    accent: str = "#d4af37"      # restrained gold (Caravaggio highlight)
    danger: str = "#c0392b"      # restrained red
    grid_alpha: float = 0.06
    font_family: str = "DejaVu Sans"


class CaravaggioTeslaTheme:
    def __init__(self, cfg: Optional[ThemeConfig] = None) -> None:
        self.cfg = cfg or ThemeConfig()

    def apply_rc(self) -> None:
        plt.rcParams.update({
            "figure.facecolor": self.cfg.background,
            "axes.facecolor": self.cfg.background,
            "savefig.facecolor": self.cfg.background,
            "text.color": self.cfg.foreground,
            "axes.labelcolor": self.cfg.foreground,
            "xtick.color": self.cfg.muted,
            "ytick.color": self.cfg.muted,
            "axes.edgecolor": self.cfg.muted,
            "font.family": self.cfg.font_family,
        })

    def finalize_plot(
        self,
        fig,
        ax,
        title: str,
        subtitle: Optional[str] = None,
        legend_text: Optional[str] = None,
        footnote: Optional[str] = None,
    ) -> None:
        # Tesla: minimal clutter
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_alpha(0.2)

        # Title block (Caravaggio: strong contrast)
        fig.suptitle(title, x=0.02, y=0.98, ha="left", va="top", fontsize=14, fontweight="bold")
        if subtitle:
            fig.text(0.02, 0.945, subtitle, ha="left", va="top", fontsize=10, color=self.cfg.muted)

        # Legend (compact, consistent)
        if legend_text:
            fig.text(0.02, 0.02, legend_text, ha="left", va="bottom", fontsize=9, color=self.cfg.muted)

        if footnote:
            fig.text(0.98, 0.02, footnote, ha="right", va="bottom", fontsize=9, color=self.cfg.muted)

        fig.tight_layout(rect=[0, 0.05, 1, 0.93])