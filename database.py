import sqlite3
import pandas as pd
from datetime import datetime
import os
import shutil

class Database:
    def __init__(self):
        self.db_path = 'crm.db'
        self.backup_dir = 'backups'
        self.initialize_database()

    def initialize_database(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Cria a tabela de leads
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_responsavel TEXT,
            numero TEXT UNIQUE,
            data_contato TEXT,
            nome_aluno TEXT,
            idade_aluno INTEGER,
            curso TEXT,
            data_ae TEXT,
            hora_ae TEXT,
            observacao TEXT,
            chances_fechar TEXT,
            ligacao TEXT,
            origem_lead TEXT,
            tipo_aluno TEXT,
            data_criacao TEXT,
            data_atualizacao TEXT
        )
        ''')

        # Cria a tabela de usuários
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT,
            funcao TEXT
        )
        ''')

        conn.commit()
        conn.close()

    def criar_backup(self):
        """Cria um backup do banco de dados"""
        try:
            # Cria diretório de backup se não existir
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Nome do arquivo de backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f'crm_backup_{timestamp}.db')
            
            # Copia o arquivo
            shutil.copy2(self.db_path, backup_file)
            return True
        except Exception as e:
            print(f"Erro ao criar backup: {str(e)}")
            return False

    def importar_excel(self, excel_path):
        """Importa dados do Excel para o SQLite"""
        try:
            # Cria backup antes de importar
            self.criar_backup()
            
            # Lê o Excel
            df = pd.read_excel(excel_path)
            
            # Conecta ao banco
            conn = sqlite3.connect(self.db_path)
            
            # Importa os dados
            df.to_sql('leads', conn, if_exists='replace', index=False)
            
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao importar Excel: {str(e)}")
            return False

    def exportar_excel(self, excel_path):
        """Exporta dados do SQLite para Excel"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM leads", conn)
            df.to_excel(excel_path, index=False)
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao exportar para Excel: {str(e)}")
            return False

    def adicionar_lead(self, dados):
        """Adiciona um novo lead"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Adiciona timestamps
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
            INSERT INTO leads (
                nome_responsavel, numero, data_contato, nome_aluno,
                idade_aluno, curso, data_ae, hora_ae, observacao,
                chances_fechar, ligacao, origem_lead, tipo_aluno,
                data_criacao, data_atualizacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['nome_responsavel'],
                dados['numero'],
                dados['data_contato'],
                dados['nome_aluno'],
                dados['idade_aluno'],
                dados['curso'],
                dados['data_ae'],
                dados['hora_ae'],
                dados['observacao'],
                dados['chances_fechar'],
                dados['ligacao'],
                dados['origem_lead'],
                dados['tipo_aluno'],
                agora,
                agora
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao adicionar lead: {str(e)}")
            return False

    def atualizar_lead(self, id, dados):
        """Atualiza um lead existente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Atualiza timestamp
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
            UPDATE leads SET
                nome_responsavel = ?,
                numero = ?,
                data_contato = ?,
                nome_aluno = ?,
                idade_aluno = ?,
                curso = ?,
                data_ae = ?,
                hora_ae = ?,
                observacao = ?,
                chances_fechar = ?,
                ligacao = ?,
                origem_lead = ?,
                tipo_aluno = ?,
                data_atualizacao = ?
            WHERE id = ?
            ''', (
                dados['nome_responsavel'],
                dados['numero'],
                dados['data_contato'],
                dados['nome_aluno'],
                dados['idade_aluno'],
                dados['curso'],
                dados['data_ae'],
                dados['hora_ae'],
                dados['observacao'],
                dados['chances_fechar'],
                dados['ligacao'],
                dados['origem_lead'],
                dados['tipo_aluno'],
                agora,
                id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao atualizar lead: {str(e)}")
            return False

    def excluir_lead(self, id):
        """Exclui um lead"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM leads WHERE id = ?', (id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao excluir lead: {str(e)}")
            return False

    def listar_leads(self):
        """Lista todos os leads"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM leads')
            leads = cursor.fetchall()
            
            # Converte para lista de dicionários
            colunas = [description[0] for description in cursor.description]
            leads_dict = []
            for lead in leads:
                lead_dict = dict(zip(colunas, lead))
                leads_dict.append(lead_dict)
            
            conn.close()
            return leads_dict
        except Exception as e:
            print(f"Erro ao listar leads: {str(e)}")
            return []

    def buscar_lead(self, id):
        """Busca um lead específico"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM leads WHERE id = ?', (id,))
            lead = cursor.fetchone()
            
            conn.close()
            return lead
        except Exception as e:
            print(f"Erro ao buscar lead: {str(e)}")
            return None

    def verificar_numero_existe(self, numero):
        """Verifica se um número já existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM leads WHERE numero = ?', (numero,))
            resultado = cursor.fetchone()
            
            conn.close()
            return resultado is not None
        except Exception as e:
            print(f"Erro ao verificar número: {str(e)}")
            return False 