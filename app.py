import sqlite3
import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# --- Configuração Inicial ---
app = Flask(__name__)
# Habilita CORS (Cross-Origin Resource Sharing) para que seu frontend 
# (mesmo em outro domínio) possa fazer requisições a esta API.
CORS(app) 

DATABASE = 'sobreaviso.db'

# --- Funções de Banco de Dados ---

def get_db():
    """Abre uma nova conexão com o banco de dados se não houver uma no contexto atual."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Retorna linhas como dicionários (mais fácil de converter para JSON)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Fecha a conexão com o banco de dados ao final da requisição."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Função para inicializar o banco de dados (criar as tabelas e inserir dados iniciais)."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        
        # Insere os dados iniciais que você mencionou
        try:
            db.execute(
                "INSERT INTO Participantes (nome, ordem_rotacao) VALUES (?, ?), (?, ?), (?, ?)",
                ("Anderson Silva", 1, "Lucas Salgado", 2, "Victor Vianna", 3)
            )
            
            # DEFINE A DATA DE INÍCIO:
            # Vamos definir como a última sexta-feira.
            hoje = datetime.date.today()
            # 4 é o índice da Sexta-feira (Seg=0, Ter=1, ..., Sex=4, Sab=5, Dom=6)
            dias_ate_ultima_sexta = (hoje.weekday() - 4) % 7
            data_inicio = hoje - datetime.timedelta(days=dias_ate_ultima_sexta)
            
            db.execute(
                "INSERT INTO Configuracao (id, data_inicio_ciclo) VALUES (?, ?)",
                (1, data_inicio.isoformat())
            )
            db.commit()
            print("Banco de dados inicializado com dados padrão.")
        except sqlite3.IntegrityError:
            print("O banco de dados já parece estar populado. Ignorando inicialização de dados.")
        except Exception as e:
            print(f"Erro ao inicializar dados: {e}")

# --- API Endpoints ---

@app.route('/api/sobreaviso-atual', methods=['GET'])
def get_sobreaviso_atual():
    """
    Endpoint principal. Calcula e retorna a pessoa de sobreaviso para a semana atual.
    """
    try:
        db = get_db()
        
        # 1. Buscar a data de início do ciclo
        config = db.execute("SELECT data_inicio_ciclo FROM Configuracao WHERE id = 1").fetchone()
        if not config:
            return jsonify({"erro": "Configuração 'data_inicio_ciclo' não encontrada."}), 500
        
        # 2. Buscar a lista de participantes em ordem
        participantes_raw = db.execute("SELECT * FROM Participantes ORDER BY ordem_rotacao ASC").fetchall()
        if not participantes_raw:
            return jsonify({"erro": "Nenhum participante cadastrado."}), 404
        
        # Converte os resultados para uma lista de dicionários
        participantes = [dict(row) for row in participantes_raw]
        total_participantes = len(participantes)
        
        # 3. A Lógica de Rotação
        data_inicio = datetime.date.fromisoformat(config['data_inicio_ciclo'])
        hoje = datetime.date.today()
        
        # Calcula quantos dias se passaram desde o início do ciclo
        diferenca_dias = (hoje - data_inicio).days
        
        # Calcula quantas semanas completas se passaram
        semanas_passadas = diferenca_dias // 7
        
        # Usa o módulo (resto da divisão) para encontrar o índice na lista
        # Se 3 pessoas, o índice será 0, 1, 2, 0, 1, 2...
        indice_atual = semanas_passadas % total_participantes
        
        pessoa_de_sobreaviso = participantes[indice_atual]
        
        return jsonify(pessoa_de_sobreaviso)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes', methods=['GET'])
def get_participantes():
    """Retorna a lista de todos os participantes, ordenados."""
    db = get_db()
    participantes_raw = db.execute("SELECT * FROM Participantes ORDER BY ordem_rotacao ASC").fetchall()
    participantes = [dict(row) for row in participantes_raw]
    return jsonify(participantes)

@app.route('/api/participantes', methods=['POST'])
def add_participante():
    """Adiciona um novo participante."""
    dados = request.get_json()
    if not dados or 'nome' not in dados or 'ordem_rotacao' not in dados:
        return jsonify({"erro": "Dados incompletos. 'nome' e 'ordem_rotacao' são obrigatórios."}), 400
        
    try:
        db = get_db()
        cursor = db.execute(
            "INSERT INTO Participantes (nome, ordem_rotacao) VALUES (?, ?)",
            (dados['nome'], dados['ordem_rotacao'])
        )
        db.commit()
        
        # Retorna o participante recém-criado com seu novo ID
        novo_id = cursor.lastrowid
        return jsonify({"id": novo_id, "nome": dados['nome'], "ordem_rotacao": dados['ordem_rotacao']}), 201
        
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Um participante com essa ordem ou nome já pode existir."}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes/<int:id>', methods=['PUT'])
def update_participante(id):
    """Atualiza um participante existente (nome ou ordem)."""
    dados = request.get_json()
    if not dados or 'nome' not in dados or 'ordem_rotacao' not in dados:
        return jsonify({"erro": "Dados incompletos. 'nome' e 'ordem_rotacao' são obrigatórios."}), 400

    try:
        db = get_db()
        db.execute(
            "UPDATE Participantes SET nome = ?, ordem_rotacao = ? WHERE id = ?",
            (dados['nome'], dados['ordem_rotacao'], id)
        )
        db.commit()
        return jsonify({"sucesso": "Participante atualizado."})
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/participantes/<int:id>', methods=['DELETE'])
def delete_participante(id):
    """Remove um participante."""
    try:
        db = get_db()
        db.execute("DELETE FROM Participantes WHERE id = ?", (id,))
        db.commit()
        return jsonify({"sucesso": "Participante removido."})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# --- Comando para inicializar o DB ---
@app.cli.command('init-db')
def init_db_command():
    """Cria as tabelas do banco de dados e insere os dados iniciais."""
    init_db()

if __name__ == '__main__':
    # Cria o banco de dados e as tabelas na primeira vez que você rodar,
    # caso o arquivo 'sobreaviso.db' não exista.
    import os
    if not os.path.exists(DATABASE):
        print("Criando banco de dados...")
        # Precisamos criar o arquivo schema.sql
        with open('schema.sql', 'w') as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS Participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ordem_rotacao INTEGER NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS Configuracao (
                id INTEGER PRIMARY KEY,
                data_inicio_ciclo TEXT NOT NULL
            );
            """)
        init_db()
        
    app.run(debug=True)