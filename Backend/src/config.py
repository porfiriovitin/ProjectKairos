"""Configuração da demonstração e caminhos relativos à raiz do projeto."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO = ROOT / "src/videos/OnibusChegandoTerminal.mp4"
BOARDING_VIDEO = ROOT / "src/videos/OnibusDandoEmbarque.mp4"


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def prepare_environment() -> None:
    # Mantenha os modelos e caches dentro do projeto, inclusive no Windows.
    for variable, directory in {
        "YOLO_CONFIG_DIR": ".cache/ultralytics",
        "MPLCONFIGDIR": ".cache/matplotlib",
        "TORCH_HOME": ".cache/torch",
    }.items():
        path = ROOT / directory
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(variable, str(path))
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    os.environ.setdefault("YOLO_VERBOSE", "false")


def arguments():
    parser = argparse.ArgumentParser(description="Boarding Monitor: YOLO + OCR em vídeo contínuo.")
    parser.add_argument("--source", default=str(DEFAULT_VIDEO), help="Vídeo, índice de câmera ou URL RTSP.")
    parser.add_argument("--boarding-source", default=str(BOARDING_VIDEO), help="Vídeo reproduzido depois da chegada na sequência padrão.")
    parser.add_argument("--single-video", action="store_true", help="Executa somente --source, sem avançar ao próximo vídeo.")
    parser.add_argument("--scene", choices=["auto", "arrival", "boarding"], default="auto")
    parser.add_argument("--platform-config", default="config/platforms.json")
    parser.add_argument("--date", default=None, help="Data da programação DD/MM/AAAA. Mock: única data do JSON.")
    parser.add_argument("--model", default="models/yolo11n.pt")
    parser.add_argument("--device", default="auto", help="auto, cpu ou índice CUDA, por exemplo 0.")
    parser.add_argument("--ocr-device", default="auto", help="auto usa o mesmo dispositivo do YOLO; cpu reduz uso de VRAM.")
    parser.add_argument("--imgsz", type=int, default=480)
    parser.add_argument("--boarding-imgsz", type=int, default=640, help="Resolução YOLO na cena com pessoas.")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--frame-width", type=int, default=1280, help="Largura máxima de processamento, preservando a proporção.")
    parser.add_argument("--ocr-interval", type=float, default=0.8, help="Intervalo mínimo de OCR por veículo, em segundos.")
    parser.add_argument("--arrival-seconds", type=float, default=20.0, help="Instante da chegada simulada no MP4 padrão.")
    parser.add_argument("--arrival-mode", choices=["auto", "time", "zone"], default="auto")
    parser.add_argument("--zone", nargs=4, type=float, default=[0.35, 0.65, 0.95, 0.98], metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--offline", action="store_true", help="Analisa todos os frames; OCR síncrono. Útil para auditoria.")
    parser.add_argument("--headless", action="store_true", help="Executa sem abrir uma janela.")
    parser.add_argument("--debug", action="store_true", help="Registra textos OCR e candidatos no console.")
    parser.add_argument("--output", help="Grava vídeo anotado; requer --offline.")
    parser.add_argument("--report", help="Salva métricas e eventos em JSON.")
    parser.add_argument("--snapshot", help="Salva imagem anotada da primeira chegada.")
    parser.add_argument("--max-seconds", type=float, help="Limita a duração total da sequência processada.")
    parser.add_argument("--prepare", action="store_true", help="Baixa/carrega os modelos e encerra.")
    parser.add_argument("--ws-host", default="127.0.0.1", help="Endereço do WebSocket do painel.")
    parser.add_argument("--ws-port", type=int, default=8765, help="Porta do WebSocket do painel.")
    parser.add_argument("--stream-fps", type=int, default=20, help="Limite de FPS enviados ao painel local.")
    parser.add_argument("--no-websocket", action="store_true", help="Desativa o painel WebSocket.")
    parser.add_argument("--keep-dashboard", action="store_true", help="Mantém o histórico acessível após o vídeo, até Ctrl+C.")
    args = parser.parse_args()
    if not 1 <= args.ws_port <= 65535:
        parser.error("ws-port deve estar entre 1 e 65535.")
    if not 1 <= args.stream_fps <= 60:
        parser.error("stream-fps deve estar entre 1 e 60.")
    if args.imgsz < 320 or args.boarding_imgsz < 320 or args.threads < 1 or args.frame_width < 640 or args.ocr_interval <= 0 or args.arrival_seconds < 0:
        parser.error("imgsz >= 320, frame-width >= 640, threads >= 1, ocr-interval > 0 e arrival-seconds >= 0 são obrigatórios.")
    x1, y1, x2, y2 = args.zone
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        parser.error("A zona deve usar coordenadas normalizadas ordenadas entre 0 e 1.")
    if args.max_seconds is not None and args.max_seconds <= 0:
        parser.error("max-seconds deve ser positivo.")
    if args.output and not args.offline:
        parser.error("Use --offline com --output para preservar a duração do vídeo exportado.")
    return args
