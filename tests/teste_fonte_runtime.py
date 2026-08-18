#!/usr/bin/env python3
"""Prova o gate de fonte única nos dois lados, sem tocar na instalação real.

O cenário mais importante não é uma cópia velha parada no disco. É um Python que
já compilou ``servir.py`` e continua vivo enquanto o arquivo foi atualizado. O teste
sobe exatamente esse caso num diretório temporário: processo antigo, fonte nova.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional


RAIZ = Path(__file__).resolve().parent.parent
GATE = RAIZ / "bin/iachat-fontes"

_ok = 0
_falhou = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if condicao:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        sufixo = f"\n      {detalhe}" if detalhe else ""
        print(f"  ✗ {nome}{sufixo}")


SERVIDOR_ANTIGO = r'''#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

UI = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def responder(self, status, corpo, tipo="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/estado":
            return self.responder(200, b'{"ultima": 0}')
        # Esta revisão ainda NÃO conhece /api/groupchat.
        nomes = {"/": "index.html", "/estilo.css": "estilo.css", "/sala.js": "sala.js"}
        if u.path in nomes:
            corpo = (UI / nomes[u.path]).read_bytes()
            tipo = "text/html" if u.path == "/" else "text/plain"
            return self.responder(200, corpo, tipo)
        return self.responder(404, b'{"erro": "rota inexistente"}')

ap = argparse.ArgumentParser()
ap.add_argument("--porta", type=int, required=True)
a = ap.parse_args()
ThreadingHTTPServer(("127.0.0.1", a.porta), Handler).serve_forever()
'''


SERVIDOR_NOVO = r'''#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

UI = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def responder(self, status, corpo, tipo="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/estado":
            return self.responder(200, b'{"ultima": 0}')
        if u.path == "/api/groupchat":
            return self.responder(200, b'{"sessions": [], "snapshots": [], "msgs": []}')
        nomes = {"/": "index.html", "/estilo.css": "estilo.css", "/sala.js": "sala.js"}
        if u.path in nomes:
            corpo = (UI / nomes[u.path]).read_bytes()
            tipo = "text/html" if u.path == "/" else "text/plain"
            return self.responder(200, corpo, tipo)
        return self.responder(404, b'{"erro": "rota inexistente"}')

ap = argparse.ArgumentParser()
ap.add_argument("--porta", type=int, required=True)
a = ap.parse_args()
ThreadingHTTPServer(("127.0.0.1", a.porta), Handler).serve_forever()
'''


def escrever(caminho: Path, conteudo: str, modo: Optional[int] = None) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    if modo is not None:
        caminho.chmod(modo)


def copiar_ui(ui: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ("index.html", "estilo.css", "sala.js", "servir.py"):
        shutil.copy2(ui / nome, destino / nome)


def montar_fixture(base: Path, servidor: str = SERVIDOR_NOVO) -> Dict[str, Path]:
    """Cria as quatro cópias mínimas que o gate conhece, todas sincronizadas."""
    core = base / "ia-chat"
    app = base / "ia-chat-app"
    scripts = base / "instalado/scripts"
    bin_dir = base / "instalado/bin"
    app_instalado = base / "Applications/ia-chat.app"

    escrever(core / "bin/iachat", "#!/bin/sh\nexit 0\n", 0o755)
    escrever(core / "bin/iachat_core.py", "VALOR = 1\n", 0o644)
    scripts.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    shutil.copy2(core / "bin/iachat", scripts / "iachat")
    shutil.copy2(core / "bin/iachat_core.py", scripts / "iachat_core.py")
    (bin_dir / "iachat").symlink_to(scripts / "iachat")

    ui = app / "ui"
    escrever(ui / "index.html", "<!doctype html><title>fonte única</title>\n")
    escrever(ui / "estilo.css", "body { color: #123; }\n")
    escrever(ui / "sala.js", "window.FONTE_UNICA = true;\n")
    escrever(ui / "servir.py", servidor, 0o755)
    copiar_ui(ui, app / "ia-chat.app/Contents/Resources/ui")
    copiar_ui(ui, app_instalado / "Contents/Resources/ui")

    return {
        "core": core,
        "app": app,
        "scripts": scripts,
        "bin": bin_dir,
        "app_instalado": app_instalado,
        "ui": ui,
    }


def ambiente(f: Dict[str, Path]) -> dict:
    return dict(
        os.environ,
        IACHAT_REPO=str(f["core"]),
        IACHAT_APP_REPO=str(f["app"]),
        IACHAT_SCRIPTS=str(f["scripts"]),
        IACHAT_BIN=str(f["bin"]),
        IACHAT_APP_INSTALLED=str(f["app_instalado"]),
        IACHAT_PORTS="",
    )


def gate(f: Dict[str, Path], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        env=ambiente(f),
        cwd=str(f["core"]),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def aguardar_servidor(porta: int) -> bool:
    limite = time.time() + 8
    while time.time() < limite:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{porta}/api/estado", timeout=1
            ) as resposta:
                return resposta.status == 200
        except OSError:
            time.sleep(0.1)
    return False


def encerrar(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def teste_copias(base: Path) -> None:
    print("— cópias sincronizadas passam —")
    f = montar_fixture(base / "copias")
    r = gate(f, "--somente-copias", "--json")
    checa("gate sincronizado sai 0", r.returncode == 0, r.stdout + r.stderr)
    try:
        dado = json.loads(r.stdout)
    except ValueError as exc:
        dado = {"erro": str(exc)}
    checa("laudo JSON declara PASS", dado.get("resultado") == "PASS", repr(dado)[:300])

    print("— touch não finge divergência —")
    alvo_touch = f["app"] / "ia-chat.app/Contents/Resources/ui/sala.js"
    os.utime(alvo_touch, None)
    r_touch = gate(f, "--somente-copias")
    checa("mtime diferente com bytes iguais continua PASS", r_touch.returncode == 0,
          r_touch.stdout + r_touch.stderr)

    print("— cópia alterada reprova e ensina —")
    bundle = f["app"] / "ia-chat.app/Contents/Resources/ui/sala.js"
    original = bundle.read_bytes()
    bundle.write_bytes(original + b"// divergencia deliberada\n")
    r_ruim = gate(f, "--somente-copias")
    checa("bundle divergente sai vermelho", r_ruim.returncode == 1,
          r_ruim.stdout + r_ruim.stderr)
    checa("erro ensina ./montar.sh", "./montar.sh" in r_ruim.stdout, r_ruim.stdout)
    bundle.write_bytes(original)
    checa("restaurado byte a byte", bundle.read_bytes() == original)
    r_restaurado = gate(f, "--somente-copias")
    checa("depois de desfazer volta a PASS", r_restaurado.returncode == 0,
          r_restaurado.stdout + r_restaurado.stderr)

    print("— instalação alterada aponta o instalador certo —")
    instalado = f["scripts"] / "iachat_core.py"
    original_instalado = instalado.read_bytes()
    instalado.write_bytes(b"VALOR = 0\n")
    r_instalado = gate(f, "--somente-copias")
    checa("script instalado divergente reprova", r_instalado.returncode == 1,
          r_instalado.stdout + r_instalado.stderr)
    checa("erro ensina ./install.sh", "./install.sh" in r_instalado.stdout,
          r_instalado.stdout)
    instalado.write_bytes(original_instalado)

    print("— app instalado alterado aponta atualização —")
    css = f["app_instalado"] / "Contents/Resources/ui/estilo.css"
    css_original = css.read_bytes()
    css.write_bytes(css_original + b"/* velho */\n")
    r_app = gate(f, "--somente-copias")
    checa("app instalado divergente reprova", r_app.returncode == 1,
          r_app.stdout + r_app.stderr)
    checa("erro ensina --atualizar", "./instalar-app.sh --atualizar" in r_app.stdout,
          r_app.stdout)
    css.write_bytes(css_original)


def teste_processo_velho(base: Path) -> None:
    print("— processo vivo com código velho reprova —")
    f = montar_fixture(base / "processo", SERVIDOR_ANTIGO)
    porta = porta_livre()
    log = base / "processo-servidor.log"
    with log.open("wb") as saida:
        proc = subprocess.Popen(
            [sys.executable, "-u", str(f["ui"] / "servir.py"), "--porta", str(porta)],
            cwd=str(f["app"]),
            stdout=saida,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    try:
        checa("controle: servidor antigo realmente subiu", aguardar_servidor(porta),
              log.read_text(encoding="utf-8", errors="replace"))

        # Dois segundos separam inequivocamente o start da regravação no `ps etime`.
        time.sleep(2.2)
        escrever(f["ui"] / "servir.py", SERVIDOR_NOVO, 0o755)
        copiar_ui(f["ui"], f["app"] / "ia-chat.app/Contents/Resources/ui")
        copiar_ui(f["ui"], f["app_instalado"] / "Contents/Resources/ui")

        r = gate(f, "--processo", f"{proc.pid}:{porta}")
        saida_gate = r.stdout + r.stderr
        checa("processo velho sai vermelho", r.returncode == 1, saida_gate)
        checa("a rota nova ausente no vivo é detectada",
              "processo vivo responde rota inexistente" in saida_gate, saida_gate)
        checa("a regravação posterior ao start é detectada",
              "arquivo foi regravado após o start" in saida_gate, saida_gate)
        checa("o erro manda reiniciar o servidor",
              f"reinicie o servidor da porta {porta}" in saida_gate, saida_gate)
        checa("a limitação criptográfica não é escondida",
              "LIMITAÇÃO DECLARADA" in saida_gate, saida_gate)
    finally:
        encerrar(proc)


def main() -> int:
    print("teste_fonte_runtime")
    checa("o gate existe", GATE.is_file(), str(GATE))
    checa("o gate é executável", os.access(str(GATE), os.X_OK), str(GATE))
    with tempfile.TemporaryDirectory(prefix="iachat-fonte-runtime-") as bruto:
        base = Path(bruto)
        teste_copias(base)
        teste_processo_velho(base)

    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
