import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("precos.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS buscas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loja TEXT NOT NULL,
            nome_produto TEXT NOT NULL,
            preco REAL,
            termo_buscado TEXT NOT NULL,
            score INTEGER,
            data_hora TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    print(f"Banco de dados pronto em: {DB_PATH.resolve()}")


def salvar_resultados(loja: str, termo_buscado: str, produtos: list[dict]):
    """Cada chamada abre/fecha sua própria conexão — seguro entre threads,
    já que não compartilhamos uma conexão sqlite3 entre requisições."""
    if not produtos:
        return

    conn = sqlite3.connect(DB_PATH)
    agora = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        """
        INSERT INTO buscas (loja, nome_produto, preco, termo_buscado, score, data_hora)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (loja, p["nome"], p["preco"], termo_buscado, p["score"], agora)
            for p in produtos
        ],
    )
    conn.commit()
    conn.close()
