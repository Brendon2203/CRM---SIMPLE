from database import Database
import pandas as pd
from datetime import datetime

def migrar_dados():
    print("=== Migração de Dados do Excel para SQLite ===")
    
    # Inicializa o banco de dados
    db = Database()
    
    try:
        # Lê o arquivo Excel
        print("\nLendo arquivo Excel...")
        df = pd.read_excel('clientes.xlsx')
        
        # Renomeia as colunas para o formato do banco
        df = df.rename(columns={
            'Nome do responsável': 'nome_responsavel',
            'Número': 'numero',
            'Data de contato': 'data_contato',
            'Nome do aluno': 'nome_aluno',
            'Idade do aluno': 'idade_aluno',
            'Curso': 'curso',
            'Data AE': 'data_ae',
            'Hora planejada AE': 'hora_ae',
            'Observação': 'observacao',
            'Chances de fechar': 'chances_fechar',
            'Ligação': 'ligacao',
            'Lead': 'origem_lead',
            'Tipo aluno': 'tipo_aluno'
        })
        
        # Adiciona timestamps
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df['data_criacao'] = agora
        df['data_atualizacao'] = agora
        
        # Importa para o SQLite
        print("\nImportando dados para o SQLite...")
        if db.importar_excel('clientes.xlsx'):
            print("\nMigração concluída com sucesso!")
            print("Os dados foram salvos no arquivo crm.db")
            print("\nVocê pode continuar usando o sistema normalmente.")
            print("O arquivo Excel original foi mantido como backup.")
        else:
            print("\nErro ao importar dados para o SQLite.")
            
    except Exception as e:
        print(f"\nErro durante a migração: {str(e)}")

if __name__ == "__main__":
    migrar_dados() 