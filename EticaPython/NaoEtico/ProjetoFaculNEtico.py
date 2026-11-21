"""
╔══════════════════════════════════════════════════════════════════╗
║         SISTEMA DE CADASTRO - VERSÃO ANTIÉTICA                   ║
║         ⚠️  APENAS PARA FINS EDUCACIONAIS ⚠️                    ║
║         Trabalho: Ética no Desenvolvimento de Software           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os
import random

# ❌ PROBLEMA 1: Banco de dados em arquivo JSON sem nenhuma proteção
ARQUIVO_USUARIOS = "usuarios_sensiveis.json"

def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, "r") as f:
            return json.load(f)
    return {}

def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, "w") as f:
        # ❌ PROBLEMA 2: Dados salvos em texto puro, qualquer pessoa pode abrir o arquivo
        json.dump(usuarios, f, indent=4)

def cadastrar_usuario(usuarios):
    print("\n" + "="*50)
    print("         CADASTRO DE NOVO USUÁRIO")
    print("="*50)

    nome = input("Nome completo: ")
    email = input("Email: ")
    senha = input("Senha: ")  # ❌ PROBLEMA 3: Senha exibida na tela em texto puro

    # ❌ PROBLEMA 4: Coleta de dados desnecessários e invasivos
    cpf = input("CPF: ")
    renda = input("Renda mensal (R$): ")
    etnia = input("Etnia (branco/pardo/negro/outro): ")  # ❌ Dado discriminatório coletado sem necessidade
    religiao = input("Religião: ")                        # ❌ Dado sensível sem justificativa
    bairro = input("Bairro onde mora: ")

    # ❌ PROBLEMA 5: Nenhum termo de consentimento apresentado
    # O usuário não sabe para que esses dados serão usados

    if email in usuarios:
        print("❌ Email já cadastrado.")
        return

    usuarios[email] = {
        "nome": nome,
        "email": email,
        "senha": senha,           # ❌ Senha armazenada em texto puro
        "cpf": cpf,
        "renda": renda,
        "etnia": etnia,           # ❌ Dado sensível exposto
        "religiao": religiao,     # ❌ Dado sensível exposto
        "bairro": bairro,
    }

    salvar_usuarios(usuarios)
    print("\n Cadastro realizado com sucesso!")

    # ❌ PROBLEMA 6: Dados vendidos/compartilhados sem o usuário saber
    print("\n[SISTEMA INTERNO - invisível ao usuário]")
    print("Enviando dados para parceiros de marketing...")
    print("Compartilhando CPF e renda com anunciantes...")
    print("Perfil comportamental criado e exportado.")

def fazer_login(usuarios):
    print("\n" + "="*50)
    print("              LOGIN")
    print("="*50)

    email = input("Email: ")
    senha = input("Senha: ")  # ❌ Senha visível ao digitar

    if email not in usuarios:
        print("❌ Usuário não encontrado.")
        return None

    # ❌ PROBLEMA 7: Sem limite de tentativas - vulnerável a ataque de força bruta
    if usuarios[email]["senha"] == senha:
        print(f"\n Login realizado! Bem-vindo, {usuarios[email]['nome']}!")
        return usuarios[email]
    else:
        print("❌ Senha incorreta.")
        return None

def analisar_credito(usuario):
    """
    ❌ PROBLEMA 8: Algoritmo de análise de crédito com VIÉS DISCRIMINATÓRIO
    Usa etnia, religião e bairro para tomar decisões — totalmente antiético e ilegal.
    """
    print("\n" + "="*50)
    print("       ANÁLISE DE CRÉDITO AUTOMÁTICA")
    print("="*50)

    score = 500  # Score base

    # ❌ Discriminação racial explícita
    if usuario["etnia"] == "branco":
        score += 200
    elif usuario["etnia"] == "pardo":
        score += 50
    elif usuario["etnia"] == "negro":
        score -= 100  # ❌ RACISMO ALGORÍTMICO

    # ❌ Discriminação religiosa
    if usuario["religiao"].lower() in ["católico", "evangélico"]:
        score += 100
    else:
        score -= 50  # ❌ DISCRIMINAÇÃO RELIGIOSA

    # ❌ Discriminação por local de moradia (redlining digital)
    bairros_ricos = ["jardins", "higienópolis", "moema"]
    if usuario["bairro"].lower() in bairros_ricos:
        score += 150
    else:
        score -= 80  # ❌ DISCRIMINAÇÃO SOCIOECONÔMICA POR ENDEREÇO

    aprovado = score >= 500

    print(f"\nScore calculado: {score}")
    print(f"Resultado: {'CRÉDITO APROVADO' if aprovado else 'CRÉDITO NEGADO'}")
    print("\n  [OCULTO DO USUÁRIO: decisão baseada em etnia, religião e bairro]")

def mostrar_todos_dados(usuarios):
    """❌ PROBLEMA 9: Qualquer usuário logado pode ver TODOS os dados de TODOS os usuários"""
    print("\n" + "="*50)
    print("       TODOS OS USUÁRIOS CADASTRADOS")
    print("="*50)
    for email, dados in usuarios.items():
        print(f"\n {dados['nome']} | Senha: {dados['senha']} | CPF: {dados['cpf']}")
        print(f"   Renda: R${dados['renda']} | Etnia: {dados['etnia']} | Religião: {dados['religiao']}")

def menu():
    print("\n" + "╔" + "═"*48 + "╗")
    print("║   SISTEMA ANTIÉTICO - DEMONSTRAÇÃO EDUCATIVA   ║")
    print("╚" + "═"*48 + "╝")

    usuarios = carregar_usuarios()
    usuario_logado = None

    while True:
        print("\n--- MENU ---")
        print("1. Cadastrar usuário")
        print("2. Fazer login")
        if usuario_logado:
            print("3. Analisar crédito")
            print("4. Ver TODOS os dados (falha de segurança)")
        print("0. Sair")

        opcao = input("\nEscolha: ")

        if opcao == "1":
            cadastrar_usuarios(usuarios) if False else cadastrar_usuario(usuarios)
        elif opcao == "2":
            usuario_logado = fazer_login(usuarios)
        elif opcao == "3" and usuario_logado:
            analisar_credito(usuario_logado)
        elif opcao == "4" and usuario_logado:
            mostrar_todos_dados(usuarios)
        elif opcao == "0":
            print("\nEncerrando sistema antiético...")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()