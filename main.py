# main.py

import time
import json
import keyboard
import threading
import copy
from rich.console import Console
from rich.live import Live
from typing import Dict, List

# Proje dosyalarından gerekli sınıfları import et
from src.api_client import APIClient
from src.analysis_engine import AnalysisEngine
from src.ui import TerminalUI

# --- Global Değişkenler ve Kontrol Mekanizmaları ---
# Bu değişkenler, iki iş parçacığı arasında güvenli veri alışverişi sağlar.
all_results: List[Dict] = []
data_lock = threading.Lock()
keep_running = True

def data_updater_thread(api_client: APIClient, analysis_engine: AnalysisEngine, config: Dict):
    """
    Arka planda çalışacak ve periyodik olarak verileri güncelleyecek olan iş parçacığı.
    """
    global all_results, keep_running
    
    app_settings = config.get("app_settings", {})
    pariteler = app_settings.get("pariteler", ["BTCUSDT"])
    zaman_araligi = app_settings.get("zaman_araligi", "1h")
    guncelleme_suresi = app_settings.get("guncelleme_siklgi_saniye", 60)

    while keep_running:
        temp_results = []
        for parite in pariteler:
            if not keep_running: break
            klines = api_client.get_klines(parite, zaman_araligi)
            market_data = {
                "ls_ratio": api_client.get_long_short_ratio(parite),
                "funding_rate": api_client.get_funding_rate(parite),
                "open_interest": api_client.get_open_interest(parite),
                "depth": api_client.get_order_book_depth(parite)
            }
            analysis_result = analysis_engine.run_full_analysis(klines, market_data)
            analysis_result['parite'] = parite
            analysis_result.update(market_data)
            temp_results.append(analysis_result)
        
        if temp_results:
            # Veri yazma işlemini kilitleyerek güvenli hale getir
            with data_lock:
                global all_results
                all_results = copy.deepcopy(temp_results)
        
        # Bir sonraki güncellemeye kadar bekle
        time.sleep(guncelleme_suresi)

def load_config(path: str = "config.json") -> Dict:
    """Yapılandırma dosyasını yükler."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        Console().print(f"[bold red]Config dosyası hatası: {e}[/bold red]")
        exit()

def main():
    """
    Ana program. Arayüzü, klavye kontrolünü yönetir ve veri iş parçacığını başlatır.
    """
    global keep_running
    
    console = Console()
    config = load_config()
    
    api_client = APIClient(config)
    analysis_engine = AnalysisEngine(config)
    ui = TerminalUI()

    pariteler = config.get("app_settings", {}).get("pariteler", ["BTCUSDT"])
    
    # --- Veri Güncelleyici İş Parçacığını Başlat ---
    updater_thread = threading.Thread(
        target=data_updater_thread, 
        args=(api_client, analysis_engine, config),
        daemon=True # Ana program kapandığında bu thread'in de kapanmasını sağlar
    )
    updater_thread.start()

    selected_index = 0
    
    # --- Ana Arayüz Döngüsü ---
    with Live(ui.layout, screen=True, redirect_stderr=False, refresh_per_second=20) as live:
        live.console.print("[yellow]h0pesignal başlatılıyor, ilk veriler çekiliyor...[/yellow]")
        time.sleep(2) # İlk verilerin gelmesi için kısa bir bekleme

        while keep_running:
            try:
                # --- Klavye Kontrolü (Her zaman aktif) ---
                if keyboard.is_pressed('down') and pariteler:
                    selected_index = (selected_index + 1) % len(pariteler)
                    time.sleep(0.15)
                elif keyboard.is_pressed('up') and pariteler:
                    selected_index = (selected_index - 1 + len(pariteler)) % len(pariteler)
                    time.sleep(0.15)
                elif keyboard.is_pressed('q'):
                    keep_running = False # Döngüyü ve thread'i sonlandır
                    break

                # --- Arayüzü Güncelleme ---
                # Veri okuma işlemini kilitleyerek güvenli hale getir
                with data_lock:
                    current_results = copy.deepcopy(all_results)
                
                if current_results:
                    ui.update_layout(current_results, selected_index)

                time.sleep(0.05) # CPU kullanımını düşürür ve döngüyü akıcı tutar

            except Exception as e:
                live.console.print(f"[bold red]Ana döngüde hata: {e}[/bold red]")
                time.sleep(5)

    console.print("\n[bold red]Uygulama kapatıldı. Bol kazançlar![/bold red]")

if __name__ == "__main__":
    main()
