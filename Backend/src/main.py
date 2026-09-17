"""Entrada do MVP Boarding Monitor. Execute: python src/main.py."""

import json
import sys
from time import perf_counter

from config import ROOT, DEFAULT_VIDEO, BOARDING_VIDEO, arguments, prepare_environment, project_path


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def run(args):
    prepare_environment()
    import torch
    import cv2

    from services.arrival import ArrivalMonitor
    from services.bus_matcher import BusMatcher, load_data
    from services.notification_service import NotificationService
    from services.boarding import BoardingMonitor, load_platforms
    from vision.detector import BusDetector
    from vision.ocr_reader import OCRReader
    from vision.overlay import Overlay
    from vision.text_tracker import TextTracker
    from vision.video_processor import VideoSource
    from vision.platform_geometry import PlatformGeometry

    torch.set_num_threads(args.threads)
    cv2.setNumThreads(1)
    if args.device == "auto":
        args.device = "0" if torch.cuda.is_available() else "cpu"
    if args.ocr_device == "auto":
        args.ocr_device = args.device
    if args.device != "cpu" and not torch.cuda.is_available():
        raise ValueError("CUDA indisponível. Instale requirements-cuda.txt ou use --device cpu.")
    if args.device == "cpu":
        hardware = "CPU"
        print("[HARDWARE] CPU. Para usar NVIDIA, instale requirements-cuda.txt.", flush=True)
    else:
        hardware = torch.cuda.get_device_name(int(args.device))
        torch.cuda.reset_peak_memory_stats(int(args.device))
        print(f"[HARDWARE] CUDA | {hardware}", flush=True)
    date, buses, passengers = load_data(ROOT, args.date)
    print(f"[INICIO] {len(buses)} viagens | {len(passengers)} passageiros | {date}", flush=True)
    print("[MODELOS] Carregando YOLO e EasyOCR. Primeiro uso requer download dos pesos.", flush=True)
    detector = BusDetector(project_path(args.model), args.device, args.imgsz)
    detector.warmup()
    # Ultralytics redefine o número de threads ao selecionar a CPU; restaure o limite.
    torch.set_num_threads(args.threads)
    reader = OCRReader(ROOT / "models/easyocr", args.ocr_device)
    if args.prepare:
        reader.close()
        print("[PRONTO] Modelos locais carregados.")
        return 0

    source = None
    writer = None
    window_created = False
    started = perf_counter()
    processed = 0
    detector_seconds = 0.0
    snapshot_saved = False
    boarding_snapshot_saved = False
    discarded_ocr = 0
    text_box_frames = 0
    text_kinds_seen = set()
    timestamp = 0.0
    last_canvas = None
    metrics = {"fps": 0.0, "detection_ms": 0.0}
    sources = [args.source]
    if args.scene in ("auto", "arrival") and not args.single_video and project_path(args.source).resolve() == DEFAULT_VIDEO.resolve():
        sources.append(args.boarding_source)
    source_index = 0
    timeline_offset = 0.0
    total_skipped = 0
    scene_reports = []
    scene_processed = 0
    scene_start = perf_counter()
    output_fps = None
    try:
        source = VideoSource(args.source, args.offline)
        scene = ("boarding" if project_path(args.source).resolve() == BOARDING_VIDEO.resolve() else "arrival") if args.scene == "auto" else args.scene
        mode = ("time" if source.demo else "zone") if args.arrival_mode == "auto" else args.arrival_mode
        if source.live and mode == "time":
            raise ValueError("Câmeras usam --arrival-mode zone; tempo simulado é restrito a vídeos.")
        monitor = ArrivalMonitor(mode, args.arrival_seconds, args.zone)
        matcher = BusMatcher(buses)
        notifier = NotificationService(passengers)
        text_tracker = TextTracker()
        overlay = Overlay()
        boarding = None
        geometry = None
        if scene == "boarding" or len(sources) > 1:
            platform_config = load_platforms(project_path(args.platform_config), buses)
        if scene == "boarding":
            boarding = BoardingMonitor(platform_config)
            geometry = PlatformGeometry(platform_config["platforms"])
            detector.image_size = args.boarding_imgsz
        print(f"[FONTE] {'CAMERA' if source.live else 'VIDEO'} | {source.fps:.2f} FPS | chegada: {mode}", flush=True)
        if not args.headless:
            cv2.namedWindow("Boarding Monitor", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Boarding Monitor", 1440, 750)
            window_created = True

        def accept_ocr(result, gray):
            nonlocal discarded_ocr
            state = monitor.states.get(result.track_id)
            if state is None or timestamp - result.timestamp > 5.0 or state.last_seen != timestamp:
                discarded_ocr += 1
                return
            state.history.append((result.timestamp, result.readings))
            state.match = matcher.match(state.history)
            platform = next((s for s in boarding.platforms.values() if s.track_id == result.track_id), None) if boarding else None
            prefix_confirmed = platform.validate_prefix(result.readings) if platform else False
            text_tracker.accept(result, gray, timestamp, matcher, platform.bus["bus_prefix"] if platform else None, prefix_confirmed)
            if args.debug:
                texts = [(r.text, round(r.confidence, 2)) for r in result.readings]
                print(f"[OCR] t={result.timestamp:.2f}s track={result.track_id} duração={result.seconds:.2f}s {texts}", flush=True)
                if state.match:
                    match = state.match
                    print(f"[MATCH] {match.bus['bus_code']} score={match.score:.2f} empresa={match.company_votes} prefixo={match.prefix_votes} confirmado={match.confirmed}", flush=True)

        started = perf_counter()
        scene_start = started
        while True:
            packet = source.read()
            if packet is None:
                scene_reports.append({"scene": scene, "processed_frames": scene_processed, "skipped_frames": source.skipped, "source_seconds": source.duration, "elapsed_seconds": round(perf_counter() - scene_start, 3)})
                total_skipped += source.skipped
                source_index += 1
                if source_index >= len(sources):
                    break
                timeline_offset += source.duration
                source.close()
                # Não transfira IDs, OCR pendente ou histórico visual entre câmeras diferentes.
                reader.poll(wait=True)
                detector.reset()
                monitor = ArrivalMonitor("zone", args.arrival_seconds, args.zone)
                text_tracker = TextTracker()
                boarding = BoardingMonitor(platform_config)
                geometry = PlatformGeometry(platform_config["platforms"])
                detector.image_size = args.boarding_imgsz
                source = VideoSource(sources[source_index], args.offline)
                scene = "boarding"
                scene_processed = 0
                scene_start = perf_counter()
                timestamp = 0.0
                print("[CENA] Plataformas 63 e 62 | Iniciando OnibusDandoEmbarque.mp4", flush=True)
                if writer is not None and abs(source.fps - output_fps) > 0.01:
                    raise ValueError("A exportação da sequência exige vídeos com o mesmo FPS.")
                continue
            frame, timestamp = packet
            full_resolution_frame = frame
            if frame.shape[1] > args.frame_width:
                scale = args.frame_width / frame.shape[1]
                frame = cv2.resize(frame, (args.frame_width, round(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            if args.max_seconds is not None and timeline_offset + timestamp >= args.max_seconds:
                break
            tick = perf_counter()
            scene_detections = detector.detect(frame, include_people=scene == "boarding")
            detections = [d for d in scene_detections if d.kind == "bus"]
            people = [d for d in scene_detections if d.kind == "person"]
            detection_time = perf_counter() - tick
            detector_seconds += detection_time
            monitor.observe(detections, timestamp, frame.shape)
            if boarding is not None:
                anchors = geometry.update(frame, timestamp)
                for observation in boarding.update(detections, people, anchors, timestamp, frame.shape):
                    notifier.notify_boarding(observation, date, timeline_offset)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            text_tracker.update(gray, {d.track_id for d in detections}, timestamp)
            result = reader.poll()
            if result is not None:
                accept_ocr(result, gray)
            if not reader.busy:
                platform_tracks = {s.track_id for s in boarding.platforms.values()} if boarding else None
                eligible = [d for d in detections if timestamp - monitor.states[d.track_id].last_ocr >= args.ocr_interval and (platform_tracks is None or d.track_id in platform_tracks)]
                # Alterna entre veículos elegíveis; nenhum track compartilha evidências OCR.
                eligible.sort(key=lambda d: (monitor.states[d.track_id].last_ocr, -(d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1])))
                if eligible:
                    detection = eligible[0]
                    monitor.states[detection.track_id].last_ocr = timestamp
                    other_boxes = [d.bbox for d in detections if d.track_id != detection.track_id]
                    reader.submit(frame, detection, timestamp, other_boxes, prefix_frame=full_resolution_frame if boarding else None)
                    if args.offline:
                        accept_ocr(reader.poll(wait=True), gray)
            if scene == "arrival":
                for state in monitor.arrivals(timestamp, date):
                    notifier.notify(state.match.bus, date, timestamp, state.track_id, mode, state.match.score)
            regions = [region for regions in text_tracker.regions.values() for region in regions]
            if regions:
                text_box_frames += 1
                text_kinds_seen.update(region.kind for region in regions)
            processed += 1
            scene_processed += 1
            elapsed = perf_counter() - started
            metrics = {"fps": processed / max(elapsed, 0.001), "detection_ms": detection_time * 1000}
            if boarding is not None:
                last_canvas = overlay.render_boarding(frame, detections, people, boarding, text_tracker, notifier, timestamp, metrics, args.offline)
            else:
                last_canvas = overlay.render(frame, detections, monitor, text_tracker, notifier, timestamp, metrics, date, args.offline)
            if args.snapshot and scene == "arrival" and notifier.events and not snapshot_saved and timestamp >= notifier.events[0]["video_seconds"] + 1:
                path = project_path(args.snapshot)
                path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(path), last_canvas):
                    raise RuntimeError("Não foi possível salvar a imagem da chegada.")
                snapshot_saved = True
            boarding_events = [event for event in notifier.events if event["event"] == "BOARDING_STARTED"]
            if args.snapshot and boarding_events and not boarding_snapshot_saved and timestamp >= boarding_events[0]["video_seconds"] + 1:
                path = project_path(args.snapshot)
                path = path.with_stem(path.stem + "-boarding")
                path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(path), last_canvas):
                    raise RuntimeError("Não foi possível salvar a imagem do embarque.")
                boarding_snapshot_saved = True
            if args.output:
                if writer is None:
                    path = project_path(args.output)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), source.fps, (last_canvas.shape[1], last_canvas.shape[0]))
                    output_fps = source.fps
                    if not writer.isOpened():
                        raise RuntimeError("Não foi possível abrir o arquivo de vídeo de saída.")
                writer.write(last_canvas)
            if not args.headless:
                cv2.imshow("Boarding Monitor", last_canvas)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")) or cv2.getWindowProperty("Boarding Monitor", cv2.WND_PROP_VISIBLE) < 1:
                    break
                if key == 32:
                    pause_start = perf_counter()
                    while True:
                        key = cv2.waitKey(50) & 0xFF
                        if key in (32, 27, ord("q")) or cv2.getWindowProperty("Boarding Monitor", cv2.WND_PROP_VISIBLE) < 1:
                            break
                    source.pause_seconds += perf_counter() - pause_start
                    if key in (27, ord("q")) or cv2.getWindowProperty("Boarding Monitor", cv2.WND_PROP_VISIBLE) < 1:
                        break

        elapsed = perf_counter() - started
        if source_index < len(sources):
            total_skipped += source.skipped
            scene_reports.append({"scene": scene, "processed_frames": scene_processed, "skipped_frames": source.skipped, "source_seconds": timestamp, "elapsed_seconds": round(perf_counter() - scene_start, 3)})
        report = {
            "mode": "offline" if args.offline else "realtime",
            "device": args.device,
            "hardware": hardware,
            "ocr_device": args.ocr_device,
            "peak_vram_mb": round(torch.cuda.max_memory_allocated(int(args.device)) / 1024 ** 2, 1) if args.device != "cpu" else None,
            "model": project_path(args.model).name,
            "processed_frames": processed,
            "skipped_frames": total_skipped,
            "source_seconds": round(timestamp, 3),
            "sequence_seconds": round(timeline_offset + timestamp, 3),
            "scenes": scene_reports,
            "elapsed_seconds": round(elapsed, 3),
            "processing_fps": round(processed / max(elapsed, 0.001), 2),
            "mean_yolo_ms": round(detector_seconds / max(processed, 1) * 1000, 2),
            "ocr_calls": reader.calls,
            "mean_ocr_seconds": round(reader.seconds / max(reader.calls, 1), 3),
            "discarded_ocr": discarded_ocr,
            "frames_with_text_boxes": text_box_frames,
            "text_box_kinds": sorted(text_kinds_seen),
            "events": notifier.events,
        }
        if args.report:
            save_json(project_path(args.report), report)
        print("[RESUMO] " + json.dumps(report, ensure_ascii=False), flush=True)
        if not notifier.events:
            print("[AVISO] Nenhuma chegada confirmada. Consulte --debug; não foi usado resultado fixo.", flush=True)
        return 0
    finally:
        reader.close()
        if source:
            source.close()
        if writer:
            writer.release()
        if window_created:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(run(arguments()))
    except KeyboardInterrupt:
        print("\n[ENCERRADO] Execução interrompida pelo usuário.")
        raise SystemExit(130)
    except Exception as error:
        print(f"[ERRO] {error}", file=sys.stderr)
        raise SystemExit(1)
