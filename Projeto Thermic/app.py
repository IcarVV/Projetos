import io
import os
import socket
import sqlite3
import sys
from datetime import date, datetime

from flask import Flask, jsonify, request, send_file, send_from_directory
from openpyxl import Workbook
from openpyxl.styles import Font

ALERTA_MIN = 15  # pausa aberta há mais minutos que isso fica em vermelho
MOTIVOS = ["Pausa pessoal", "Café/Lanche", "Solicitação de material", "Retirada de material",
           "Desvio de foco", "Manutenção de máquina", "Aguardando gestão", "Não identificado", 
           "Início/Término de serviço", "Aguardando liberação/Inspeção", "Troca de EPI",
           "Reunião/Treinamento", "Aguardando serviço", "Aguardando documentação"]

# no .exe (PyInstaller) os arquivos (index.html, logo, banco) ficam na pasta do próprio executável
PASTA = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(PASTA, "cronoanalise.db")
CAMPOS = ("entrada", "saida_almoco", "volta_almoco", "saida_final")
app = Flask(__name__)


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


with db() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS turnos(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, nome TEXT,
        processo TEXT, entrada TEXT, saida_almoco TEXT, volta_almoco TEXT, saida_final TEXT);
    CREATE TABLE IF NOT EXISTS pausas(id INTEGER PRIMARY KEY AUTOINCREMENT, turno_id INTEGER,
        os TEXT, inicio TEXT, fim TEXT, motivo TEXT);""")


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


if __name__ == "__main__":
    print(f"\nNeste PC: http://127.0.0.1:5000\nCelulares e outros PCs (mesma rede): http://{ip_local()}:5000\n")
    print(f"Pasta dos arquivos: {PASTA}")
    for f in ("index.html", "LogoThermic.png", "LogoThermic.ico"):
        if not os.path.exists(os.path.join(PASTA, f)):
            print(f"ATENCAO: {f} nao foi encontrado nessa pasta")
    try:
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:  # mostra o erro em vez de fechar a janela de uma vez
        print("\nERRO:", e)
        input("Pressione Enter para fechar...")
