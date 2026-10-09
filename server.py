# -*- coding: utf-8 -*-
"""
Веб-сервер калькулятора точных критериев 2×2
Только стандартная библиотека + numpy/scipy (exact_tests_core).

Запуск:
    python server.py
    → http://127.0.0.1:8080
"""

from __future__ import annotations

import json
import math
import os
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ядро расчётов лежит на уровень выше
ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
sys.path.insert(0, PARENT)
sys.path.insert(0, ROOT)

from exact_tests_core import calculate_all, _fmt_or, _fmt_num  # noqa: E402

HOST = os.environ.get("HOST", "0.0.0.0")  # 0.0.0.0 for Render/Railway
PORT = int(os.environ.get("PORT", "8080"))
STATIC_DIR = os.path.join(ROOT, "static")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = ROOT  # files in same folder as server.py

def _json_safe(obj):
    """Преобразует nan/inf в JSON-совместимые значения."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return None
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    return obj


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/calculate":
            return self._api_calculate()
        self.send_error(404, "Not Found")

    def _api_calculate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8"))

            a = int(data["a"])
            b = int(data["b"])
            c = int(data["c"])
            d = int(data["d"])
            alternative = data.get("alternative", "two-sided")
            groups = data.get("groups", "auto")
            design = data.get("design", "independent")

            if min(a, b, c, d) < 0:
                raise ValueError("Все значения должны быть ≥ 0")
            if a + b + c + d == 0:
                raise ValueError("Таблица не может состоять только из нулей")
            if alternative not in ("two-sided", "less", "greater"):
                raise ValueError("Некорректная альтернатива")
            if groups not in ("auto", "rows", "columns"):
                raise ValueError("Некорректная ориентация групп")
            if design not in ("independent", "paired", "unknown"):
                raise ValueError("Некорректный дизайн данных")

            result = calculate_all(a, b, c, d, alternative, groups, design=design)

            # удобные строки для UI
            result["fmt"] = {
                "sample_or": _fmt_or(result["sample_or"]),
                "woolf_or": _fmt_or(result["or"]),
                "fisher_or": _fmt_or(result["fisher_or"]),
                "fisher_p": _fmt_num(result["fisher_p"], 10),
                "mid_p": _fmt_num(result["mid_p"], 10),
                "barnard_p": _fmt_num(result["barnard_p"], 10),
                "barnard_stat": _fmt_num(result["barnard_stat"]),
                "boschloo_p": _fmt_num(result["boschloo_p"], 10),
                "boschloo_stat": _fmt_num(result["boschloo_stat"], 10),
                "chi2": _fmt_num(result["chi2"]),
                "chi2_p": _fmt_num(result["chi2_p"], 10),
                "yates": _fmt_num(result["yates"]),
                "yates_p": _fmt_num(result["yates_p"], 10),
                "mcnemar_exact_p": _fmt_num(result["mcnemar_exact_p"], 10),
                "mcnemar_chi2": _fmt_num(result["mcnemar_chi2"]),
                "mcnemar_chi2_p": _fmt_num(result["mcnemar_chi2_p"], 10),
                "mcnemar_corr": _fmt_num(result["mcnemar_corr"]),
                "mcnemar_corr_p": _fmt_num(result["mcnemar_corr_p"], 10),
                "ci_low": f"{result['ci_low']:.8f}",
                "ci_high": f"{result['ci_high']:.8f}",
            }
            result["table"] = {
                "a": a, "b": b, "c": c, "d": d,
                "row1": a + b, "row2": c + d,
                "col1": a + c, "col2": b + d,
                "n": a + b + c + d,
            }

            payload = _json_safe({"ok": True, "result": result})
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = {"ok": False, "error": str(e), "trace": traceback.format_exc()}
            body = json.dumps(err, ensure_ascii=False).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    os.chdir(STATIC_DIR)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"СтатПоиск:  http://{HOST}:{PORT}/")
    print("Остановка: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")
        server.server_close()


if __name__ == "__main__":
    main()
