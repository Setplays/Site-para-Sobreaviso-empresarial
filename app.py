import sqlite3
import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# --- Configuração Inicial ---
app = Flask(__name__)
CORS(app) 
DATABASE = 'sobreaviso.db'

# --- Funções de Banco de Dados ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        
        try:
            db.execute(
                "INSERT INTO Participantes (nome, ordem_rotacao, telefone) VALUES (?, ?, ?), (?, ?, ?), (?, ?, ?)",
                (
                    "Anderson Silva", 1, "(21) 99999-1111", 
                    "Lucas Salgado", 2, "(21) 99999-2222", 
                    "Victor Vianna", 3, "(21) 99999-3333"
                )
            )
            
            hoje = datetime.date.today()
            dias_ate_ultima_sexta = (hoje.weekday() - 4) % 7
            data_inicio = hoje - datetime.timedelta(days=dias_ate_ultima_sexta)
            
            db.execute(
                "INSERT INTO Configuracao (id, data_inicio_ciclo) VALUES (?, ?)",
                (1, data_inicio.isoformat())
            )
            db.commit()
            print("Banco de dados inicializado com dados padrão (incluindo telefones e tabela de log).")
        except sqlite3.IntegrityError:
            print("O banco de dados já parece estar populado. Ignorando inicialização de dados.")
        except Exception as e:
            print(f"Erro ao inicializar dados: {e}")

# --- API Endpoints: Sobreaviso ---

@app.route('/api/sobreaviso-atual', methods=['GET'])
def get_sobreaviso_atual():
    # (Código desta função não mudou)
    try:
        db = get_db()
        config = db.execute("SELECT data_inicio_ciclo FROM Configuracao WHERE id = 1").fetchone()
        if not config:
            return jsonify({"erro": "Configuração 'data_inicio_ciclo' não encontrada."}), 500
        
        participantes_raw = db.execute("SELECT * FROM Participantes ORDER BY ordem_rotacao ASC").fetchall()
        if not participantes_raw:
            return jsonify({"erro": "Nenhum participante cadastrado."}), 404
        
        participantes = [dict(row) for row in participantes_raw]
        total_participantes = len(participantes)
        
        data_inicio = datetime.date.fromisoformat(config['data_inicio_ciclo'])
        hoje = datetime.date.today()
        diferenca_dias = (hoje - data_inicio).days
        semanas_passadas = diferenca_dias // 7
        indice_atual = semanas_passadas % total_participantes
        
        pessoa_de_sobreaviso = participantes[indice_atual]
        return jsonify(pessoa_de_sobreaviso)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes', methods=['GET'])
def get_participantes():
    # (Código desta função não mudou)
    db = get_db()
    participantes_raw = db.execute("SELECT * FROM Participantes ORDER BY ordem_rotacao ASC").fetchall()
    participantes = [dict(row) for row in participantes_raw]
    return jsonify(participantes)

@app.route('/api/participantes', methods=['POST'])
def add_participante():
    # (Código desta função não mudou)
    dados = request.get_json()
    if not dados or 'nome' not in dados:
        return jsonify({"erro": "Dados incompletos. 'nome' é obrigatório."}), 400
    telefone = dados.get('telefone', None) 
    try:
        db = get_db()
        max_ordem_result = db.execute("SELECT MAX(ordem_rotacao) as max_o FROM Participantes").fetchone()
        nova_ordem = 1 
        if max_ordem_result and max_ordem_result['max_o'] is not None:
            nova_ordem = max_ordem_result['max_o'] + 1
        cursor = db.execute(
            "INSERT INTO Participantes (nome, ordem_rotacao, telefone) VALUES (?, ?, ?)",
            (dados['nome'], nova_ordem, telefone)
        )
        db.commit()
        novo_id = cursor.lastrowid
        return jsonify({
            "id": novo_id, "nome": dados['nome'], "ordem_rotacao": nova_ordem, "telefone": telefone
        }), 201
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes/<int:id>', methods=['PUT'])
def update_participante(id):
    # (Código desta função não mudou)
    dados = request.get_json()
    if not dados or 'nome' not in dados or 'ordem_rotacao' not in dados:
        return jsonify({"erro": "Dados incompletos."}), 400
    telefone = dados.get('telefone', None) 
    try:
        db = get_db()
        db.execute(
            "UPDATE Participantes SET nome = ?, ordem_rotacao = ?, telefone = ? WHERE id = ?",
            (dados['nome'], dados['ordem_rotacao'], telefone, id)
        )
        db.commit()
        return jsonify({"sucesso": "Participante atualizado."})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes/<int:id>', methods=['DELETE'])
def delete_participante(id):
    # (Código desta função não mudou)
    try:
        db = get_db()
        db.execute("DELETE FROM Participantes WHERE id = ?", (id,))
        db.commit()
        return jsonify({"sucesso": "Participante removido."})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# --- NOVOS ENDPOINTS: Histórico de Acesso ---

@app.route('/api/admin-log', methods=['POST'])
def log_admin_access():
    """Registra um IP e data/hora no banco de dados."""
    try:
        db = get_db()
        
        # Pega o IP do requisitante. 
        # 'request.remote_addr' pega o IP de quem fez a chamada.
        ip_address = request.remote_addr
        
        # Pega a data e hora atual
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        
        db.execute(
            "INSERT INTO AcessosAdmin (ip_address, timestamp) VALUES (?, ?)",
            (ip_address, timestamp)
        )
        db.commit()
        return jsonify({"sucesso": "Log registrado"}), 201
    except Exception as e:
        print(f"Erro ao registrar log: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/api/admin-log', methods=['GET'])
def get_admin_log():
    """Retorna os últimos 20 logs de acesso."""
    try:
        db = get_db()
        logs_raw = db.execute(
            "SELECT ip_address, timestamp FROM AcessosAdmin ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        
        logs = [dict(row) for row in logs_raw]
        return jsonify(logs)
    except Exception as e:
        print(f"Erro ao buscar logs: {e}")
        return jsonify({"erro": str(e)}), 500


# --- Inicialização do Script ---

if __name__ == '__main__':
    import os
    if not os.path.exists(DATABASE):
        print("Criando banco de dados...")
        with open('schema.sql', 'w') as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS Participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ordem_rotacao INTEGER NOT NULL, -- Correção: UNIQUE removido
                telefone TEXT 
            );
            
            CREATE TABLE IF NOT EXISTS Configuracao (
                id INTEGER PRIMARY KEY,
                data_inicio_ciclo TEXT NOT NULL
            );
            
            -- NOVA TABELA: Para o histórico de acessos
            CREATE TABLE IF NOT EXISTS AcessosAdmin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            """)
        init_db()
        
    app.run(debug=True)