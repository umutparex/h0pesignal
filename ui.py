# src/ui.py

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text
from typing import Dict, Any, List
import time

class TerminalUI:
    """
    Rich kütüphanesini kullanarak gelişmiş, çok panelli ve interaktif 
    terminal arayüzünü yöneten sınıf.
    """
    def __init__(self):
        self.console = Console()
        self.layout = self._create_layout()

    def _create_layout(self) -> Layout:
        """Ana arayüz yerleşimini oluşturur."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(name="footer", size=5)
        )
        layout["main"].split_row(Layout(name="summary_table", ratio=2), Layout(name="details_panel", ratio=1))
        layout["footer"].split_row(Layout(name="sentiment"), Layout(name="depth"))
        return layout

    def update_layout(self, all_analysis_data: List[Dict[str, Any]], selected_index: int):
        """
        Tüm arayüz panellerini yeni verilerle günceller.
        Bu metot, Live objesi tarafından çağrılmak üzere tasarlanmıştır.
        """
        zaman_str = time.strftime("%Y-%m-%d %H:%M:%S")
        self.layout["header"].update(Panel(f"[bold green]h0pesignal | ZİRVE SÜRÜMÜ[/] | [yellow]{zaman_str}[/]", style="green"))
        
        selected_data = all_analysis_data[selected_index] if all_analysis_data and 0 <= selected_index < len(all_analysis_data) else {}
        
        self.layout["summary_table"].update(self._create_main_table(all_analysis_data, selected_index))
        self.layout["details_panel"].update(self._create_details_panel(selected_data))
        self.layout["sentiment"].update(self._create_sentiment_panel(selected_data))
        self.layout["depth"].update(self._create_depth_panel(selected_data))

    def _create_main_table(self, all_analysis_data: List[Dict[str, Any]], selected_index: int) -> Panel:
        """Ana özet tablosunu oluşturur ve seçili satırı vurgular."""
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("PARİTE", style="cyan", width=12)
        table.add_column("FİYAT", style="yellow", justify="right")
        table.add_column("SİNYAL", justify="center")
        table.add_column("STRATEJİ", style="green", justify="center")
        table.add_column("SKOR", style="bold", justify="center")
        table.add_column("ANA SEBEPLER", style="dim", min_width=30)

        for i, data in enumerate(all_analysis_data):
            score = data.get("score", 0)
            sinyal_yonu = f"[bold green]✅ LONG[/]" if score > 0 else f"[bold red]⛔️ SHORT[/]" if score < 0 else "[dim]-- NÖTR --[/]"
            
            # Seçili satırı vurgulamak için stil belirle
            row_style = "on #282a36" if i == selected_index else ""
            
            table.add_row(
                data.get("parite", "N/A"), f"{data.get('fiyat', 0):,.4f} $", sinyal_yonu,
                data.get("strategy", "Bekle"), str(score), data.get("detay_str", ""),
                style=row_style
            )
        return Panel(table, title="[bold]Genel Piyasa Görünümü (▲/▼ tuşlarıyla gezinin)[/]", border_style="magenta")

    def _create_details_panel(self, analysis_data: Dict) -> Panel:
        parite = analysis_data.get("parite", "...")
        table = Table(show_header=True, header_style="bold blue", expand=True)
        table.add_column("ANALİZ", style="cyan")
        table.add_column("DEĞER", style="white", justify="right")
        table.add_column("SİNYAL", style="bold", justify="center")

        details = analysis_data.get("details", {})
        if not details:
            table.add_row("Veri Bekleniyor...", "", "")
        else:
            for key, data in details.items():
                if isinstance(data, dict):
                    value, signal = data.get('value', 'N/A'), data.get('signal', 0)
                    value_str = str(value)
                    signal_str = f"[green]{signal}[/]" if signal > 0 else f"[red]{signal}[/]" if signal < 0 else f"[dim]{signal}[/]"
                    table.add_row(key.upper(), value_str, signal_str)
        
        return Panel(table, title=f"[bold yellow]Teknik Analiz Dökümü: {parite}[/]", border_style="blue")

    def _create_sentiment_panel(self, data: Dict) -> Panel:
        fr = data.get('funding_rate'); oi = data.get('open_interest'); ls = data.get('ls_ratio')
        fr_str = f"[bold {'red' if fr is not None and fr > 0 else 'green'}]{fr:+.4f}%[/]" if fr is not None else "[dim]N/A[/]"
        oi_str = f"[bold yellow]{oi/1e9:.2f}B $[/]" if oi is not None else "[dim]N/A[/]"
        ls_str = f"[bold {'green' if ls is not None and ls > 1 else 'red'}]{ls:.2f}[/]" if ls is not None else "[dim]N/A[/]"
        text = Text(f"Funding: {fr_str} | L/S Oranı: {ls_str} | Açık Faiz: {oi_str}", justify="center")
        return Panel(text, title="Piyasa Duyarlılığı", border_style="green")

    def _create_depth_panel(self, data: Dict) -> Panel:
        depth = data.get("depth")
        if not depth or not depth.get("bids") or not depth.get("asks"):
            return Panel(Align.center("[dim]Veri Yok[/]"), title="Emir Defteri Derinliği (Heatmap)", border_style="red")
        
        bids = [f"[green]{float(p):>10,.2f} ({float(q):<7.2f})[/]" for p, q in depth['bids'][:3]]
        asks = [f"[red]{float(p):>10,.2f} ({float(q):<7.2f})[/]" for p, q in depth['asks'][:3]]
        
        text = Text("\n".join(asks[::-1] + [f"{'-'*25:^25}"] + bids), justify="center")
        return Panel(text, title="Emir Defteri Derinliği (Heatmap)", border_style="red")
