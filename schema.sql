
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
            