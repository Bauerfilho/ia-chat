#!/usr/bin/env python3
"""Gates dos comandos do dono: goal · plan · concluir · parar · quem · decidi · refaz.

Tudo roda em ``IACHAT_HOME`` temporário, com um despachante FALSO (``IACHAT_DESPACHO``):
nenhuma IA da frota é acionada e nenhum plano é pago. Os processos que o teste mata são
dele mesmo — ``sleep`` nascidos do despachante falso, dentro do diretório temporário.

Os casos que precisam REPROVAR estão marcados ``T-RED``. O que mais importa é o
``T-RED 2``: com o PID reciclado, o ``parar`` tem que RECUSAR e o processo tem que
CONTINUAR VIVO. Matar processo errado é o pior desfecho possível deste comando.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CMD = RAIZ / "bin" / "iachat-comando"
DESPACHO = RAIZ / "bin" / "iachat-despacho.sh"
DECIDE = RAIZ / "bin" / "iachat-decide"
falhas: list[str] = []
faxina: list[int] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  ‣ {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


# Subcomandos que assinam mensagem na sala. Sem TTY e sem `--de`, o comando RECUSA
# em vez de assinar como o dono (`autor()`, bin/iachat-comando) — e o teste
# roda por subprocesso, que é exatamente o caso sem TTY que a guarda existe para pegar.
# Declarar o autor aqui, num lugar só, mantém os testes medindo o gate que eles querem
# medir; quem quer provar a própria guarda passa `--de` (ou a ausência dele) de propósito.
ASSINAM = {"goal", "plan", "concluir", "parar", "decidi"}


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """A mesma porta pública que o dono usa no terminal."""
    argv = list(args)
    if argv and argv[0] in ASSINAM and "--de" not in argv:
        argv += ["--de", "claude"]
    return subprocess.run(
        [sys.executable, str(CMD), *argv], env=env, capture_output=True, text=True,
    )


def configura(core, ias: list[str]) -> None:
    core.garantir_estrutura()
    core.p_config().write_text(
        json.dumps({"na_sala": ias, "brain": ias[0], "teto_bytes": 204800}) + "\n",
        encoding="utf-8",
    )


def falso_despachante(base: Path) -> Path:
    """Um worker de mentira: escreve o plano, mas segue vivo com um filho `sleep`.

    O filho existe para provar que o `parar` derruba a ÁRVORE. Matar só a casca e
    deixar o motor rodando foi a dor real desta madrugada.
    """
    p = base / "falso-despachante.sh"
    p.write_text(
        "#!/usr/bin/env bash\n"
        "# <braco> <missao> <prompt> <log> <plano>\n"
        'echo "worker falso braco=$1 missao=$2" > "$4"\n'
        'if [ -n "${FALSO_SEM_PLANO:-}" ]; then :; else echo "plano de $1" > "$5"; fi\n'
        "sleep 300 &\n"
        'echo "$!" > "$4.neto"\n'
        "wait\n",
        encoding="utf-8",
    )
    p.chmod(0o755)
    return p


def vivo_no_so(pid: int) -> bool:
    """Vivo de verdade. `ps -o pid=` também lista ZUMBI (defunto ainda não colhido
    pelo pai), e zumbi não está rodando nada — contá-lo como vivo faria o teste
    aprovar um `parar` que não parou, e reprovar um que parou."""
    r = subprocess.run(["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True)
    est = r.stdout.strip()
    return r.returncode == 0 and est != "" and not est.startswith("Z")


def estado(base: Path) -> dict:
    return json.loads((base / "comando" / "estado.json").read_text(encoding="utf-8"))


def grava_estado(base: Path, d: dict) -> None:
    (base / "comando" / "estado.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def espera_plano(p: Path, seg: float = 6.0) -> bool:
    fim = time.time() + seg
    while time.time() < fim:
        if p.exists() and p.stat().st_size > 0:
            return True
        time.sleep(0.1)
    return False


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-comandos-teste-"))
    falso = falso_despachante(base)
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "IACHAT_DESPACHO": str(falso),
        "PYTHON_DONTWRITEBYTECODE": "1",
    }
    os.environ["IACHAT_HOME"] = str(base)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RAIZ / "bin"))
    import iachat_core as core

    try:
        configura(core, ["claude", "codex", "kimi"])

        checa(
            "T0 as três portas existem e são executáveis",
            CMD.is_file() and os.access(CMD, os.X_OK)
            and DESPACHO.is_file() and os.access(DESPACHO, os.X_OK)
            and DECIDE.is_file(),
            f"{CMD.name} · {DESPACHO.name}",
        )

        # ---- T-RED 1: /plan sem /goal REPROVA -------------------------------
        sem_goal = roda(env, "plan")
        checa(
            "T-RED plan sem goal REPROVA (não há enunciado para planejar)",
            sem_goal.returncode == 2 and "não há objetivo" in sem_goal.stderr
            and "Traceback" not in sem_goal.stderr,
            f"rc={sem_goal.returncode}",
        )

        # ---- T-RED 2: /concluir antes de /plan REPROVA ----------------------
        roda(env, "goal", "--calado", "provar o ciclo dos comandos do dono")
        cedo = roda(env, "concluir", "--calado")
        checa(
            "T-RED concluir sem plano REPROVA (autorizar o vazio é assinar em branco)",
            cedo.returncode == 3 and "não há plano no disco" in cedo.stderr
            and estado(base)["estado"] == "aberta",
            f"rc={cedo.returncode}",
        )

        # ---- T1: /goal grava e ANUNCIA na sala ------------------------------
        # `--de bauer` de propósito: é ESTE caminho que o teste prova — o dono não está
        # em `na_sala`, então quem assina é a orquestradora, com a procedência na frente.
        g = roda(env, "goal", "--novo", "--de", "bauer",
                 "arrumar o sino do codex sem quebrar o hash")
        e1 = estado(base)
        chat = core.p_chat().read_text(encoding="utf-8")
        checa(
            "T1 goal abre missão, grava no disco e anuncia na sala",
            g.returncode == 0 and e1["id"] == "m2" and e1["estado"] == "aberta"
            and "arrumar o sino" in e1["goal"]
            and "do dono (bauer)" in chat and "arrumar o sino" in chat,
            f"id={e1['id']} chat={len(chat)} B",
        )

        # ---- T2: /plan --seco não gasta a frota -----------------------------
        # `--todas` trava o ciclo multi-worker (parar/colher/refaz abaixo). A
        # calibração por nível mora em teste_plan_calibrado.py — este arquivo
        # prova o despacho, não a heurística.
        seco = roda(env, "plan", "--seco", "--todas")
        checa(
            "T2 plan --seco mostra quem seria despachado sem despachar nada",
            seco.returncode == 0 and "codex" in seco.stdout and "kimi" in seco.stdout
            and "claude" not in seco.stdout  # o brain orquestra, não se despacha
            and not estado(base)["workers"],
            f"workers={len(estado(base)['workers'])}",
        )

        # ---- T3: /plan dispara a frota, com PID e marca no `ps` -------------
        pl = roda(env, "plan", "--todas")
        e3 = estado(base)
        w_codex = e3["workers"]["codex"]
        cmdline = subprocess.run(
            ["ps", "-o", "command=", "-p", str(w_codex["pid"])],
            capture_output=True, text=True,
        ).stdout
        checa(
            "T3 plan despacha a frota; o PID carrega a marca do worker no ps",
            pl.returncode == 0 and set(e3["workers"]) == {"codex", "kimi"}
            and e3["estado"] == "planejando"
            and w_codex["lstart"] and w_codex["prompt"] in cmdline,
            f"pid={w_codex['pid']}",
        )
        # o prompt tem que dizer "não aplique" — planejar é reversível, aplicar não
        prompt = Path(w_codex["prompt"]).read_text(encoding="utf-8")
        checa(
            "T3b o pedido de plano proíbe aplicar e nomeia o arquivo de saída",
            "NÃO aplique nada" in prompt and w_codex["plano"] in prompt
            and "arquivo:linha" in prompt,
            f"{len(prompt)} B",
        )

        # ---- T4: /quem vê vivo, com pid e há quanto tempo -------------------
        espera_plano(Path(w_codex["plano"]))
        q = roda(env, "quem")
        qj = json.loads(roda(env, "quem", "--json").stdout)
        checa(
            "T4 quem mostra vivo, com pid, papel e tempo",
            q.returncode == 0 and f"pid {w_codex['pid']}" in q.stdout
            and "planejando" in q.stdout
            and qj["missao"] == "m2"
            and any(x["ia"] == "codex" and "🟢" in x["estado"] for x in qj["quem"]),
            f"{len(q.stdout)} B",
        )

        # ---- T-RED 3: /goal novo com worker vivo REPROVA --------------------
        atropelo = roda(env, "goal", "--calado", "outro objetivo qualquer")
        checa(
            "T-RED goal novo com worker vivo REPROVA (abandonaria quem está rodando)",
            atropelo.returncode == 3 and "worker(s) vivo(s)" in atropelo.stderr
            and estado(base)["id"] == "m2",
            f"rc={atropelo.returncode}",
        )

        # ---- T-RED 4: PID RECICLADO → recusa, e o processo SOBREVIVE --------
        e4 = estado(base)
        pid_codex = e4["workers"]["codex"]["pid"]
        lstart_bom = e4["workers"]["codex"]["lstart"]
        e4["workers"]["codex"]["lstart"] = "Mon Jan  1 00:00:00 2001"
        grava_estado(base, e4)
        reciclado = roda(env, "parar", "--ia", "codex", "--calado")
        sobreviveu = vivo_no_so(pid_codex)
        checa(
            "T-RED parar com PID RECICLADO recusa E o processo continua vivo",
            reciclado.returncode == 3 and "RECICLADO" in reciclado.stderr
            and "NÃO MATEI" in reciclado.stderr and sobreviveu,
            f"rc={reciclado.returncode} vivo={sobreviveu}",
        )
        e4["workers"]["codex"]["lstart"] = lstart_bom
        grava_estado(base, e4)

        # ---- T-RED 5: PID sem a marca do worker → recusa --------------------
        impostor = subprocess.Popen(
            ["sleep", "300"], start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        faxina.append(impostor.pid)
        time.sleep(0.3)
        e5 = estado(base)
        e5["workers"]["impostor"] = {
            **e5["workers"]["codex"],
            "pid": impostor.pid,
            "lstart": subprocess.run(
                ["ps", "-o", "lstart=", "-p", str(impostor.pid)],
                capture_output=True, text=True,
            ).stdout.strip(),
        }
        grava_estado(base, e5)
        sem_marca = roda(env, "parar", "--ia", "impostor", "--calado")
        checa(
            "T-RED parar em PID sem a marca do worker recusa E o alheio sobrevive",
            sem_marca.returncode == 3 and "não carrega a marca" in sem_marca.stderr
            and vivo_no_so(impostor.pid),
            f"rc={sem_marca.returncode}",
        )
        e5 = estado(base)
        del e5["workers"]["impostor"]
        grava_estado(base, e5)

        # ---- T-RED 6: parar IA que não está na missão REPROVA ---------------
        forasteiro = roda(env, "parar", "--ia", "grok", "--calado")
        checa(
            "T-RED parar IA fora da missão REPROVA sem tocar em ninguém",
            forasteiro.returncode == 2 and "não estão nesta missão" in forasteiro.stderr
            and vivo_no_so(pid_codex),
            f"rc={forasteiro.returncode}",
        )

        # ---- T5: /plan --colher devolve o plano PARA A SALA ------------------
        espera_plano(Path(estado(base)["workers"]["kimi"]["plano"]))
        col = roda(env, "plan", "--colher")
        chat2 = core.p_chat().read_text(encoding="utf-8")
        corpo_planos = (Path(estado(base)["workers"]["codex"]["plano"])
                        .read_text(encoding="utf-8"))
        checa(
            "T5 colher devolve o plano na SALA, por resumo + caminho (não o corpo)",
            col.returncode == 0 and estado(base)["estado"] == "planejada"
            and "Planos da missão m2" in chat2
            and estado(base)["workers"]["codex"]["plano"] in chat2
            and corpo_planos.strip() in col.stdout,
            f"chat={len(chat2)} B",
        )

        # ---- T6: /parar mata a ÁRVORE (o neto morre junto) ------------------
        neto = int(Path(str(estado(base)["workers"]["codex"]["log"]) + ".neto")
                   .read_text(encoding="utf-8").strip())
        faxina.append(neto)
        checa("T6a o neto do worker estava vivo antes do parar", vivo_no_so(neto), f"pid={neto}")
        pr = roda(env, "parar", "--calado")
        time.sleep(0.5)
        checa(
            "T6 parar derruba a ÁRVORE: casca e neto, e marca `parada` no estado",
            pr.returncode == 0 and "parado(s)" in pr.stdout
            and not vivo_no_so(pid_codex) and not vivo_no_so(neto)
            and estado(base)["estado"] == "parada",
            f"rc={pr.returncode} neto_vivo={vivo_no_so(neto)}",
        )

        # ---- T7: /refaz redispara o morto retomando o parcial ---------------
        e7 = estado(base)
        plano_codex = Path(e7["workers"]["codex"]["plano"])
        tent_antes = e7["workers"]["codex"].get("tentativas", 1)
        rf = roda(env, "refaz", "--ia", "codex", "--forcar")
        e8 = estado(base)
        novo_prompt = Path(e8["workers"]["codex"]["prompt"]).read_text(encoding="utf-8")
        faxina.append(e8["workers"]["codex"]["pid"])
        checa(
            "T7 refaz redispara o morto, com pid novo e o parcial na retomada",
            rf.returncode == 0 and e8["workers"]["codex"]["pid"] != pid_codex
            and e8["workers"]["codex"]["tentativas"] == tent_antes + 1
            and "RETOMADA" in novo_prompt and "plano de codex" in novo_prompt
            and plano_codex.with_suffix(".parcial1.md").exists(),
            f"tentativa={e8['workers']['codex']['tentativas']}",
        )

        # ---- T-RED 7: refaz de quem está vivo REPROVA -----------------------
        time.sleep(0.5)
        duplo = roda(env, "refaz", "--ia", "codex")
        checa(
            "T-RED refaz de worker VIVO REPROVA (dois escrevendo o mesmo plano)",
            duplo.returncode == 3 and "ainda está VIVO" in duplo.stderr,
            f"rc={duplo.returncode}",
        )
        fora = roda(env, "refaz", "--ia", "grok")
        checa(
            "T-RED refaz de IA fora da missão REPROVA",
            fora.returncode == 2 and "não está nesta missão" in fora.stderr,
            f"rc={fora.returncode}",
        )
        roda(env, "parar", "--calado")

        # ---- T8: /concluir autoriza, nomeia e posta na sala ------------------
        cc = roda(env, "concluir", "--para", "codex", "aplicar só o passo 1")
        e9 = estado(base)
        chat3 = core.p_chat().read_text(encoding="utf-8")
        checa(
            "T8 concluir autoriza, registra quem pode aplicar e nomeia na sala",
            cc.returncode == 0 and e9["estado"] == "autorizada"
            and e9["autorizado"]["para"] == ["codex"]
            and "AUTORIZADO" in chat3 and "para=codex" in chat3,
            f"estado={e9['estado']}",
        )

        # ---- T9: /decidi DELEGA ao iachat-decide ----------------------------
        d = roda(env, "decidi", "--de", "bauer", "--sobre", "aplicar",
                 "--porque", "planejar é reversível e aplicar não",
                 "só aplica depois do /concluir")
        registro = (base / "decisoes.md")
        listagem = subprocess.run(
            [sys.executable, str(DECIDE), "decisoes"], env=env, capture_output=True, text=True,
        )
        checa(
            "T9 decidi delega ao iachat-decide: a decisão vive no registro dele",
            d.returncode == 0 and registro.exists()
            and "id=D1" in registro.read_text(encoding="utf-8")
            and "D1 [aplicar]" in listagem.stdout,
            f"rc={d.returncode}",
        )

        # ---- T-RED 8: decidi sem --porque REPROVA (gate herdado, não copiado) -
        sem_porque = roda(env, "decidi", "--de", "bauer", "outra decisão")
        checa(
            "T-RED decidi sem --porque REPROVA pelo gate do iachat-decide",
            sem_porque.returncode == 2 and "falta --porque" in sem_porque.stderr,
            f"rc={sem_porque.returncode}",
        )

        # ---- T9b: o DONO anuncia mesmo não estando em `na_sala` ---------------
        # `iachat-decide --anunciar` chama core.post(de,…), que rejeita quem não está
        # na sala (iachat_core.py:258-262): com `--de bauer` daria traceback. Quem
        # anuncia é o `/decidi`, por `voz()`, que faz o dono falar pela orquestradora.
        anuncio = roda(env, "decidi", "--de", "bauer", "--porque",
                       "o sino tem que tocar em quem vai obedecer",
                       "--anunciar", "codex", "decisão nominada ao codex")
        chat_d = core.p_chat().read_text(encoding="utf-8")
        checa(
            "T9b decidi do DONO anuncia pela orquestradora e nomina, sem traceback",
            anuncio.returncode == 0 and "Traceback" not in anuncio.stderr
            and "do dono (bauer)" in chat_d
            and "DECIDIDO: decisão nominada ao codex" in chat_d
            and "para=codex" in chat_d,
            f"rc={anuncio.returncode}",
        )

        # ---- T10: o despachante real recusa braço que não existe -------------
        vazio = base / "vazio.txt"
        vazio.write_text("nada\n", encoding="utf-8")
        braco = subprocess.run(
            [str(DESPACHO), "braco-que-nao-existe", "m2", str(vazio),
             str(base / "x.log"), str(base / "x.md")],
            capture_output=True, text=True,
        )
        checa(
            "T10 despachante recusa braço sem adaptador, com a lista do que existe",
            braco.returncode == 3 and "braço sem adaptador" in braco.stderr
            and "codex" in braco.stderr,
            f"rc={braco.returncode}",
        )

        # ================================================================
        # RUNS DO IASWARM — o mundo real: dispatch.sh grava logs/<w>.pid,
        # três workers morrem na queda de energia, e o painel jura que andam.
        # Tudo forjado em /tmp; nenhum processo da frota é tocado.
        # ================================================================
        run = base / "run-forjado"
        for sub in ("logs", "contratos", "progress", "resultados"):
            (run / sub).mkdir(parents=True, exist_ok=True)
        (run / "workers.tsv").write_text(
            "e3-squad\tcodex\t5\tcontratos/e3-squad.md\n"
            "e5-handoff\tgrok\t5\tcontratos/e5-handoff.md\n"
            "e6-roster\tqwen\t5\tcontratos/e6-roster.md\n"
            "e9-vivo\tkimi\t5\tcontratos/e9-vivo.md\n",
            encoding="utf-8",
        )
        for w in ("e3-squad", "e5-handoff", "e6-roster", "e9-vivo"):
            (run / "contratos" / f"{w}.md").write_text(f"# contrato {w}\n", encoding="utf-8")
        # os três que caíram deixaram log parcial e nenhum resultado
        for w in ("e3-squad", "e5-handoff", "e6-roster"):
            (run / "logs" / f"{w}.log").write_text(
                f"[{w}] etapa 2 de 5: li o núcleo e comecei o gate\n", encoding="utf-8")
        # PIDs mortos: números que não existem (alto o bastante para não colidir)
        pids_mortos = {"e3-squad": 999731, "e5-handoff": 999735, "e6-roster": 999739}
        for w, p in pids_mortos.items():
            (run / "logs" / f"{w}.pid").write_text(f"{p}\n", encoding="utf-8")

        # um worker VIVO de verdade: script DENTRO do run, então o caminho do run
        # aparece na linha de comando — é esse o âncora, não o nome do worker
        (run / "logs" / "worker-falso.sh").write_text(
            "#!/usr/bin/env bash\nsleep 300 &\necho \"$!\" > \"$2\"\nwait\n", encoding="utf-8")
        (run / "logs" / "worker-falso.sh").chmod(0o755)
        neto_f = run / "logs" / "e9-vivo.neto"
        proc_vivo = subprocess.Popen(
            ["bash", str(run / "logs" / "worker-falso.sh"), "e9-vivo", str(neto_f)],
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        faxina.append(proc_vivo.pid)
        (run / "logs" / "e9-vivo.pid").write_text(f"{proc_vivo.pid}\n", encoding="utf-8")

        # o VIZINHO que só MENCIONA o nome do worker, e não pertence ao run: é ele que
        # um `pkill -f e3-squad` mataria por engano
        vizinho_sh = base / "processo-que-menciona-e3-squad.sh"
        vizinho_sh.write_text("#!/usr/bin/env bash\nsleep 300\n", encoding="utf-8")
        vizinho_sh.chmod(0o755)
        vizinho = subprocess.Popen(
            ["bash", str(vizinho_sh), "e3-squad", "e5-handoff", "e6-roster"],
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        faxina.append(vizinho.pid)

        # o órfão VIVO sem `.pid`: aconteceu de verdade (d1-watchdog, 18/08)
        orfao = subprocess.Popen(
            ["bash", str(run / "logs" / "worker-falso.sh"), "d1-watchdog",
             str(run / "logs" / "d1.neto")],
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        faxina.append(orfao.pid)

        # o painel mentindo, como o real: state.json diz que todo mundo anda
        (run / "state.json").write_text(json.dumps({"workers": [
            {"worker": w, "braco": b, "estado": "rodando"}
            for w, b in (("e3-squad", "codex"), ("e5-handoff", "grok"),
                         ("e6-roster", "qwen"), ("e9-vivo", "kimi"))]}), encoding="utf-8")
        time.sleep(0.8)

        # ---- T11: quem --run separa os TRÊS desfechos ------------------------
        qr = roda(env, "quem", "--run", str(run))
        qrj = json.loads(roda(env, "quem", "--run", str(run), "--json").stdout)
        por_w = {x["worker"]: x for x in qrj["workers"]}
        checa(
            "T11 quem --run acerta vivo × morto, ancorado no PID gravado",
            qr.returncode == 0
            and all(por_w[w]["veredito"] == "morto" for w in pids_mortos)
            and por_w["e9-vivo"]["veredito"] == "vivo"
            and "3 morto(s)" in qr.stdout and "1 vivo(s)" in qr.stdout,
            f"e9={por_w['e9-vivo']['veredito']}",
        )
        checa(
            "T11b quem --run denuncia o state.json que jura que os mortos andam",
            "state.json diz que" in qr.stdout and "painel=rodando      ps=morto" in qr.stdout,
            "painel × ps",
        )
        checa(
            "T11c quem --run acha o VIVO sem `.pid` (ausência de .pid ≠ morte)",
            any(p == orfao.pid for p, _ in
                [(x["pid"], x["cmd"]) for x in qrj["orfaos"]]),
            f"órfãos={[x['pid'] for x in qrj['orfaos']]}",
        )
        # A linha de comando do PRÓPRIO `quem --run` contém o caminho do run: se ele se
        # contasse, todo diagnóstico viria com um fantasma dentro. A conferência é por
        # PID — o conjunto tem que ser EXATAMENTE o órfão plantado, nem mais nem menos.
        # (Por nome não dá: o diretório do teste se chama `iachat-comandos-teste-…`, e
        # um filtro por substring engoliria o órfão legítimo junto.)
        checa(
            "T-RED quem --run não se conta como órfão: o conjunto é exatamente o plantado",
            {x["pid"] for x in qrj["orfaos"]} == {orfao.pid}
            and os.getpid() not in {x["pid"] for x in qrj["orfaos"]},
            f"órfãos={[x['pid'] for x in qrj['orfaos']]} plantado={orfao.pid}",
        )

        # ---- T-RED 10: PID que existe mas NÃO é do run → recusa --------------
        (run / "logs" / "e3-squad.pid").write_text(f"{vizinho.pid}\n", encoding="utf-8")
        intruso = roda(env, "parar", "--run", str(run), "--ia", "e3-squad", "--calado")
        checa(
            "T-RED parar --run recusa PID que existe mas não cita o run; vizinho sobrevive",
            intruso.returncode == 3 and "NÃO cita este run" in intruso.stderr
            and vivo_no_so(vizinho.pid),
            f"rc={intruso.returncode}",
        )
        # este é o teste do `pkill -f`: o vizinho MENCIONA e3-squad na linha de comando
        cmd_vizinho = subprocess.run(["ps", "-o", "command=", "-p", str(vizinho.pid)],
                                     capture_output=True, text=True).stdout
        checa(
            "T-RED o vizinho de fato casaria `pkill -f e3-squad`, e mesmo assim viveu",
            "e3-squad" in cmd_vizinho and vivo_no_so(vizinho.pid),
            "âncora é o PID gravado + o run no cmd, nunca o nome",
        )
        (run / "logs" / "e3-squad.pid").write_text(f"{pids_mortos['e3-squad']}\n",
                                                   encoding="utf-8")

        # ---- T-RED 11: nasceu DEPOIS do despacho → reciclado → recusa --------
        antigo = time.time() - 7200  # o `.pid` foi escrito há 2h; o processo é de agora
        os.utime(run / "logs" / "e9-vivo.pid", (antigo, antigo))
        temporal = roda(env, "parar", "--run", str(run), "--ia", "e9-vivo", "--calado")
        checa(
            "T-RED parar --run recusa PID nascido DEPOIS do despacho (reciclado no tempo)",
            temporal.returncode == 3 and "reciclado" in temporal.stderr
            and vivo_no_so(proc_vivo.pid),
            f"rc={temporal.returncode} vivo={vivo_no_so(proc_vivo.pid)}",
        )
        agora_ts = time.time()
        os.utime(run / "logs" / "e9-vivo.pid", (agora_ts, agora_ts))

        # ---- T-RED 12: refaz --run recusa o não-verificável ------------------
        os.utime(run / "logs" / "e9-vivo.pid", (antigo, antigo))
        rf_nv = roda(env, "refaz", "--run", str(run), "--ia", "e9-vivo")
        checa(
            "T-RED refaz --run recusa quem não se prova morto (duplicaria trabalho pago)",
            rf_nv.returncode == 3 and "não consigo provar" in rf_nv.stderr,
            f"rc={rf_nv.returncode}",
        )
        os.utime(run / "logs" / "e9-vivo.pid", (agora_ts, agora_ts))

        # ---- T12: refaz --run ressuscita os três, retomando o parcial --------
        seco_r = roda(env, "refaz", "--run", str(run), "--ia", "e3-squad", "--seco")
        checa(
            "T12a refaz --run --seco mostra a retomada sem gastar assinatura",
            seco_r.returncode == 0 and "seria redisparado" in seco_r.stdout
            and "retomando" in seco_r.stdout
            and not (run / "logs" / "e3-squad.r2.log").exists(),
            f"rc={seco_r.returncode}",
        )
        ressuscitados = []
        for w in ("e3-squad", "e5-handoff", "e6-roster"):
            rr = roda(env, "refaz", "--run", str(run), "--ia", w)
            novo = int((run / "logs" / f"{w}.pid").read_text().strip())
            faxina.append(novo)
            ressuscitados.append((w, rr.returncode, novo))
        # o `--seco` acima não escreveu nada, então esta é a tentativa r2
        prompts = sorted((run / "logs").glob("e3-squad.r*.prompt.txt"))
        checa(
            "T12b o refaz --seco não deixou prompt no disco: só a rodada real escreveu",
            [p.name for p in prompts] == ["e3-squad.r2.prompt.txt"],
            f"{[p.name for p in prompts]}",
        )
        pr3 = prompts[-1].read_text(encoding="utf-8")
        checa(
            "T12 refaz --run ressuscita os 3 mortos, com PID novo e protocolo iaswarm",
            all(rc == 0 and pid not in pids_mortos.values() for _, rc, pid in ressuscitados)
            and "PROTOCOLO IASWARM" in pr3 and "RETOMADA" in pr3
            and "etapa 2 de 5" in pr3
            and str(run / "progress" / "e3-squad.jsonl") in pr3,
            f"{[(w, p) for w, _, p in ressuscitados]}",
        )

        # ---- T-RED 13: refaz --run de quem já entregou REPROVA ---------------
        (run / "resultados" / "e5-handoff.md").write_text("missão: x\nresultado: pronto\n",
                                                          encoding="utf-8")
        roda(env, "parar", "--run", str(run), "--ia", "e5-handoff", "--calado")
        time.sleep(0.4)
        entregue = roda(env, "refaz", "--run", str(run), "--ia", "e5-handoff")
        checa(
            "T-RED refaz --run recusa quem já entregou (apagaria trabalho pronto)",
            entregue.returncode == 3 and "já entregou" in entregue.stderr,
            f"rc={entregue.returncode}",
        )
        fora_run = roda(env, "refaz", "--run", str(run), "--ia", "nao-existe")
        checa(
            "T-RED refaz --run de worker fora do workers.tsv REPROVA",
            fora_run.returncode == 2 and "não está neste run" in fora_run.stderr,
            f"rc={fora_run.returncode}",
        )

        # ---- T13: parar --run mata a árvore do alvo e SÓ dele ----------------
        neto_vivo = int(neto_f.read_text(encoding="utf-8").strip())
        faxina.append(neto_vivo)
        antes = sorted(p.name for p in (run / "logs").iterdir())
        pr_run = roda(env, "parar", "--run", str(run), "--ia", "e9-vivo", "--calado")
        time.sleep(0.6)
        checa(
            "T13 parar --run derruba a árvore do worker e não encosta nos vizinhos",
            pr_run.returncode == 0
            and not vivo_no_so(proc_vivo.pid) and not vivo_no_so(neto_vivo)
            and vivo_no_so(vizinho.pid) and vivo_no_so(orfao.pid),
            f"alvo={vivo_no_so(proc_vivo.pid)} vizinho={vivo_no_so(vizinho.pid)}",
        )
        checa(
            "T13b parar --run não escreve nada no run (é dado de outro programa)",
            sorted(p.name for p in (run / "logs").iterdir()) == antes
            and "nada foi escrito" in pr_run.stdout,
            f"{len(antes)} arquivos",
        )
        naorun = roda(env, "quem", "--run", str(base))
        checa(
            "T-RED --run em pasta que não é run do iaswarm REPROVA",
            naorun.returncode == 2 and "não parece um run" in naorun.stderr,
            f"rc={naorun.returncode}",
        )

        # ---- T14: /decidi alimenta os DOIS instrumentos ----------------------
        d2 = roda(env, "decidi", "--de", "bauer", "--sobre", "energia",
                  "--porque", "a queda de 18/08 matou 3 workers sem aviso",
                  "worker que cai volta pelo refaz, nunca por kill na mão")
        chat4 = core.p_chat().read_text(encoding="utf-8")
        reg = (base / "decisoes.md").read_text(encoding="utf-8")
        rel = subprocess.run(
            [sys.executable, str(RAIZ / "bin" / "iachat-report"), "--horas", "24"],
            env=env, capture_output=True, text=True)
        checa(
            "T14 decidi grava no registro E posta DECIDIDO: que o iachat-report lê",
            d2.returncode == 0 and "id=D2" in reg
            and "DECIDIDO: worker que cai volta pelo refaz" in chat4
            and "worker que cai volta pelo refaz" in rel.stdout,
            f"report={len(rel.stdout)} B",
        )

    finally:
        for pid in faxina:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
        import shutil
        shutil.rmtree(base, ignore_errors=True)

    print()
    if falhas:
        print(f"✗ {len(falhas)} falha(s): {', '.join(falhas)}")
        return 1
    print("✔ tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
