"""
╔══════════════════════════════════════════════════════════════════╗
║             SISTEMA DE CADASTRO - VERSÃO ÉTICA                   ║
║           Boas práticas de privacidade e segurança               ║
║         Trabalho: Ética no Desenvolvimento de Software           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os
import hashlib
import hmac
import secrets
import re
from datetime import datetime

# Arquivo separado, poderia ser um banco com criptografia em produção
ARQUIVO_USUARIOS = "usuarios_eticos.json"
MAX_TENTATIVAS_LOGIN = 3
tentativas_login = {}

# Funções de criptografia segura para senhas
def gerar_salt():
    """Gera um salt aleatório único para cada senha"""
    return secrets.token_hex(32)

def hash_senha(senha: str, salt: str) -> str:
    """Gera um hash seguro da senha com PBKDF2 + SHA-256"""
    chave = hashlib.pbkdf2_hmac(
        'sha256',
        senha.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100_000  # 100 mil iterações dificulta força bruta
    )
    return chave.hex()

def verificar_senha(senha_digitada: str, salt: str, hash_armazenado: str) -> bool:
    """Compara senhas de forma segura, sem vulnerabilidade de timing attack"""
    hash_tentativa = hash_senha(senha_digitada, salt)
    return hmac.compare_digest(hash_tentativa, hash_armazenado)  # Comparação segura

def validar_email(email: str) -> bool:
    padrao = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return re.match(padrao, email) is not None

def validar_senha_forte(senha: str) -> tuple[bool, str]:
    """✅ Garante que a senha tenha requisitos mínimos de segurança"""
    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    if not re.search(r'[A-Z]', senha):
        return False, "A senha deve ter pelo menos uma letra maiúscula."
    if not re.search(r'[0-9]', senha):
        return False, "A senha deve ter pelo menos um número."
    return True, "Senha válida."

def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, "r") as f:
            return json.load(f)
    return {}

def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=4)
        # ✅ Senhas nunca são salvas em texto puro — apenas o hash

def exibir_termo_consentimento() -> bool:
    """✅ BOA PRÁTICA 3: Consentimento informado antes de coletar qualquer dado"""
    print("\n" + "="*60)
    print("             TERMO DE USO E PRIVACIDADE")
    print("="*60)
    print("""
Este sistema coleta APENAS os dados estritamente necessários:
  • Nome e email: para identificação e contato
  • Senha (armazenada como HASH, nunca em texto puro)

✅ Seus dados NÃO serão vendidos ou compartilhados.
✅ Você pode solicitar a exclusão da sua conta a qualquer momento.
✅ Nenhum dado sensível (etnia, religião, etc.) será coletado.

Em conformidade com a LGPD (Lei Geral de Proteção de Dados).
    """)
    resposta = input("Você concorda com os termos? (s/n): ").strip().lower()
    return resposta == "s"

def cadastrar_usuario(usuarios):
    print("\n" + "="*50)
    print("         CADASTRO DE NOVO USUÁRIO")
    print("="*50)

    # ✅ BOA PRÁTICA 4: Consentimento antes de qualquer coleta
    if not exibir_termo_consentimento():
        print("\n⚠️  Cadastro cancelado. Consentimento não fornecido.")
        return

    nome = input("\nNome completo: ").strip()
    if not nome:
        print("❌ Nome não pode ser vazio.")
        return

    email = input("Email: ").strip().lower()
    if not validar_email(email):
        print("❌ Email inválido.")
        return

    if email in usuarios:
        print("❌ Este email já está cadastrado.")
        return

    # ✅ BOA PRÁTICA 5: Senha com getpass (não exibe na tela)
    import getpass
    senha = getpass.getpass("Senha (não será exibida): ")
    valida, mensagem = validar_senha_forte(senha)
    if not valida:
        print(f"❌ {mensagem}")
        return

    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("❌ As senhas não coincidem.")
        return

    # ✅ BOA PRÁTICA 6: Hash + salt único por usuário
    salt = gerar_salt()
    senha_hash = hash_senha(senha, salt)

    # ✅ BOA PRÁTICA 7: Armazenamos APENAS o necessário
    usuarios[email] = {
        "nome": nome,
        "email": email,
        "senha_hash": senha_hash,   # ✅ Apenas o hash
        "salt": salt,               # ✅ Salt único
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        # ❌ NÃO coletamos: CPF, renda, etnia, religião, bairro
    }

    salvar_usuarios(usuarios)
    print("\n✅ Cadastro realizado com sucesso!")
    print("🔒 Sua senha foi armazenada de forma segura (hash criptográfico).")

def fazer_login(usuarios):
    print("\n" + "="*50)
    print("              LOGIN SEGURO")
    print("="*50)

    import getpass
    email = input("Email: ").strip().lower()

    # ✅ BOA PRÁTICA 8: Limite de tentativas contra força bruta
    if tentativas_login.get(email, 0) >= MAX_TENTATIVAS_LOGIN:
        print(f"❌ Conta temporariamente bloqueada após {MAX_TENTATIVAS_LOGIN} tentativas.")
        print("   Entre em contato com o suporte para desbloquear.")
        return None

    senha = getpass.getpass("Senha: ")

    if email not in usuarios:
        # ✅ BOA PRÁTICA 9: Mensagem genérica para não revelar se o email existe
        print("❌ Email ou senha incorretos.")
        return None

    usuario = usuarios[email]
    if verificar_senha(senha, usuario["salt"], usuario["senha_hash"]):
        tentativas_login[email] = 0  # ✅ Reseta contador após sucesso
        print(f"\n✅ Login realizado! Bem-vindo, {usuario['nome']}!")
        return usuario
    else:
        tentativas_login[email] = tentativas_login.get(email, 0) + 1
        restantes = MAX_TENTATIVAS_LOGIN - tentativas_login[email]
        print(f"❌ Email ou senha incorretos. Tentativas restantes: {restantes}")
        return None

def analisar_credito(usuario):
    """
    ✅ BOA PRÁTICA 10: Análise de crédito JUSTA — baseada apenas em critérios
    financeiros objetivos, sem viés discriminatório.
    """
    print("\n" + "="*50)
    print("       ANÁLISE DE CRÉDITO TRANSPARENTE")
    print("="*50)

    print("\nPara análise de crédito, precisamos de informações financeiras.")
    print("ℹ️  Esses dados são usados APENAS para esta análise e não serão armazenados.\n")

    try:
        renda = float(input("Renda mensal líquida (R$): "))
        dividas = float(input("Total de dívidas atuais (R$): "))
        meses_emprego = int(input("Meses no emprego atual: "))
        valor_solicitado = float(input("Valor do crédito solicitado (R$): "))
    except ValueError:
        print("❌ Valores inválidos.")
        return

    # ✅ Critérios objetivos, financeiros e transparentes
    score = 0
    detalhes = []

    # Comprometimento de renda (máx 30%)
    comprometimento = (dividas / renda * 100) if renda > 0 else 100
    if comprometimento < 20:
        score += 300
        detalhes.append("✅ Baixo comprometimento de renda (+300)")
    elif comprometimento < 30:
        score += 150
        detalhes.append("⚠️  Comprometimento moderado (+150)")
    else:
        score += 0
        detalhes.append("❌ Alto comprometimento de renda (+0)")

    # Estabilidade no emprego
    if meses_emprego >= 24:
        score += 200
        detalhes.append("✅ Emprego estável há 2+ anos (+200)")
    elif meses_emprego >= 12:
        score += 100
        detalhes.append("⚠️  Emprego estável há 1+ ano (+100)")
    else:
        score += 30
        detalhes.append("⚠️  Emprego recente (+30)")

    # Relação valor solicitado / renda
    meses_para_pagar = valor_solicitado / renda if renda > 0 else 9999
    if meses_para_pagar <= 6:
        score += 200
        detalhes.append("✅ Valor compatível com renda (+200)")
    elif meses_para_pagar <= 12:
        score += 100
        detalhes.append("⚠️  Valor razoável (+100)")
    else:
        score += 0
        detalhes.append("❌ Valor elevado para renda (+0)")

    print("\n📊 RELATÓRIO TRANSPARENTE:")
    print("-" * 40)
    for detalhe in detalhes:
        print(f"  {detalhe}")
    print(f"\n  Score final: {score}/700")
    print("-" * 40)

    aprovado = score >= 400
    print(f"\nResultado: {'✅ CRÉDITO APROVADO' if aprovado else '❌ CRÉDITO NEGADO'}")
    print("\nℹ️  Esta decisão foi baseada EXCLUSIVAMENTE em critérios financeiros.")
    print("   Raça, religião, gênero ou endereço NÃO influenciam esta análise.")

def ver_meus_dados(usuario):
    """✅ BOA PRÁTICA 11: Usuário pode ver APENAS os próprios dados (LGPD Art. 18)"""
    print("\n" + "="*50)
    print("          MEUS DADOS CADASTRADOS")
    print("="*50)
    print(f"\n  Nome:         {usuario['nome']}")
    print(f"  Email:        {usuario['email']}")
    print(f"  Senha:        *** (armazenada de forma segura)")
    print(f"  Cadastro em:  {usuario['criado_em']}")
    print("\n  ℹ️  Nenhum outro dado seu está armazenado.")

def excluir_conta(usuarios, email):
    """✅ BOA PRÁTICA 12: Direito ao esquecimento (LGPD Art. 18, VI)"""
    confirmacao = input("\n⚠️  Tem certeza que deseja excluir sua conta? (s/n): ").lower()
    if confirmacao == "s":
        del usuarios[email]
        salvar_usuarios(usuarios)
        print("✅ Conta excluída com sucesso. Todos os seus dados foram removidos.")
        return True
    return False

def menu():
    print("\n" + "╔" + "═"*48 + "╗")
    print("║     ✅  SISTEMA ÉTICO - DEMONSTRAÇÃO EDUCATIVA ║")
    print("╚" + "═"*48 + "╝")

    usuarios = carregar_usuarios()
    usuario_logado = None

    while True:
        print("\n--- MENU ---")
        print("1. Cadastrar usuário")
        print("2. Fazer login")
        if usuario_logado:
            print("3. Analisar crédito")
            print("4. Ver meus dados")
            print("5. Excluir minha conta")
            print("6. Logout")
        print("0. Sair")

        opcao = input("\nEscolha: ")

        if opcao == "1":
            cadastrar_usuario(usuarios)
        elif opcao == "2":
            usuario_logado = fazer_login(usuarios)
        elif opcao == "3" and usuario_logado:
            analisar_credito(usuario_logado)
        elif opcao == "4" and usuario_logado:
            ver_meus_dados(usuario_logado)
        elif opcao == "5" and usuario_logado:
            if excluir_conta(usuarios, usuario_logado["email"]):
                usuario_logado = None
        elif opcao == "6" and usuario_logado:
            print(f"Até logo, {usuario_logado['nome']}!")
            usuario_logado = None
        elif opcao == "0":
            print("\nEncerrando sistema. Até mais!")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()