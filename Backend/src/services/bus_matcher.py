"""Relaciona evidências OCR por veículo com os candidatos da programação."""

import json
import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz.fuzz import ratio


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.upper())
    text = re.sub(r"\b([01]?\d|2[0-3])\s*[:,;.]\s*([0-5]\d)\b", r"\1:\2", text)
    return re.sub(r"[^A-Z0-9: ]", "", "".join(c for c in text if not unicodedata.combining(c)))


def load_data(root: Path, date: str | None = None):
    with (root / "bus_schedules.json").open(encoding="utf-8-sig") as file:
        schedules = json.load(file)
    with (root / "passengers.json").open(encoding="utf-8-sig") as file:
        passengers = json.load(file)["passengers"]
    if date is None:
        if len(schedules) != 1:
            raise ValueError("Há várias datas na programação. Informe --date DD/MM/AAAA.")
        date = next(iter(schedules))
    if date not in schedules:
        raise ValueError(f"Data {date} não encontrada em bus_schedules.json.")
    buses = schedules[date]
    codes = [bus["bus_code"] for bus in buses]
    if len(codes) != len(set(codes)):
        raise ValueError("bus_code deve ser único na programação da data selecionada.")
    for bus in buses:
        for field in ("bus_company", "bus_prefix", "itinerary"):
            if not bus.get(field):
                raise ValueError(f"Campo ausente no ônibus {bus['bus_code']}: {field}")
        for field in ("from", "to", "departure_time"):
            if not bus["itinerary"].get(field):
                raise ValueError(f"Campo ausente no itinerário: {field}")
    return date, buses, passengers


def company_similarity(text: str, company: str) -> float:
    text = normalize(text).replace("1", "I").replace("0", "O")
    company = normalize(company)
    words = [w for w in company.split() if w not in {"EMPRESA", "VIACAO", "AUTO", "EXPRESSO", "TRANSPORTES"}]
    expected = "".join(words) or company.replace(" ", "")
    observed = text.replace(" ", "")
    if len(observed) < max(4, len(expected) * 0.65):
        return 0.0
    if expected in observed:
        return 1.0
    return ratio(observed, expected) / 100


def prefix_similarity(text: str, prefix: str) -> float:
    best = 0.0
    # Correções limitadas a tokens numéricos; não converta nomes/horários em prefixos.
    mapping = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "G": "6", "B": "8"})
    for token in normalize(text).split():
        if ":" in token or len(token) != len(prefix):
            continue
        if sum(c.isdigit() for c in token) < len(token) - 1:
            continue
        numeric = token.translate(mapping)
        if numeric.isdigit():
            best = max(best, ratio(numeric, prefix) / 100)
    return best


@dataclass
class Match:
    bus: dict
    score: float
    company_votes: int
    prefix_votes: int
    confirmed: bool


class BusMatcher:
    def __init__(self, buses: list[dict]):
        self.buses = buses

    def classify_text(self, text: str) -> str:
        if any(company_similarity(text, bus["bus_company"]) >= 0.78 for bus in self.buses):
            return "EMPRESA"
        if any(prefix_similarity(text, str(bus["bus_prefix"])) >= 0.8 for bus in self.buses):
            return "PREFIXO"
        value = normalize(text)
        if re.search(r"\d{1,2}\s*:\s*\d{2}", value):
            return "HORARIO"
        for bus in self.buses:
            if any(normalize(bus["itinerary"][field]) in value for field in ("from", "to")):
                return "ITINERARIO"
        if re.match(r"^(DE[ :]|P[/ ]|PARA )", text.upper()):
            return "ITINERARIO"
        return "TEXTO"

    def match(self, history: deque) -> Match | None:
        if not history:
            return None
        ranked = []
        for bus in self.buses:
            company_scores, prefix_scores, extra_scores = [], [], []
            for _, readings in history:
                texts = [r.text for r in readings if r.confidence >= 0.20]
                company_scores.append(max((company_similarity(t, bus["bus_company"]) for t in texts), default=0))
                prefix_scores.append(max((prefix_similarity(t, str(bus["bus_prefix"])) for t in texts), default=0))
                joined = " ".join(normalize(t) for t in texts)
                itinerary = bus["itinerary"]
                extra_scores.append(sum(normalize(itinerary[k]) in joined for k in ("from", "to", "departure_time")) / 3)
            company_votes = sum(s >= 0.78 for s in company_scores)
            prefix_votes = sum(s >= 0.80 for s in prefix_scores)
            score = 0.35 * max(company_scores) + 0.55 * max(prefix_scores) + 0.10 * max(extra_scores)
            confirmed = (
                len(history) >= 3 and company_votes >= 2 and prefix_votes >= 2
                and score >= 0.82
            )
            ranked.append(Match(bus, score, company_votes, prefix_votes, confirmed))
        ranked.sort(key=lambda m: m.score, reverse=True)
        best = ranked[0]
        if best.score < 0.25:
            return None
        # Não escolha arbitrariamente entre viagens/veículos de pontuações próximas.
        if len(ranked) > 1 and best.score - ranked[1].score < 0.06:
            best.confirmed = False
        return best
