
from decimal import Decimal, InvalidOperation

from banco import criar_tabela
from operacoes import cadastrar, listar, atualizar, excluir, resumo


def ler_valor():
    while True:
        texto = input("Valor (R$): ").strip().replace(",", ".")

        try:
            valor = Decimal(texto)
            centavos = valor * 100

            if (
                not valor.is_finite()
                or valor <= 0
                or centavos != centavos.to_integral_value()
            ):
                print("Digite um valor positivo com até 2 casas decimais.")
                continue

            return int(centavos)

        except InvalidOperation:
            print("Valor inválido. Tente novamente.")


def ler_texto(mensagem):
    while True:
        texto = input(mensagem).strip()
        if texto:
            return texto
        print("Esse campo não pode ficar vazio.")


def ler_id():
    return int(input("ID da transação: "))


criar_tabela()

while True:
    print("\n===== CONTROLE FINANCEIRO =====")
    print("1 - Cadastrar receita")
    print("2 - Cadastrar despesa")
    print("3 - Listar transações")
    print("4 - Atualizar transação")
    print("5 - Excluir transação")
    print("6 - Resumo financeiro")
    print("0 - Sair")

    opcao = input("Escolha uma opção: ")

    try:
        if opcao in ("1", "2"):
            descricao = ler_texto("Descrição: ")
            valor = ler_valor()
            categoria = ler_texto("Categoria: ")

            tipo = "receita" if opcao == "1" else "despesa"

            cadastrar(descricao, valor, tipo, categoria)

        elif opcao == "3":
            listar()

        elif opcao == "4":
            id_transacao = ler_id()
            descricao = ler_texto("Nova descrição: ")
            valor = ler_valor()

            atualizar(id_transacao, descricao, valor)

        elif opcao == "5":
            id_transacao = ler_id()
            excluir(id_transacao)

        elif opcao == "6":
            resumo()

        elif opcao == "0":
            print("Sistema encerrado!")
            break

        else:
            print("Opção inválida!")

    except ValueError:
        print("Digite um número inteiro válido para o ID.")
