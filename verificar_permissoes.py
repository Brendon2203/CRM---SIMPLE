import os
import sys
import stat
import shutil
from datetime import datetime

def verificar_arquivo(arquivo):
    """Verifica se o arquivo existe e suas permissões"""
    if not os.path.exists(arquivo):
        print(f"Arquivo {arquivo} não encontrado!")
        return False
        
    # Verifica permissões
    permissao = os.access(arquivo, os.W_OK)
    print(f"Permissão de escrita: {'Sim' if permissao else 'Não'}")
    
    # Mostra informações do arquivo
    stats = os.stat(arquivo)
    print(f"\nInformações do arquivo:")
    print(f"Tamanho: {stats.st_size} bytes")
    print(f"Última modificação: {datetime.fromtimestamp(stats.st_mtime)}")
    print(f"Permissões: {oct(stats.st_mode)[-3:]}")
    
    return permissao

def corrigir_permissoes(arquivo):
    """Tenta corrigir as permissões do arquivo"""
    try:
        # Tenta dar permissão total ao arquivo
        os.chmod(arquivo, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        print("\nPermissões corrigidas!")
        return True
    except Exception as e:
        print(f"\nErro ao corrigir permissões: {str(e)}")
        return False

def criar_backup(arquivo):
    """Cria um backup do arquivo"""
    try:
        # Cria diretório de backup se não existir
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nome do arquivo de backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f'backup_{os.path.basename(arquivo)}_{timestamp}')
        
        # Copia o arquivo
        shutil.copy2(arquivo, backup_file)
        print(f"\nBackup criado em: {backup_file}")
        return True
    except Exception as e:
        print(f"\nErro ao criar backup: {str(e)}")
        return False

def main():
    arquivo = 'clientes.xlsx'
    
    print("=== Verificação de Permissões do Arquivo ===")
    
    # Verifica o arquivo
    if not verificar_arquivo(arquivo):
        print("\nArquivo não encontrado ou sem permissões!")
        return
    
    # Pergunta se deseja corrigir as permissões
    resposta = input("\nDeseja corrigir as permissões do arquivo? (s/n): ").lower()
    if resposta == 's':
        if corrigir_permissoes(arquivo):
            print("Permissões corrigidas com sucesso!")
        else:
            print("Não foi possível corrigir as permissões.")
    
    # Pergunta se deseja criar um backup
    resposta = input("\nDeseja criar um backup do arquivo? (s/n): ").lower()
    if resposta == 's':
        if criar_backup(arquivo):
            print("Backup criado com sucesso!")
        else:
            print("Não foi possível criar o backup.")

if __name__ == "__main__":
    main() 