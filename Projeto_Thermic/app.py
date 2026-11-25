import io
import logging
import os
import secrets
import socket
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, redirect, request, send_file, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from openpyxl import Workbook
from openpyxl.styles import Font

HORA_LIMPEZA = "23:55"  # todo dia, nesse horário: backup do banco e limpeza (nenhum registro é apagado)
DIAS_BACKUP = 60  # backups mais antigos que isso são apagados
ALERTA_MIN = 15  # pausa aberta há mais minutos que isso fica em vermelho
MOTIVOS = ["Pausa pessoal", "Café/Lanche", "Solicitação de material", "Retirada de material",
           "Desvio de foco", "Manutenção de máquina", "Aguardando gestão", "Não identificado", 
           "Início/Término de serviço", "Aguardando liberação/Inspeção", "Troca de EPI",
           "Reunião/Treinamento", "Aguardando serviço", "Aguardando documentação"]

# no .exe (PyInstaller) os arquivos (index.html, logo, banco) ficam na pasta do próprio executável
PASTA = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(PASTA, "cronoanalise.db")
BACKUP = os.path.join(PASTA, "backup")
CAMPOS = ("entrada", "saida_almoco", "volta_almoco", "saida_final")
app = Flask(__name__)


@contextmanager
def db():
    """Abre o banco, confirma (commit) no fim e SEMPRE fecha a conexão."""
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


with db() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS turnos(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, nome TEXT,
        processo TEXT, entrada TEXT, saida_almoco TEXT, volta_almoco TEXT, saida_final TEXT);
    CREATE TABLE IF NOT EXISTS pausas(id INTEGER PRIMARY KEY AUTOINCREMENT, turno_id INTEGER,
        os TEXT, inicio TEXT, fim TEXT, motivo TEXT);
    CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, login TEXT UNIQUE,
        senha TEXT, ativo INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS config(chave TEXT PRIMARY KEY, valor TEXT);""")


def agora():
    return datetime.now().strftime("%H:%M:%S")


def hora(v):
    """'HH:MM' -> 'HH:MM:SS'; vazio -> None."""
    v = (v or "").strip()
    return None if not v else (v if len(v) == 8 else v + ":00")


def seg(h):
    a, b, c = map(int, h.split(":"))
    return a * 3600 + b * 60 + c


def dados(data):
    """Turnos e pausas do dia, com os tempos calculados em segundos."""
    hoje = data == date.today().isoformat()
    ag = seg(agora())
    with db() as c:
        ts = [dict(r) for r in c.execute("SELECT * FROM turnos WHERE data=? ORDER BY entrada, id", (data,))]
        ps = [dict(r) for r in c.execute(
            "SELECT p.*, t.nome, t.processo FROM pausas p JOIN turnos t ON t.id=p.turno_id "
            "WHERE t.data=? ORDER BY p.inicio, p.id", (data,))]
    for p in ps:  
        fim = seg(p["fim"]) if p["fim"] else (ag if hoje else seg(p["inicio"]))
        p["dur"] = max(0, fim - seg(p["inicio"]))
    for t in ts:
        fim = seg(t["saida_final"]) if t["saida_final"] else (ag if hoje else seg(t["entrada"]))
        pres = max(0, fim - seg(t["entrada"]))
        alm = 0
        if t["saida_almoco"]:
            volta = seg(t["volta_almoco"]) if t["volta_almoco"] else fim
            alm = max(0, volta - seg(t["saida_almoco"]))
        pau = sum(p["dur"] for p in ps if p["turno_id"] == t["id"])
        t.update(pres=pres, alm=alm, pau=pau, tot=max(0, pres - alm), trab=max(0, pres - alm - pau))
    return ts, ps


# ---------- usuários (login e senha) e senha de administrador ----------
def cfg_get(k):
    with db() as c:
        r = c.execute("SELECT valor FROM config WHERE chave=?", (k,)).fetchone()
    return r["valor"] if r else None


def cfg_set(k, v):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO config(chave,valor) VALUES(?,?)", (k, v))


if not cfg_get("secret"):
    cfg_set("secret", secrets.token_hex(32))  # guardada no banco: os logins sobrevivem a reinícios
app.secret_key = cfg_get("secret")
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(SESSION_COOKIE_NAME="thermic_sessao", SESSION_COOKIE_SAMESITE="Lax")
PUBLICAS = ("/login", "/admin", "/logo", "/LogoThermic.ico", "/favicon.ico", "/api/login", "/api/logout", "/api/eu")
FALHAS = {}  # ip -> (erros seguidos, bloqueado até)


def usuario_atual():
    uid = session.get("uid")
    if not uid:
        return None
    with db() as c:
        return c.execute("SELECT id, nome FROM usuarios WHERE id=? AND ativo=1", (uid,)).fetchone()


def admin_ativo():
    return session.get("admin_ate", 0) > time.time()  # o modo administrador dura 30 min


def bloqueado():
    return FALHAS.get(request.remote_addr, (0, 0))[1] > time.time()


def falha():
    ip = request.remote_addr
    n = FALHAS.get(ip, (0, 0))[0] + 1
    FALHAS[ip] = (0, time.time() + 60) if n >= 5 else (n, 0)


@app.before_request
def exigir_login():
    p = request.path
    if p in PUBLICAS or p.startswith("/api/admin/") or usuario_atual():
        return None
    if p.startswith("/api/"):
        return "Faça login para continuar.", 401
    return redirect("/login")


@app.get("/login")
@app.get("/admin")
def pagina_acesso():
    return send_from_directory(PASTA, "acesso.html")


@app.get("/api/eu")
def api_eu():
    u = usuario_atual()
    return jsonify(logado=bool(u), admin=admin_ativo(), admin_definida=bool(cfg_get("admin")))


@app.post("/api/login")
def api_login():
    if bloqueado():
        return "Muitas tentativas. Aguarde 1 minuto.", 429
    j = request.get_json()
    with db() as c:
        u = c.execute("SELECT * FROM usuarios WHERE login=? AND ativo=1", ((j.get("login") or "").strip().lower(),)).fetchone()
    if not u or not check_password_hash(u["senha"], j.get("senha") or ""):
        falha()
        return "Login ou senha incorretos.", 401
    FALHAS.pop(request.remote_addr, None)
    session.clear()
    session.permanent = True
    session["uid"] = u["id"]
    return jsonify(ok=True)


@app.post("/api/logout")
def api_logout():
    session.pop("uid", None)
    return jsonify(ok=True)


@app.post("/api/admin/entrar")
def admin_entrar():
    if bloqueado():
        return "Muitas tentativas. Aguarde 1 minuto.", 429
    h = cfg_get("admin")
    if not h or not check_password_hash(h, request.get_json().get("senha") or ""):
        falha()
        return "Senha de administrador incorreta.", 401
    FALHAS.pop(request.remote_addr, None)
    session.permanent = True
    session["admin_ate"] = time.time() + 1800
    return jsonify(ok=True)


@app.post("/api/admin/sair")
def admin_sair():
    session.pop("admin_ate", None)
    return jsonify(ok=True)


@app.post("/api/admin/definir")
def admin_definir():
    """Cria a senha de administrador (só no PC do servidor) ou troca, se já estiver no modo administrador."""
    if not cfg_get("admin") and request.remote_addr not in ("127.0.0.1", "::1"):
        return "A senha de administrador só pode ser criada no PC do servidor: abra http://127.0.0.1:5000/admin nele.", 403
    if cfg_get("admin") and not admin_ativo():
        return "Entre como administrador primeiro.", 401
    nova = request.get_json().get("senha") or ""
    if len(nova) < 4:
        return "A senha deve ter pelo menos 4 caracteres.", 400
    cfg_set("admin", generate_password_hash(nova))
    session.permanent = True
    session["admin_ate"] = time.time() + 1800
    return jsonify(ok=True)


@app.get("/api/admin/usuarios")
def admin_lista():
    if not admin_ativo():
        return "Entre como administrador.", 401
    with db() as c:
        return jsonify([dict(r) for r in c.execute("SELECT id, nome, login, ativo FROM usuarios ORDER BY nome")])


@app.post("/api/admin/usuarios")
def admin_novo():
    if not admin_ativo():
        return "Entre como administrador.", 401
    j = request.get_json()
    nome, login, senha = (j.get("nome") or "").strip(), (j.get("login") or "").strip().lower(), j.get("senha") or ""
    if not nome or len(login) < 3 or " " in login:
        return "Informe o nome e um login de pelo menos 3 letras, sem espaços.", 400
    if len(senha) < 4:
        return "A senha deve ter pelo menos 4 caracteres.", 400
    with db() as c:
        if c.execute("SELECT 1 FROM usuarios WHERE login=?", (login,)).fetchone():
            return "Esse login já existe.", 400
        c.execute("INSERT INTO usuarios(nome,login,senha) VALUES(?,?,?)", (nome, login, generate_password_hash(senha)))
    return jsonify(ok=True)


@app.post("/api/admin/usuarios/<int:i>")
def admin_edita(i):
    if not admin_ativo():
        return "Entre como administrador.", 401
    j = request.get_json()
    senha = j.get("senha") or ""
    if senha and len(senha) < 4:
        return "A senha deve ter pelo menos 4 caracteres.", 400
    with db() as c:
        if "ativo" in j:  # desativar não apaga nada: o histórico continua
            c.execute("UPDATE usuarios SET ativo=? WHERE id=?", (1 if j["ativo"] else 0, i))
        if senha:
            c.execute("UPDATE usuarios SET senha=? WHERE id=?", (generate_password_hash(senha), i))
    return jsonify(ok=True)


@app.get("/")
def index():
    return send_from_directory(PASTA, "index.html")


@app.get("/logo")
def logo():
    return send_from_directory(PASTA, "LogoThermic.png")  

@app.get("/LogoThermic.ico")
@app.get("/favicon.ico")
def favicon():
    return send_from_directory(PASTA, "LogoThermic.ico") 

@app.get("/api/dia")
def api_dia():
    data = request.args.get("data") or date.today().isoformat()
    ts, ps = dados(data)
    return jsonify(data=data, hoje=date.today().isoformat(), agora=agora(),  
                   usuario=(usuario_atual() or {"nome": ""})["nome"],
                   turnos=ts, pausas=ps, motivos=MOTIVOS, alerta_min=ALERTA_MIN)


@app.post("/api/turno")
def novo_turno():
    j = request.get_json()
    nome, proc = j["nome"].strip(), j["processo"].strip()
    if not nome or not proc:
        return "Informe o nome e o processo do operador.", 400
    with db() as c:
        if c.execute("SELECT 1 FROM turnos WHERE data=? AND lower(nome)=lower(?)", (j["data"], nome)).fetchone():
            return "Esse operador já tem entrada registrada neste dia.", 400
        c.execute("INSERT INTO turnos(data,nome,processo,entrada) VALUES(?,?,?,?)",
                  (j["data"], nome, proc, hora(j.get("hora")) or agora()))
    return jsonify(ok=True)


@app.post("/api/turno/<int:i>")
def set_turno(i):
    j = request.get_json()
    if j["campo"] not in CAMPOS:
        return "Campo inválido.", 400
    v = hora(j["hora"]) if "hora" in j else agora()  
    if j["campo"] == "entrada" and not v:
        return "A entrada não pode ficar vazia.", 400
    with db() as c:
        c.execute(f"UPDATE turnos SET {j['campo']}=? WHERE id=?", (v, i))
    return jsonify(ok=True)


@app.delete("/api/turno/<int:i>")
def del_turno(i):
    with db() as c:
        c.execute("DELETE FROM pausas WHERE turno_id=?", (i,))
        c.execute("DELETE FROM turnos WHERE id=?", (i,))
    return jsonify(ok=True)


@app.post("/api/pausa")
def nova_pausa():
    j = request.get_json()
    if not j.get("motivo", "").strip():
        return "Informe o motivo da pausa.", 400
    with db() as c:
        if c.execute("SELECT 1 FROM pausas WHERE turno_id=? AND fim IS NULL", (j["turno_id"],)).fetchone():
            return "Esse operador já tem uma pausa aberta. Feche-a antes de abrir outra.", 400
        c.execute("INSERT INTO pausas(turno_id,os,inicio,motivo) VALUES(?,?,?,?)",
                  (j["turno_id"], j.get("os", "").strip(), hora(j.get("hora")) or agora(), j["motivo"].strip()))
    return jsonify(ok=True)


@app.post("/api/pausa/<int:i>")
def set_pausa(i):
    j = request.get_json()
    if j["campo"] not in ("inicio", "fim"):
        return "Campo inválido.", 400
    v = hora(j["hora"]) if "hora" in j else agora()
    if j["campo"] == "inicio" and not v:
        return "O início não pode ficar vazio.", 400
    with db() as c:
        c.execute(f"UPDATE pausas SET {j['campo']}=? WHERE id=?", (v, i))
    return jsonify(ok=True)


@app.delete("/api/pausa/<int:i>")
def del_pausa(i):
    with db() as c:
        c.execute("DELETE FROM pausas WHERE id=?", (i,))
    return jsonify(ok=True)


@app.get("/exportar")
def exportar():
    data = request.args.get("data") or date.today().isoformat()
    ts, ps = dados(data)
    d = lambda s: s / 86400
    wb = Workbook()
    a = wb.active
    a.title = "Entrada e Saída"
    a.append(["Data", "Operador", "Processo", "Entrada", "Saída almoço", "Volta almoço", "Saída final",
              "Tempo presente", "Almoço", "Tempo total", "Pausas", "Tempo real de trabalho"])
    for t in ts:
        a.append([data, t["nome"], t["processo"], t["entrada"], t["saida_almoco"], t["volta_almoco"],
                  t["saida_final"], d(t["pres"]), d(t["alm"]), d(t["tot"]), d(t["pau"]), d(t["trab"])])
    b = wb.create_sheet("Pausas")
    b.append(["Data", "Operador", "Processo", "OP/Peça", "Início", "Fim", "Duração", "Motivo"])
    for p in ps:
        b.append([data, p["nome"], p["processo"], p["os"], p["inicio"], p["fim"], d(p["dur"]), p["motivo"]])
    for ws, cols in ((a, "HIJKL"), (b, "G")):
        for cel in ws[1]:
            cel.font = Font(bold=True)
        ws.freeze_panes = "A2"
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 22
        for col in cols:
            for cel in ws[col][1:]:
                cel.number_format = "[h]:mm:ss"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"cronoanalise_{data}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def sem_quickedit():
    """No Windows, clicar na janela preta entra no modo de seleção e PAUSA o programa. Isto desliga esse modo."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)  # entrada do console
        m = ctypes.c_uint32()
        k.GetConsoleMode(h, ctypes.byref(m))
        k.SetConsoleMode(h, (m.value & ~0x0040) | 0x0080)
    except Exception:
        pass


def cabecalho():
    print(f"\nNeste PC: http://127.0.0.1:5000\nCelulares e outros PCs (mesma rede): http://{ip_local()}:5000\n")
    print(f"Pasta dos arquivos: {PASTA}")
    for f in ("index.html", "acesso.html", "LogoThermic.png", "LogoThermic.ico"):
        if not os.path.exists(os.path.join(PASTA, f)):
            print(f"ATENCAO: {f} nao foi encontrado nessa pasta")
    print(f"Limpeza diaria com backup as {HORA_LIMPEZA} (pasta backup)")
    print("Cadastro de usuarios e senha de administrador: http://127.0.0.1:5000/admin\n")


def limpeza():
    """Backup do banco, compactação e limpeza da janela. Não apaga nenhum registro."""
    os.makedirs(BACKUP, exist_ok=True)
    destino = os.path.join(BACKUP, f"cronoanalise_{date.today().isoformat()}.db")
    with db() as c:
        copia = sqlite3.connect(destino)
        try:
            c.backup(copia)
        finally:
            copia.close()
    try:  # compacta o arquivo do banco
        c = sqlite3.connect(DB, isolation_level=None)
        c.execute("VACUUM")
        c.close()
    except sqlite3.Error:
        pass
    limite = time.time() - DIAS_BACKUP * 86400
    for f in os.listdir(BACKUP):
        p = os.path.join(BACKUP, f)
        if f.endswith(".db") and os.path.getmtime(p) < limite:
            os.remove(p)
    os.system("cls" if os.name == "nt" else "clear")
    cabecalho()
    print(f"Limpeza das {datetime.now():%H:%M} concluida. Backup salvo em {destino}")


def agendador():
    feito = None
    while True:
        try:
            if datetime.now().strftime("%H:%M") >= HORA_LIMPEZA and feito != date.today():
                feito = date.today()
                limpeza()
        except Exception as e:
            print("Falha na limpeza:", e)
        time.sleep(30)


def servir():
    try:
        from waitress import serve  # servidor próprio para ficar ligado por dias
    except ImportError:
        app.run(host="0.0.0.0", port=5000)
    else:
        serve(app, host="0.0.0.0", port=5000, threads=8)


if __name__ == "__main__":
    sem_quickedit()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # não escreve uma linha por requisição na janela
    cabecalho()
    threading.Thread(target=agendador, daemon=True).start()
    try:
        servir()
    except Exception as e:  # mostra o erro em vez de fechar a janela de uma vez
        print("\nERRO:", e)
        input("Pressione Enter para fechar...")
