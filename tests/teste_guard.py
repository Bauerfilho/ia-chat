#!/usr/bin/env python3
"""Gates do ia-guard e do ia-budget.

Dois instrumentos da mesma família (disciplina de escrita), um arquivo de
teste — a fronteira do executor só autoriza `tests/teste_guard.py`.

Roda as CLIs em subprocesso e usa IACHAT_HOME temporário; nunca toca a
sala real. Inclui o caso que REPROVA: se o porteiro devolver OK numa
mensagem com caminho inexistente, o gate cai. Gate que nunca viu vermelho
não é gate.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
GUARD = BIN / "iachat-guard"
BUDGET = BIN / "iachat-budget"
sys.path.insert(0, str(BIN))

falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def carrega(caminho: Path, nome: str):
    """Carrega CLI sem sufixo .py (os binários do plugin não têm extensão)."""
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def roda(env: dict[str, str], cli: Path, *args: str, stdin: str | None = None):
    return subprocess.run(
        [sys.executable, str(cli), *args],
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
    )


def main() -> int:
    guard = carrega(GUARD, "iachat_guard")
    budget = carrega(BUDGET, "iachat_budget")
    import iachat_core as core

    base = Path(tempfile.mkdtemp(prefix="iachat-guard-teste-"))
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # Isola o import do núcleo já feito: o core lê IACHAT_HOME a cada chamada.
    os.environ["IACHAT_HOME"] = str(base)

    try:
        checa("G0 CLI guard é executável", GUARD.is_file() and os.access(GUARD, os.X_OK), str(GUARD))
        checa("G0 CLI budget é executável", BUDGET.is_file() and os.access(BUDGET, os.X_OK), str(BUDGET))

        # ---- prova de fogo: o porteiro TEM que ver vermelho --------------------
        fantasma = "/Users/bauervieiracesarfilhovieira/Projetos/ia-chat/bin/iachat_bell.py"
        r = guard.avaliar(
            f"Arrumei o bug. O patch está em {fantasma}.",
            ultima_msg=16,
        )
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-V1 caminho inexistente é P1 (o caso que REPROVA)",
            r["pior"] == "P1" and "V1" in ids,
            f"pior={r['pior']} ids={ids}",
        )
        cli_v1 = roda(env, GUARD, "--texto", f"O patch está em {fantasma}.")
        checa(
            "G-V1 CLI exit 1 no P1",
            cli_v1.returncode == 1 and "V1" in cli_v1.stdout,
            f"rc={cli_v1.returncode} out={cli_v1.stdout[:80]!r}",
        )

        alvo = base / "cinco_linhas.py"
        alvo.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
        r = guard.avaliar(
            f"O teto está em {alvo}:9999 — muda lá.",
            ultima_msg=16,
        )
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-V2 linha além do fim é P1",
            r["pior"] == "P1" and "V2" in ids,
            f"pior={r['pior']} ids={ids}",
        )

        r = guard.avaliar("Como combinamos na #4242, deixei o daemon parado.", ultima_msg=16)
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-V3 #N impossível é P1",
            r["pior"] == "P1" and "V3" in ids,
            f"pior={r['pior']} ids={ids}",
        )

        r = guard.avaliar(
            "Resolvi aquele problema do daemon; se voltar é só repetir.",
            ultima_msg=16,
        )
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-L1 deixis sem antecedente é P2 (não P1)",
            r["pior"] == "P2" and "L1" in ids,
            f"pior={r['pior']} ids={ids}",
        )

        r = guard.avaliar("Testei e está tudo certo do meu lado, pode seguir.", ultima_msg=16)
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-L2 aferição sem medida é P2",
            r["pior"] == "P2" and "L2" in ids,
            f"pior={r['pior']} ids={ids}",
        )

        r = guard.avaliar(
            "Preciso de você: instale o hook aí na sua casca e me avisa.",
            ultima_msg=16,
        )
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-L3 pedido sem comando é P2",
            r["pior"] == "P2" and "L3" in ids,
            f"pior={r['pior']} ids={ids}",
        )

        boa = (
            f"Fechei a fase 5. Prova: `python3 {RAIZ / 'tests' / 'teste_rotacao.py'}` "
            f"→ 3 gates verdes; o recorte saiu em {base} e a função é "
            f"`{alvo}:3`. Confere do teu lado com `iachat status`."
        )
        r = guard.avaliar(boa, ultima_msg=16)
        checa(
            "G-P0 mensagem boa passa limpa",
            r["pior"] == "OK" and not r["achados"],
            f"pior={r['pior']} ids={[a['id'] for a in r['achados']]}",
        )

        r = guard.avaliar("Rode `/reload` e depois `/ia-chat-activate`.", ultima_msg=16)
        ids = [a["id"] for a in r["achados"]]
        checa(
            "G-slash-command /reload NÃO é V1",
            "V1" not in ids,
            f"ids={ids}",
        )

        # Tamanho é dado, não veredito: 3 KB densos passam.
        densa = (
            f"Medi 16 mensagens em {base}: 24757 B, densidade 12.6/KB. "
            f"Comando: `iachat status`. Função `{alvo}:2`. Ref #1.\n"
        ) * 8
        r = guard.avaliar(densa, ultima_msg=16)
        checa(
            "G-tamanho grande e denso NÃO reprova",
            r["metricas"]["bytes"] > 2048 and r["pior"] in {"OK", "P2"},
            f"bytes={r['metricas']['bytes']} pior={r['pior']} d={r['metricas']['densidade']}",
        )

        cli_vazio = roda(env, GUARD, "--texto", "   ")
        checa("G-vazio exit 2", cli_vazio.returncode == 2, f"rc={cli_vazio.returncode}")

        # Ensaio NÃO cria a sala.
        casa_nova = Path(tempfile.mkdtemp(prefix="iachat-guard-ensaio-"))
        env_nova = {**env, "IACHAT_HOME": str(casa_nova)}
        shutil.rmtree(casa_nova)
        checa("G-ensaio casa ainda não existe", not casa_nova.exists())
        cli_ensaio = roda(env_nova, GUARD, "--texto", "ping de ensaio sem sala")
        checa(
            "G-ensaio não cria IACHAT_HOME",
            not casa_nova.exists() and cli_ensaio.returncode == 0,
            f"existe={casa_nova.exists()} rc={cli_ensaio.returncode}",
        )
        if casa_nova.exists():
            shutil.rmtree(casa_nova, ignore_errors=True)

        cli_p2 = roda(env, GUARD, "--texto", "Testei e está tudo certo.")
        checa(
            "G-P2 CLI exit 0 (não barra suspeita)",
            cli_p2.returncode == 0 and "L2" in cli_p2.stdout,
            f"rc={cli_p2.returncode}",
        )

        # ---- budget: sala sintética ------------------------------------------
        core.garantir_estrutura()
        core.p_config().write_text(
            json.dumps(
                {
                    "na_sala": ["claude", "codex", "kimi"],
                    "brain": "claude",
                    "teto_bytes": 20480,
                    "cota_diaria_bytes": 8000,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        # Recria o módulo de budget? Não precisa: ele relê config a cada chamada.
        corpo = "x" * 400
        core.post("claude", f"@codex @kimi multicast {corpo}")
        core.post("claude", f"@codex unicast {corpo}")
        core.post("kimi", f"sem nominação {corpo}")
        core.post("codex", f"@claude resposta curta")

        msgs = budget.coletar()
        por = budget.contas(msgs, ["claude", "codex", "kimi"])
        checa(
            "B-identidade imposto == recebido",
            budget.identidade(msgs)
            and sum(x["imposto"] for x in por.values())
            == sum(x["recebido"] for x in por.values()),
            f"imposto={sum(x['imposto'] for x in por.values())} "
            f"recebido={sum(x['recebido'] for x in por.values())}",
        )

        multi = next(m for m in msgs if m["n"] == 1)
        checa(
            "B-multicast 2 destinos cobra 2×",
            len(multi["para"]) == 2 and multi["imposto"] == multi["escrito"] * 2,
            f"para={multi['para']} imposto={multi['imposto']} escrito={multi['escrito']}",
        )

        solta = next(m for m in msgs if m["n"] == 3)
        checa(
            "B-sem nominação imposto é 0",
            solta["imposto"] == 0 and solta["escrito"] > 0,
            f"imposto={solta['imposto']} escrito={solta['escrito']}",
        )

        mtime_antes = (
            core.p_chat().stat().st_mtime_ns,
            core.p_config().stat().st_mtime_ns,
        )
        rep = roda(env, BUDGET, "report", "--json")
        mtime_depois = (
            core.p_chat().stat().st_mtime_ns,
            core.p_config().stat().st_mtime_ns,
        )
        checa("B-report exit 0", rep.returncode == 0, f"rc={rep.returncode} err={rep.stderr[:80]!r}")
        checa(
            "B-report não escreve na sala",
            mtime_antes == mtime_depois,
            f"antes={mtime_antes} depois={mtime_depois}",
        )
        dados = json.loads(rep.stdout)
        checa(
            "B-report json fecha identidade",
            dados.get("identidade_ok") is True,
            f"identidade_ok={dados.get('identidade_ok')}",
        )
        checa(
            "B-cota vem do config (8000)",
            dados.get("cota_diaria") == 8000
            and "cota_diaria_bytes" in dados.get("origem_cota", ""),
            f"cota={dados.get('cota_diaria')} origem={dados.get('origem_cota')}",
        )

        # check verde: silêncio, exit 0
        chk_verde = roda(env, BUDGET, "check", "--de", "codex", "--tamanho", "10", "--destinos", "1")
        checa(
            "B-check verde é silêncio e exit 0",
            chk_verde.returncode == 0 and chk_verde.stdout == "" and chk_verde.stderr == "",
            f"rc={chk_verde.returncode} out={chk_verde.stdout!r} err={chk_verde.stderr!r}",
        )

        # check vermelho: avisa, NÃO bloqueia
        chk_verm = roda(
            env,
            BUDGET,
            "check",
            "--de",
            "claude",
            "--tamanho",
            "9000",
            "--destinos",
            "2",
        )
        checa(
            "B-check vermelho avisa e exit 0 (nunca bloqueia)",
            chk_verm.returncode == 0 and "estourou" in chk_verm.stderr,
            f"rc={chk_verm.returncode} err={chk_verm.stderr[:120]!r}",
        )

        # destinos 0 honrado (correção da proposta: max(1, destinos) mentia)
        chk0 = roda(
            env,
            BUDGET,
            "check",
            "--de",
            "kimi",
            "--tamanho",
            "5000",
            "--destinos",
            "0",
            "--json",
        )
        d0 = json.loads(chk0.stdout)
        checa(
            "B-check destinos 0 não inventa 1×",
            chk0.returncode == 0 and d0["destinos"] == 0 and d0["projetado"] == d0["gasto"],
            f"destinos={d0.get('destinos')} projetado={d0.get('projetado')} gasto={d0.get('gasto')}",
        )

        # --texto infere destinos pelos @
        chk_txt = roda(
            env,
            BUDGET,
            "check",
            "--de",
            "claude",
            "--texto",
            "@codex @kimi resumo em /tmp/x.md",
            "--json",
        )
        dt = json.loads(chk_txt.stdout)
        checa(
            "B-check --texto infere 2 destinos",
            dt.get("destinos") == 2 and dt.get("tamanho") == len("@codex @kimi resumo em /tmp/x.md".encode()),
            f"destinos={dt.get('destinos')} tamanho={dt.get('tamanho')}",
        )

        # sobrevive à rotação: totais iguais antes e depois
        antes_tot = (dados["total_escrito"], dados["total_imposto"])
        core.p_config().write_text(
            json.dumps(
                {
                    "na_sala": ["claude", "codex", "kimi"],
                    "brain": "claude",
                    "teto_bytes": 800,
                    "cota_diaria_bytes": 8000,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rot = core.rotate(forcar=True)
        recortes = list((base / "arquivo").glob("*.md"))
        depois = json.loads(roda(env, BUDGET, "report", "--json").stdout)
        checa(
            "B-rotação: recorte existe e totais não mudam",
            bool(rot.get("rodou"))
            and recortes
            and (depois["total_escrito"], depois["total_imposto"]) == antes_tot,
            f"rodou={rot.get('rodou')} recortes={len(recortes)} "
            f"antes={antes_tot} depois=({depois.get('total_escrito')},{depois.get('total_imposto')})",
        )

        # skills com frontmatter mínimo
        for nome in ("ia-guard", "ia-budget"):
            skill = (RAIZ / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
            checa(
                f"D-{nome} SKILL.md tem name+description e o comando real",
                skill.startswith("---")
                and f"name: {nome}" in skill
                and "description:" in skill
                and f"iachat-{nome.split('-', 1)[1]}" in skill,
                f"head={skill.splitlines()[:4]}",
            )

        print()
        print("✅ IA-GUARD+BUDGET PASSOU" if not falhas else f"❌ IA-GUARD+BUDGET REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
