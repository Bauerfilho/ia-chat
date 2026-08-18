#!/usr/bin/env python3
"""Gates do iachat-doctor: o instrumento que separa "não" de "não sei".

Roda o binário real em subprocesso, com IACHAT_HOME/PATH/IACHAT_SCRIPTS
temporários; nunca toca a sala real nem a instalação de verdade. As asserções
são sobre o `--json` (machine-parseable por contrato), com uma checagem de
saída texto no fim.

Os casos que REPROVAM (✗ + exit 1) são a maioria de propósito: gate que nunca
viu vermelho não é gate. E há o gate gêmeo, igualmente importante: o que não
pôde ser medido sai ⚠ e NÃO reprova — fundir "não sei" em "não" foi a mentira
que este programa existe para enterrar.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "iachat-doctor"
falhas: list[str] = []

# Os 6 arquivos que install.sh:15-16 copia — o contrato que codigo-sincronizado mede.
BINARIOS = (
    "iachat",
    "iachat_core.py",
    "ia-bell-daemon.sh",
    "ia-bell-hook.sh",
    "ia-bell-install-daemon.sh",
    "ia-bell-install-hook.py",
)


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """Executa o binário real, sem importar nada de dentro dele."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def laudo(env: dict[str, str], *args: str) -> tuple[int, dict]:
    """Roda com --json e devolve (exit code, laudo parseado)."""
    r = roda(env, *args, "--json")
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, {"_erro": f"stdout não é JSON: {r.stdout[:200]} / {r.stderr[:200]}"}


def estado(laudo_json: dict, escopo: str, item: str) -> str | None:
    for i in laudo_json.get("itens", []):
        if i["escopo"] == escopo and i["item"] == item:
            return i["estado"]
    return None


def monta_sala(base: Path, msgs: int = 3, teto: int = 100000,
               config_extra: dict | None = None, config_sem: tuple[str, ...] = (),
               estado_ultima: int | None = None, padding: int = 0) -> Path:
    """Sala sintética completa e coerente (a menos que o teste peça o contrário)."""
    sala = base / "sala"
    for d in (".lock", "cursor", "pendente", "arquivo"):
        (sala / d).mkdir(parents=True, exist_ok=True)
    corpo = "".join(
        f"<!-- iachat msg={n} de=claude em=2026-08-17T20:0{n}:00-03:00 -->\n"
        f"## claude · 20:0{n}\n\nmensagem {n}\n\n" for n in range(1, msgs + 1)
    )
    corpo += "x" * padding
    (sala / "iachat.md").write_text(corpo, encoding="utf-8")
    cfg = {"na_sala": ["__teste__"], "brain": "__teste__",
           "teto_bytes": teto, "notificar_operador": True}
    for k in config_sem:
        cfg.pop(k, None)
    cfg.update(config_extra or {})
    (sala / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    if estado_ultima is not None:
        (sala / ".estado.json").write_text(
            json.dumps({"ultima": estado_ultima}) + "\n", encoding="utf-8")
    return sala


def fake_iachat(diretorio: Path, rc: int = 0) -> Path:
    """CLI de mentira: duas linhas no stdout (o doctor lê a 2ª) e o rc pedido."""
    alvo = diretorio / "iachat"
    alvo.write_text(
        "#!/bin/sh\n"
        'printf "chat      /fake/iachat.md\\ntamanho   100 B / 1000 B (10%% do teto)\\n"\n'
        f"exit {rc}\n",
        encoding="utf-8",
    )
    alvo.chmod(0o755)
    return alvo


def ambiente(base: Path, sala: Path, com_cli: bool = True) -> dict[str, str]:
    """PATH fechado: só o bin temporário + o sistema. O `iachat` real some daqui."""
    binario = base / "path-bin"
    binario.mkdir(parents=True, exist_ok=True)
    scripts = base / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    # O fallback de IACHAT_SCRIPTS existe sempre; com_cli controla só o PATH.
    if not (scripts / "iachat").exists():
        fake_iachat(scripts)
    if com_cli:
        fake_iachat(binario)
    return {
        **os.environ,
        "PATH": f"{binario}:/usr/bin:/bin",
        "IACHAT_HOME": str(sala),
        "IACHAT_SCRIPTS": str(scripts),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def monta_par_repo_scripts(base: Path, divergente: str | None = None) -> Path:
    """Repo e scripts sintéticos com os 6 binários do contrato de instalação."""
    repo = base / "repo"
    (repo / "bin").mkdir(parents=True, exist_ok=True)
    (base / "scripts").mkdir(parents=True, exist_ok=True)
    for nome in BINARIOS:
        (repo / "bin" / nome).write_text(f"conteudo {nome}\n", encoding="utf-8")
        copia = base / "scripts" / nome
        copia.write_text(
            f"conteudo {nome}\n" if nome != divergente else "DIVERGE\n",
            encoding="utf-8",
        )
    return repo


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-doctor-teste-"))
    try:
        checa("binário novo é executável", CLI.is_file() and os.access(CLI, os.X_OK), str(CLI))

        # ---- D1: sala sã ⇒ sem ✗, exit 0 ------------------------------------
        sala = monta_sala(base / "d1", msgs=3, estado_ultima=3)
        env = ambiente(base / "d1", sala)
        rc, j = laudo(env)
        checa(
            "D1 sala sã: exit 0 e bloco sala todo ✓",
            rc == 0
            and j.get("placar", {}).get("falhou") == 0
            and all(estado(j, "sala", i) == "ok" for i in
                    ("sala-estrutura", "sala-integra", "sala-config", "sala-teto",
                     "cli-no-path", "cli-responde")),
            f"rc={rc} placar={j.get('placar')}",
        )
        checa(
            "D1 sem --repo: codigo-sincronizado é ⚠, nunca ✓ por omissão",
            estado(j, "sala", "codigo-sincronizado") == "?",
            f"estado={estado(j, 'sala', 'codigo-sincronizado')}",
        )
        checa(
            "D1 casca fora do registro vira ⚠ e não reprova",
            estado(j, "casca:__teste__", "registro") == "?"
            and estado(j, "sala", "sala-config") == "ok",
            f"registro={estado(j, 'casca:__teste__', 'registro')}",
        )

        # ---- D2 (REPROVA): estrutura incompleta ⇒ ✗ + exit 1 ------------------
        sala2 = monta_sala(base / "d2", msgs=1, estado_ultima=1)
        shutil.rmtree(sala2 / "pendente")
        (sala2 / "config.json").unlink()
        rc2, j2 = laudo(ambiente(base / "d2", sala2))
        checa(
            "D2 REPROVA estrutura incompleta: sala-estrutura ✗ e exit 1",
            rc2 == 1 and estado(j2, "sala", "sala-estrutura") == "falhou",
            f"rc={rc2} estado={estado(j2, 'sala', 'sala-estrutura')}",
        )

        # ---- D3 (REPROVA): contador mente ⇒ sala-integra ✗ --------------------
        sala3 = monta_sala(base / "d3", msgs=3, estado_ultima=9)
        rc3, j3 = laudo(ambiente(base / "d3", sala3))
        checa(
            "D3 REPROVA .estado.json divergente do chat",
            rc3 == 1 and estado(j3, "sala", "sala-integra") == "falhou",
            f"rc={rc3}",
        )

        # ---- D4: .estado.json AUSENTE é ⚠ (sala nova), não ✗ -----------------
        sala4 = monta_sala(base / "d4", msgs=2, estado_ultima=None)
        rc4, j4 = laudo(ambiente(base / "d4", sala4))
        checa(
            "D4 cache ausente vira ⚠ e não reprova (falso ✗ aqui é alarme falso)",
            rc4 == 0 and estado(j4, "sala", "sala-integra") == "?",
            f"rc={rc4} estado={estado(j4, 'sala', 'sala-integra')}",
        )

        # ---- D5 (REPROVA): config sem na_sala ⇒ ✗; só sem teto_bytes ⇒ ✓ -----
        sala5 = monta_sala(base / "d5a", msgs=1, estado_ultima=1, config_sem=("na_sala",))
        rc5, j5 = laudo(ambiente(base / "d5a", sala5))
        checa(
            "D5 REPROVA config sem na_sala (entrega dirigida morre em silêncio)",
            rc5 == 1 and estado(j5, "sala", "sala-config") == "falhou",
            f"rc={rc5}",
        )
        sala5b = monta_sala(base / "d5b", msgs=1, estado_ultima=1,
                            config_sem=("teto_bytes",))
        rc5b, j5b = laudo(ambiente(base / "d5b", sala5b))
        checa(
            "D5 sem teto_bytes cai em fallback consistente: ✓, não ✗ "
            "(o defeito dos 3 defaults foi corrigido no core em 17/08)",
            rc5b == 0 and estado(j5b, "sala", "sala-config") == "ok",
            f"rc={rc5b} estado={estado(j5b, 'sala', 'sala-config')}",
        )

        # ---- D6 (REPROVA): chat ≥ 90% do teto ⇒ sala-teto ✗ -------------------
        sala6 = monta_sala(base / "d6", msgs=1, teto=1000, estado_ultima=1,
                           padding=950)
        rc6, j6 = laudo(ambiente(base / "d6", sala6))
        checa(
            "D6 REPROVA chat a 95% do teto",
            rc6 == 1 and estado(j6, "sala", "sala-teto") == "falhou",
            f"rc={rc6}",
        )

        # ---- D7 (REPROVA): CLI fora do PATH ⇒ cli-no-path ✗ -------------------
        sala7 = monta_sala(base / "d7", msgs=1, estado_ultima=1)
        env7 = ambiente(base / "d7", sala7, com_cli=False)
        rc7, j7 = laudo(env7)
        checa(
            "D7 REPROVA iachat fora do PATH — e cli-responde mede o fallback "
            "de IACHAT_SCRIPTS independente",
            rc7 == 1
            and estado(j7, "sala", "cli-no-path") == "falhou"
            and estado(j7, "sala", "cli-responde") == "ok",
            f"rc={rc7} path={estado(j7, 'sala', 'cli-no-path')} "
            f"responde={estado(j7, 'sala', 'cli-responde')}",
        )

        # ---- D8 (REPROVA): CLI quebra ⇒ cli-responde ✗ ------------------------
        sala8 = monta_sala(base / "d8", msgs=1, estado_ultima=1)
        env8 = ambiente(base / "d8", sala8)
        fake_iachat(base / "d8" / "path-bin", rc=3)
        rc8, j8 = laudo(env8)
        checa(
            "D8 REPROVA CLI que sai rc=3",
            rc8 == 1 and estado(j8, "sala", "cli-responde") == "falhou",
            f"rc={rc8}",
        )

        # ---- D9: sala inexistente ⇒ ⚠ honesto e ZERO escrita ------------------
        sala9 = base / "d9" / "sala-que-nao-existe"
        env9 = ambiente(base / "d9", sala9)
        rc9, j9 = laudo(env9)
        checa(
            "D9 sala inexistente: cli-responde ⚠ (não rodou para não criar), "
            "estrutura ✗, exit 1",
            rc9 == 1
            and estado(j9, "sala", "cli-responde") == "?"
            and estado(j9, "sala", "sala-estrutura") == "falhou",
            f"rc={rc9}",
        )
        checa(
            "D9 o diagnóstico NÃO criou a sala (auditor não é autor)",
            not sala9.exists(),
            f"exists={sala9.exists()}",
        )

        # ---- D10: --json é machine-parseable e todo item tem `como` -----------
        sala10 = monta_sala(base / "d10", msgs=1, estado_ultima=1)
        rc10, j10 = laudo(ambiente(base / "d10", sala10))
        itens = j10.get("itens", [])
        checa(
            "D10 laudo JSON: placar de 3 desfechos e `como` auditável em todo item",
            rc10 == 0
            and set(j10.get("placar", {})) == {"ok", "falhou", "?"}
            and itens
            and all(i.get("como") for i in itens)
            and all(i["estado"] in ("ok", "falhou", "?") for i in itens),
            f"itens={len(itens)} placar={j10.get('placar')}",
        )

        # ---- D11: saída texto fecha com o placar dos três números -------------
        r11 = roda(ambiente(base / "d10", sala10))
        checa(
            "D11 saída texto termina em PLACAR com os três desfechos separados",
            "PLACAR" in r11.stdout and "✗ falhou" in r11.stdout
            and "⚠ não-consegui-verificar" in r11.stdout,
            f"ultima linha={r11.stdout.strip().splitlines()[-1][:60]}",
        )

        # ---- D12 (REPROVA): instalado diverge do repo ⇒ sync ✗ ----------------
        sala12 = monta_sala(base / "d12", msgs=1, estado_ultima=1)
        repo12 = monta_par_repo_scripts(base / "d12", divergente="iachat_core.py")
        env12 = ambiente(base / "d12", sala12)
        rc12, j12 = laudo(env12, "--repo", str(repo12))
        checa(
            "D12 REPROVA bin divergente entre repo e instalado",
            rc12 == 1 and estado(j12, "sala", "codigo-sincronizado") == "falhou",
            f"rc={rc12}",
        )
        repo12b = monta_par_repo_scripts(base / "d12b")
        rc12b, j12b = laudo(ambiente(base / "d12b", sala12), "--repo", str(repo12b))
        checa(
            "D12 pares idênticos ⇒ codigo-sincronizado ✓",
            estado(j12b, "sala", "codigo-sincronizado") == "ok",
            f"estado={estado(j12b, 'sala', 'codigo-sincronizado')}",
        )

        # ---- D13 (REPROVA): CLI do repo fora do PATH ⇒ clis-do-repo ✗ ---------
        sala13 = monta_sala(base / "d13", msgs=1, estado_ultima=1)
        repo13 = monta_par_repo_scripts(base / "d13")
        cli_novo = repo13 / "bin" / "iachat-claim"
        cli_novo.write_text("#!/usr/bin/env python3\nprint('claim')\n", encoding="utf-8")
        cli_novo.chmod(0o755)
        env13 = ambiente(base / "d13", sala13)
        rc13, j13 = laudo(env13, "--repo", str(repo13))
        checa(
            "D13 REPROVA iachat-claim no repo sem resolução no PATH "
            "(a skill chama pelo nome — install.sh:15-16 não o instala)",
            rc13 == 1 and estado(j13, "sala", "clis-do-repo") == "falhou",
            f"rc={rc13}",
        )
        link = base / "d13" / "path-bin" / "iachat-claim"
        link.symlink_to(cli_novo)
        rc13b, j13b = laudo(env13, "--repo", str(repo13))
        checa(
            "D13 CLI linkado ⇒ clis-do-repo ✓ (o ✗ virou ✓ por mudança medida)",
            rc13b == 0 and estado(j13b, "sala", "clis-do-repo") == "ok",
            f"rc={rc13b} estado={estado(j13b, 'sala', 'clis-do-repo')}",
        )

        # ---- D14: --repo inválido ⇒ exit 2 (o diagnóstico não começou) --------
        r14 = roda(ambiente(base / "d13", sala13), "--repo", str(base / "sem-bin"))
        checa(
            "D14 --repo sem bin/ aborta com exit 2, não com laudo inventado",
            r14.returncode == 2,
            f"rc={r14.returncode}",
        )

        print()
        print("✅ IA-DOCTOR PASSOU" if not falhas else f"❌ IA-DOCTOR REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
