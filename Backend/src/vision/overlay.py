"""Janela da demonstração: vídeo anotado, evidências e eventos."""

import textwrap
import unicodedata

import cv2
import numpy as np

BACKGROUND = (24, 20, 15)
PANEL = (37, 31, 23)
WHITE = (241, 238, 226)
MUTED = (164, 158, 145)
GREEN = (130, 223, 79)
AMBER = (63, 193, 252)
CYAN = (230, 213, 85)
PURPLE = (236, 142, 215)
COLORS = {"EMPRESA": CYAN, "PREFIXO": AMBER, "HORARIO": PURPLE, "ITINERARIO": PURPLE}


def ascii_text(value):
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")


def write(image, text, position, color=WHITE, scale=0.55, thickness=1):
    cv2.putText(image, ascii_text(text), position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def label(image, text, x, y, color, scale=0.5):
    text = ascii_text(text)
    (width, height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x = max(0, min(int(x), image.shape[1] - width - 14))
    y = max(height + 10, min(int(y), image.shape[0] - 5))
    cv2.rectangle(image, (x, y - height - 8), (x + width + 12, y + 5), BACKGROUND, -1)
    write(image, text, (x + 6, y), color, scale)


class Overlay:
    def render(self, frame, detections, monitor, text_tracker, notifier, timestamp, metrics, date, offline):
        height, width = frame.shape[:2]
        video = frame.copy()
        if monitor.mode == "zone":
            x1, y1, x2, y2 = monitor.zone
            p1, p2 = (int(x1 * width), int(y1 * height)), (int(x2 * width), int(y2 * height))
            tint = video.copy()
            cv2.rectangle(tint, p1, p2, GREEN, -1)
            video = cv2.addWeighted(tint, 0.12, video, 0.88, 0)
            cv2.rectangle(video, p1, p2, GREEN, 2)
            label(video, "ZONA DE CHEGADA", p1[0], p1[1] - 6, GREEN)
        for detection in detections:
            state = monitor.states[detection.track_id]
            match = state.match
            color = GREEN if state.arrived else CYAN if match and match.confirmed else AMBER
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(video, (x1, y1), (x2, y2), color, 2)
            status = "CHEGOU" if state.arrived else "IDENTIFICADO" if match and match.confirmed else "IDENTIFICANDO"
            name = f"{match.bus['bus_company']} | {match.bus['bus_prefix']}" if match and match.confirmed else "ONIBUS"
            label(video, f"#{state.track_id:02} {name} | {status}", x1, y1 - 10, color, 0.57)
            if match and match.confirmed:
                route = match.bus["itinerary"]
                label(video, f"PROGRAMACAO: {route['from']} > {route['to']} | {route['departure_time']}", x1, y2 - 8, color)
            for region in text_tracker.regions.get(state.track_id, []):
                polygon = region.polygon.astype(np.int32)
                center = polygon.mean(axis=0)
                if not (x1 <= center[0] <= x2 and y1 <= center[1] <= y2):
                    continue
                text_color = COLORS[region.kind]
                cv2.polylines(video, [polygon], True, text_color, 2, cv2.LINE_AA)
                label_y = polygon[:, 1].max() + 20 if region.kind == "PREFIXO" else polygon[:, 1].min() - 5
                label(video, f"{region.kind}: {region.text[:32]}", polygon[:, 0].min(), label_y, text_color, 0.45)

        sidebar = 370
        top, bottom = 76, 48
        canvas = np.full((max(height, 680) + top + bottom, width + sidebar, 3), BACKGROUND, dtype=np.uint8)
        canvas[top:top + height, :width] = video
        cv2.rectangle(canvas, (width, top), (width + sidebar, canvas.shape[0] - bottom), PANEL, -1)
        write(canvas, "BOARDING MONITOR", (24, 34), WHITE, 0.85, 2)
        write(canvas, "VISAO COMPUTACIONAL  /  YOLO + OCR", (24, 57), CYAN, 0.43)
        clock = f"{timestamp:05.1f}s  |  {metrics['fps']:.1f} FPS  |  YOLO {metrics['detection_ms']:.0f} ms"
        write(canvas, clock, (max(430, width - 475), 32), WHITE, 0.56)
        mode = "AUDITORIA: TODOS OS FRAMES" if offline else "PROCESSAMENTO CONTINUO"
        write(canvas, mode, (max(430, width - 475), 55), MUTED, 0.43)
        left, y = width + 24, top + 30
        write(canvas, "CENTRAL DE CHEGADAS", (left, y), WHITE, 0.60, 2)
        y += 30
        cv2.line(canvas, (left, y), (width + sidebar - 24, y), MUTED, 1)
        y += 30
        states = [monitor.states[d.track_id] for d in detections]
        states.sort(key=lambda s: (s.arrived, bool(s.match and s.match.confirmed), (s.bbox[2] - s.bbox[0]) * (s.bbox[3] - s.bbox[1])), reverse=True)
        focus = states[0] if states else None
        if focus:
            write(canvas, f"VEICULO #{focus.track_id:02}", (left, y), CYAN, 0.52, 2)
            y += 29
            if focus.match:
                match = focus.match
                bus = match.bus
                write(canvas, bus["bus_company"], (left, y), WHITE, 0.65, 2)
                y += 28
                write(canvas, f"Prefixo {bus['bus_prefix']}  /  {bus['bus_code']}", (left, y), AMBER, 0.53)
                y += 26
                status = "IDENTIDADE CONFIRMADA" if match.confirmed else "CANDIDATO EM VALIDACAO"
                write(canvas, status, (left, y), GREEN if match.confirmed else AMBER, 0.43)
                y += 26
                write(canvas, f"Score de match: {match.score:.2f}", (left, y), MUTED, 0.46)
                y += 22
                write(canvas, f"Leituras: empresa {match.company_votes} | prefixo {match.prefix_votes}", (left, y), MUTED, 0.41)
                y += 32
                if match.confirmed:
                    write(canvas, "ITINERARIO / JSON", (left, y), PURPLE, 0.44)
                    y += 25
                    for field in ("from", "to"):
                        write(canvas, bus["itinerary"][field], (left, y), WHITE, 0.56)
                        y += 25
                    write(canvas, f"Saida {bus['itinerary']['departure_time']} | {bus.get('bus_kind', '')}", (left, y), MUTED, 0.46)
                    y += 28
            else:
                write(canvas, "Lendo empresa e prefixo...", (left, y), MUTED, 0.49)
                y += 30
        else:
            write(canvas, "Aguardando onibus na imagem", (left, y), MUTED, 0.48)
            y += 35
        y = max(y + 16, top + 405)
        cv2.line(canvas, (left, y), (width + sidebar - 24, y), MUTED, 1)
        y += 28
        write(canvas, f"EVENTOS EMITIDOS: {len(notifier.events)}", (left, y), GREEN, 0.5, 2)
        y += 28
        if notifier.events:
            event = notifier.events[-1]
            write(canvas, f"BUS_ARRIVED / {event['bus_code']}", (left, y), GREEN, 0.52, 2)
            y += 23
            write(canvas, f"{event['video_seconds']:.1f}s | {len(event['passenger_codes'])} passageiros avisados", (left, y), WHITE, 0.44)
            y += 26
            for passenger in notifier.passengers:
                if passenger["passenger_code"] in event["passenger_codes"]:
                    for line in textwrap.wrap(passenger["name"], 34):
                        write(canvas, line, (left, y), MUTED, 0.42)
                        y += 21
        else:
            write(canvas, "Aguardando confirmacao de chegada", (left, y), MUTED, 0.42)
        footer = canvas.shape[0] - 18
        write(canvas, "EMPRESA", (24, footer), CYAN, 0.43)
        write(canvas, "PREFIXO", (130, footer), AMBER, 0.43)
        write(canvas, "LETREIRO", (230, footer), PURPLE, 0.43)
        write(canvas, "Caixas: deteccao e OCR reais | Dados da viagem: mock", (350, footer), MUTED, 0.42)
        write(canvas, "ESPACO pausa | Q sair", (width + 24, footer), MUTED, 0.44)
        return canvas
