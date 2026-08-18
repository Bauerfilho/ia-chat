#!/usr/bin/env python3
"""Gates da ponte ia-mail: vermelho provado antes do verde.

O teste nunca toca a caixa real. Ele constrói índices mínimos em diretório
temporário, executa o binário verdadeiro em subprocesso e compara o estado
byte a byte antes/depois de cada comando de leitura.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


RAIZ = Path(__file__).resolve().parent.parent
CLI = RAIZ / "bin" / "ia-mail"
FALHAS = []

NOMES_CREDENCIAL = re.compile(
    r"(?:password|passwd|pwd|senha|secret|token|credential|credencial)", re.IGNORECASE
)
SQL_MUTANTE = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO|"
    r"ALTER\s+TABLE|DROP\s+(?:TABLE|TRIGGER|INDEX)|"
    r"CREATE\s+(?:TABLE|TRIGGER|INDEX)|ATTACH|DETACH|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)
MODULOS_PROIBIDOS = {"imaplib", "smtplib", "keyring"}


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(nome)


def nomes_de_alvo(alvo: ast.AST):
    """Expande alvos de atribuição para detectar um campo sensível disfarçado."""
    if isinstance(alvo, ast.Name):
        yield alvo.id
    elif isinstance(alvo, ast.Attribute):
        yield alvo.attr
    elif isinstance(alvo, (ast.Tuple, ast.List)):
        for item in alvo.elts:
            for nome in nomes_de_alvo(item):
                yield nome


def campos_de_credencial(codigo: str) -> list[str]:
    """Grep semântico: opções/variáveis/imports, não a palavra em texto explicativo."""
    arvore = ast.parse(codigo)
    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            modulo = no.module if isinstance(no, ast.ImportFrom) else ""
            nomes = [a.name for a in no.names]
            for nome in ([modulo] if modulo else []) + nomes:
                if nome and nome.split(".")[0] in MODULOS_PROIBIDOS:
                    achados.append(f"import:{nome}")
        if isinstance(no, ast.arg) and NOMES_CREDENCIAL.search(no.arg):
            achados.append(f"argumento:{no.arg}")
        if isinstance(no, ast.Subscript):
            chave = no.slice
            if (
                isinstance(chave, ast.Constant)
                and isinstance(chave.value, str)
                and NOMES_CREDENCIAL.search(chave.value)
            ):
                achados.append(f"chave:{chave.value}")
        if isinstance(no, ast.Dict):
            for chave in no.keys:
                if (
                    isinstance(chave, ast.Constant)
                    and isinstance(chave.value, str)
                    and NOMES_CREDENCIAL.search(chave.value)
                ):
                    achados.append(f"chave:{chave.value}")
        if isinstance(no, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            for alvo in alvos:
                for nome in nomes_de_alvo(alvo):
                    if NOMES_CREDENCIAL.search(nome):
                        achados.append(f"campo:{nome}")
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            if no.func.attr == "add_argument":
                for argumento in no.args:
                    if (
                        isinstance(argumento, ast.Constant)
                        and isinstance(argumento.value, str)
                        and NOMES_CREDENCIAL.search(argumento.value)
                    ):
                        achados.append(f"opcao:{argumento.value}")
    return achados


def sql_mutante(codigo: str) -> list[str]:
    """Procura qualquer literal SQL capaz de alterar o índice ou o esquema."""
    arvore = ast.parse(codigo)
    achados = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Constant) or not isinstance(no.value, str):
            continue
        casamento = SQL_MUTANTE.search(no.value)
        if casamento:
            achados.append(casamento.group(0).upper())
    return achados


def criar_indice(caminho: Path) -> None:
    """Cria somente o subconjunto do schema V10 consumido pelo CLI."""
    conexao = sqlite3.connect(str(caminho))
    conexao.executescript(
        """
        CREATE TABLE mailboxes (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            total_count INTEGER NOT NULL DEFAULT 0,
            unread_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE addresses (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL,
            comment TEXT NOT NULL
        );
        CREATE TABLE subjects (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL
        );
        CREATE TABLE summaries (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL
        );
        CREATE TABLE messages (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            sender INTEGER,
            subject INTEGER NOT NULL,
            summary INTEGER,
            date_sent INTEGER,
            date_received INTEGER,
            mailbox INTEGER NOT NULL,
            read INTEGER NOT NULL DEFAULT 0,
            deleted INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conexao.executemany(
        "INSERT INTO mailboxes(ROWID, url, total_count, unread_count) VALUES (?, ?, ?, ?)",
        [
            (1, "imap://conta@example.test/INBOX", 5, 3),
            (2, "imap://conta@example.test/Archive", 0, 0),
        ],
    )
    conexao.executemany(
        "INSERT INTO addresses(ROWID, address, comment) VALUES (?, ?, ?)",
        [
            (1, "alerts@example.test", "Alertas alerts@example.test"),
            (2, "person@example.test", "Pessoa person@example.test"),
        ],
    )
    conexao.executemany(
        "INSERT INTO subjects(ROWID, subject) VALUES (?, ?)",
        [
            (1, "Vaga Python #42"),
            (2, "Re: Vaga Python #42"),
            (3, "Boletim semanal"),
            (4, "Conversa com person@example.test"),
        ],
    )
    conexao.executemany(
        "INSERT INTO summaries(ROWID, summary) VALUES (?, ?)",
        [
            (1, "Primeiro trecho"),
            (2, "Segundo trecho"),
            (3, "Terceiro trecho"),
            (4, "Quarto trecho para person@example.test"),
        ],
    )
    conexao.executemany(
        """
        INSERT INTO messages(
            ROWID, sender, subject, summary, date_sent, date_received, mailbox, read, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 1, 1, 1787000001, 1787000001, 1, 0, 0),
            (2, 1, 2, 2, 1787000002, 1787000002, 1, 0, 0),
            (3, 1, 3, 3, 1787000003, 1787000003, 1, 1, 0),
            (4, 2, 4, 4, 1787000004, 1787000004, 1, 0, 0),
            (5, 2, 4, 4, 1787000005, 1787000005, 1, 1, 0),
        ],
    )
    conexao.commit()
    conexao.close()


def assinatura(caminho: Path) -> dict:
    """Assina bytes e campos de estado: um write fica impossível de esconder."""
    uri = caminho.resolve().as_uri() + "?mode=ro"
    conexao = sqlite3.connect(uri, uri=True)
    caixas = conexao.execute(
        "SELECT ROWID, total_count, unread_count FROM mailboxes ORDER BY ROWID"
    ).fetchall()
    mensagens = conexao.execute(
        "SELECT ROWID, mailbox, read, deleted FROM messages ORDER BY ROWID"
    ).fetchall()
    conexao.close()
    return {
        "sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
        "caixas": caixas,
        "mensagens": mensagens,
        "arquivos": sorted(p.name for p in caminho.parent.iterdir()),
    }


def rodar(indice: Path, *args: str) -> subprocess.CompletedProcess:
    """Roda o binário real com Python atual e sem cache gravado no repositório."""
    ambiente = dict(os.environ)
    ambiente["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), "--db", str(indice), *args],
        capture_output=True,
        text=True,
        env=ambiente,
        timeout=10,
    )


def json_da_saida(processo: subprocess.CompletedProcess) -> Optional[dict]:
    try:
        return json.loads(processo.stdout)
    except (TypeError, json.JSONDecodeError):
        return None


def main() -> int:
    codigo = CLI.read_text(encoding="utf-8") if CLI.is_file() else ""

    # VERMELHO 1: o gate precisa pegar tanto campo interno quanto opção de CLI.
    codigo_com_segredo = (
        codigo
        + '\npassword = input()\nparser.add_argument("--password")\n'
        + 'valor = os.environ["MAIL_PASSWORD"]\n'
    )
    checa(
        "R1 VERMELHO: campo/opção de credencial é reprovado",
        bool(campos_de_credencial(codigo_com_segredo)),
    )

    # VERMELHO 2: um único UPDATE escondido precisa derrubar o gate estático.
    codigo_com_mutacao = codigo + '\nconexao.execute("UPDATE messages SET read = 1")\n'
    checa(
        "R2 VERMELHO: SQL que marca mensagem é reprovado",
        bool(sql_mutante(codigo_com_mutacao)),
    )

    checa("G1 binário existe e é executável", CLI.is_file() and os.access(CLI, os.X_OK))
    checa(
        "G2 fonte não aceita nem armazena campo de credencial",
        not campos_de_credencial(codigo),
        ", ".join(campos_de_credencial(codigo)),
    )
    checa(
        "G3 fonte não contém SQL mutante",
        not sql_mutante(codigo),
        ", ".join(sql_mutante(codigo)),
    )
    checa("G4 conexão exige mode=ro", '"?mode=ro"' in codigo)
    checa("G5 conexão reforça PRAGMA query_only", "PRAGMA query_only = ON" in codigo)

    with tempfile.TemporaryDirectory(prefix="ia-mail-teste-") as temporario:
        base = Path(temporario)

        # VERMELHO 3: prova que o oráculo de estado detecta uma alteração real.
        indice_vermelho = base / "Envelope Index vermelho"
        criar_indice(indice_vermelho)
        antes_vermelho = assinatura(indice_vermelho)
        mutador = sqlite3.connect(str(indice_vermelho))
        mutador.execute("UPDATE messages SET read = 1 WHERE ROWID = 1")
        mutador.commit()
        mutador.close()
        checa(
            "R3 VERMELHO: oráculo detecta marcação como lida",
            assinatura(indice_vermelho) != antes_vermelho,
        )

        indice = base / "Envelope Index"
        criar_indice(indice)
        indice.chmod(0o444)

        estado_inicial = assinatura(indice)
        caixas = rodar(indice, "--json", "caixas")
        caixas_json = json_da_saida(caixas)
        checa("G6 `caixas` sai 0 e JSON válido", caixas.returncode == 0 and caixas_json is not None)
        checa(
            "G7 `caixas` lista total e não-lidos corretos",
            caixas_json is not None
            and len(caixas_json.get("caixas", [])) == 2
            and caixas_json["caixas"][0]["nao_lidas"] == 3,
        )
        checa(
            "G8 listagem não altera nenhum byte nem campo da caixa",
            assinatura(indice) == estado_inicial,
        )

        recentes = rodar(indice, "--json", "recentes", "--caixa", "1", "-n", "3")
        recentes_json = json_da_saida(recentes)
        checa(
            "G9 recentes lê cabeçalho e trecho",
            recentes.returncode == 0
            and recentes_json is not None
            and len(recentes_json.get("mensagens", [])) == 3
            and recentes_json["mensagens"][0]["assunto"]
            == "Conversa com p***@example.test"
            and recentes_json["mensagens"][0]["trecho"]
            == "Quarto trecho para p***@example.test",
        )
        checa(
            "G10 endereço completo nunca sai",
            "alerts@example.test" not in recentes.stdout
            and "person@example.test" not in recentes.stdout
            and "***@example.test" in recentes.stdout,
        )

        privado = rodar(
            indice, "--json", "--privado", "recentes", "--caixa", "1", "-n", "2"
        )
        privado_json = json_da_saida(privado)
        checa(
            "G11 modo privado oculta nome, assunto e trecho",
            privado.returncode == 0
            and privado_json is not None
            and all(
                m["remetente"] == m["assunto"] == m["trecho"]
                == "(oculto no modo privado)"
                for m in privado_json.get("mensagens", [])
            ),
        )

        repeticoes = rodar(
            indice,
            "--json",
            "repeticoes",
            "--caixa",
            "1",
            "-n",
            "5",
            "--minimo",
            "2",
        )
        repeticoes_json = json_da_saida(repeticoes)
        grupos = repeticoes_json.get("repeticoes", []) if repeticoes_json else []
        grupo_alertas = next((g for g in grupos if g["mensagens"] == 3), None)
        checa(
            "G12 repetição agrupa remetente e une Re: ao assunto-base",
            repeticoes.returncode == 0
            and grupo_alertas is not None
            and grupo_alertas["assuntos_distintos"] == 2
            and any(l["quantidade"] == 2 for l in grupo_alertas["linhas_repetidas"]),
        )
        checa(
            "G13 todos os comandos mantêm o índice byte-idêntico",
            assinatura(indice) == estado_inicial,
        )

        ausente = rodar(base / "nao-existe", "--json", "caixas")
        checa(
            "G14 índice ausente falha fechado e não tenta outra rota",
            ausente.returncode == 2 and "nenhuma rota" not in ausente.stdout,
        )

    print(f"\n{len(FALHAS) and 'FALHOU' or 'PASSOU'} — {14 + 3 - len(FALHAS)} ✔  {len(FALHAS)} ✗")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    raise SystemExit(main())
