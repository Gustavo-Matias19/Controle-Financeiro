
from banco import conectar


def cadastrar(descricao, valor_centavos, tipo, categoria):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO transacoes
        (descricao, valor_centavos, tipo, categoria)
        VALUES (?, ?, ?, ?)
    """, (descricao, valor_centavos, tipo, categoria))

    conexao.commit()
    conexao.close()

    print("Transação cadastrada com sucesso!")


def listar():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, descricao, valor_centavos, tipo, categoria, data
        FROM transacoes
        ORDER BY data DESC, id DESC
    """)

    transacoes = cursor.fetchall()
    conexao.close()

    if not transacoes:
        print("Nenhuma transação cadastrada.")
        return

    for t in transacoes:
        valor = t[2] / 100
        print(
            f"ID: {t[0]} | {t[1]} | R$ {valor:.2f} | "
            f"{t[3]} | {t[4]} | {t[5]}"
        )


def atualizar(id_transacao, descricao, valor_centavos):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE transacoes
        SET descricao = ?, valor_centavos = ?
        WHERE id = ?
    """, (descricao, valor_centavos, id_transacao))

    alteradas = cursor.rowcount
    conexao.commit()
    conexao.close()

    if alteradas:
        print("Transação atualizada!")
    else:
        print("ID não encontrado.")


def excluir(id_transacao):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        DELETE FROM transacoes
        WHERE id = ?
    """, (id_transacao,))

    excluidas = cursor.rowcount
    conexao.commit()
    conexao.close()

    if excluidas:
        print("Transação excluída!")
    else:
        print("ID não encontrado.")


def resumo():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT tipo, COALESCE(SUM(valor_centavos), 0)
        FROM transacoes
        GROUP BY tipo
    """)

    resultados = cursor.fetchall()
    conexao.close()

    valores = dict(resultados)

    receitas = valores.get("receita", 0) / 100
    despesas = valores.get("despesa", 0) / 100
    saldo = receitas - despesas

    print(f"Receitas: R$ {receitas:.2f}")
    print(f"Despesas: R$ {despesas:.2f}")
    print(f"Saldo: R$ {saldo:.2f}")
