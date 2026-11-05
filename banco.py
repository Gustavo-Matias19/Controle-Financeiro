
import sqlite3

def conectar():
    return sqlite3.connect("financeiro.db")


def criar_tabela():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL CHECK(valor_centavos > 0),
            tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
            categoria TEXT NOT NULL,
            data TEXT NOT NULL DEFAULT (date('now'))
        )
    """)

    conexao.commit()
    conexao.close()
