
            CREATE TABLE IF NOT EXISTS Participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ordem_rotacao INTEGER NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS Configuracao (
                id INTEGER PRIMARY KEY,
                data_inicio_ciclo TEXT NOT NULL
            );
            