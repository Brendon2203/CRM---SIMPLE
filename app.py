from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import pandas as pd
from datetime import datetime
import os
import re
import bcrypt

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Caminhos dos arquivos Excel
PLANILHA_PATH = 'clientes.xlsx'
USUARIOS_PATH = 'usuarios.xlsx'

def inicializar_usuarios():
    """Função para criar o arquivo de usuários se não existir"""
    if not os.path.exists(USUARIOS_PATH):
        df = pd.DataFrame(columns=['usuario', 'senha', 'funcao'])
        # Cria o usuário admin padrão
        senha = bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt())
        df.loc[0] = ['admin', senha.decode('utf-8'), 'admin']
        df.to_excel(USUARIOS_PATH, index=False)

def verificar_senha(senha_digitada, senha_hash):
    """Verifica se a senha está correta"""
    return bcrypt.checkpw(senha_digitada.encode('utf-8'), senha_hash.encode('utf-8'))

def usuario_atual():
    """Retorna os dados do usuário atual"""
    if 'usuario' in session:
        df = pd.read_excel(USUARIOS_PATH)
        usuario = df[df['usuario'] == session['usuario']].iloc[0]
        return {
            'usuario': usuario['usuario'],
            'funcao': usuario['funcao']
        }
    return None

def requer_admin(f):
    """Decorator para rotas que requerem privilégios de admin"""
    def decorated_function(*args, **kwargs):
        user = usuario_atual()
        if not user or user['funcao'] != 'admin':
            return redirect(url_for('menu'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def carregar_leads():
    """Função auxiliar para carregar os leads do arquivo Excel"""
    try:
        if not os.path.exists(PLANILHA_PATH):
            print(f"Arquivo {PLANILHA_PATH} não encontrado!")
            return []
        df = pd.read_excel(PLANILHA_PATH)
        leads = df.to_dict('records')
        print(f"Carregados {len(leads)} leads com sucesso!")
        return leads
    except Exception as e:
        print(f"Erro ao carregar leads: {str(e)}")
        return []

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verifica se o arquivo de usuários existe
        inicializar_usuarios()
        
        # Carrega os usuários
        df = pd.read_excel(USUARIOS_PATH)
        
        # Procura o usuário
        user = df[df['usuario'] == username]
        if not user.empty and verificar_senha(password, user.iloc[0]['senha']):
            session['usuario'] = username
            return redirect(url_for('menu'))
        else:
            return render_template('login.html', erro='Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/usuarios', methods=['GET', 'POST'])
@requer_admin
def usuarios():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            funcao = request.form['funcao']
            
            df = pd.read_excel(USUARIOS_PATH)
            
            # Verifica se o usuário já existe
            if username in df['usuario'].values:
                return render_template('usuarios.html', 
                    erro='Este usuário já existe.',
                    usuarios=df.to_dict('records'))
            
            # Criptografa a senha
            senha_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Adiciona o novo usuário
            novo_usuario = pd.DataFrame([{
                'usuario': username,
                'senha': senha_hash.decode('utf-8'),
                'funcao': funcao
            }])
            
            df = pd.concat([df, novo_usuario], ignore_index=True)
            df.to_excel(USUARIOS_PATH, index=False)
            
            return render_template('usuarios.html', 
                sucesso='Usuário criado com sucesso!',
                usuarios=df.to_dict('records'))
            
        except Exception as e:
            return render_template('usuarios.html', 
                erro=f'Erro ao criar usuário: {str(e)}',
                usuarios=df.to_dict('records'))
    
    df = pd.read_excel(USUARIOS_PATH)
    return render_template('usuarios.html', usuarios=df.to_dict('records'))

@app.route('/excluir_usuario/<username>')
@requer_admin
def excluir_usuario(username):
    try:
        df = pd.read_excel(USUARIOS_PATH)
        
        # Não permite excluir o próprio usuário
        if username == session['usuario']:
            return jsonify({'success': False, 'error': 'Você não pode excluir seu próprio usuário.'})
        
        # Remove o usuário
        df = df[df['usuario'] != username]
        df.to_excel(USUARIOS_PATH, index=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/menu')
def menu():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html', user=usuario_atual())

@app.route('/baixar')
def baixar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return send_file(PLANILHA_PATH, as_attachment=True)

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Validação do número de telefone (obrigatório)
            numero = request.form['numero'].strip()
            if not numero or not re.match(r'^\(\d{2}\)[9]?\d{4}-\d{4}$', numero):
                return render_template('adicionar.html', 
                    erro='Número de telefone inválido.',
                    dados=request.form)

            # Verifica se o número já existe
            df = pd.read_excel(PLANILHA_PATH)
            numeros_existentes = df['Número'].astype(str).str.strip().tolist()
            if numero in numeros_existentes:
                return render_template('adicionar.html', 
                    erro='Este número já existe no banco de dados.',
                    dados=request.form)

            # Processa a data de contato (obrigatório)
            data_contato = request.form['data_contato'].strip()
            if data_contato.lower() == 'hoje':
                data_contato = datetime.today().strftime("%d/%m/%Y")
            else:
                try:
                    # Valida o formato da data
                    datetime.strptime(data_contato, "%d/%m/%Y")
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Data de contato inválida. Use o formato DD/MM/AAAA ou a palavra "hoje".',
                        dados=request.form)

            # Validações opcionais
            responsavel = request.form['responsavel'].strip().title() if request.form['responsavel'].strip() else ''
            aluno = request.form['aluno'].strip().title() if request.form['aluno'].strip() else ''
            
            # Valida nome do responsável se fornecido
            if responsavel and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', responsavel):
                return render_template('adicionar.html', 
                    erro='O nome do responsável deve conter apenas letras e ter no mínimo 3 caracteres.',
                    dados=request.form)

            # Valida nome do aluno se fornecido
            if aluno and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', aluno):
                return render_template('adicionar.html', 
                    erro='O nome do aluno deve conter apenas letras e ter no mínimo 3 caracteres.',
                    dados=request.form)

            # Valida idade se fornecida
            idade = None
            if request.form['idade'].strip():
                try:
                    idade = int(request.form['idade'])
                    if idade < 4 or idade > 99:
                        return render_template('adicionar.html', 
                            erro='Idade inválida. Deve ser um número entre 4 e 99.',
                            dados=request.form)
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Idade inválida. Deve ser um número entre 4 e 99.',
                        dados=request.form)

            # Valida data da AE se fornecida
            data_ae = request.form['data_ae'].strip()
            if data_ae:
                try:
                    datetime.strptime(data_ae, "%d/%m/%Y")
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Data da AE inválida. Use o formato DD/MM/AAAA.',
                        dados=request.form)

            # Valida hora da AE se fornecida
            hora_ae = request.form['hora_ae'].strip()
            if hora_ae and not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', hora_ae):
                return render_template('adicionar.html', 
                    erro='Hora da AE inválida. Use o formato HH:MM.',
                    dados=request.form)

            # Prepara os dados para salvar
            dados = {
                "Nome do responsável": responsavel,
                "Número": numero,
                "Data de contato": data_contato,
                "Nome do aluno": aluno,
                "Idade do aluno": idade if idade is not None else '',
                "Curso": request.form['curso'].strip(),
                "Data AE": data_ae,
                "Hora planejada AE": hora_ae,
                "Observação": request.form['observacao'].strip(),
                "Chances de fechar": request.form['chance'].strip(),
                "Ligação": request.form['ligacao'].strip()
            }
            
            df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
            df.to_excel(PLANILHA_PATH, index=False)
            return render_template('adicionar.html', sucesso=True)
            
        except Exception as e:
            return render_template('adicionar.html', 
                erro=f'Erro ao salvar os dados: {str(e)}',
                dados=request.form)
            
    return render_template('adicionar.html')

@app.route('/alterar_dados', methods=['GET', 'POST'])
@requer_admin
def alterar_dados():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            dados = request.get_json()
            index = int(dados['index'])
            df = pd.read_excel(PLANILHA_PATH)
            
            # Atualiza os dados do lead
            df.loc[index, 'Nome do responsável'] = dados['responsavel'].strip().title()
            df.loc[index, 'Número'] = dados['numero'].strip()
            df.loc[index, 'Nome do aluno'] = dados['aluno'].strip().title()
            df.loc[index, 'Idade do aluno'] = int(dados['idade']) if dados['idade'].strip() else ''
            df.loc[index, 'Curso'] = dados['curso'].strip()
            df.loc[index, 'Data AE'] = dados['data_ae'].strip()
            df.loc[index, 'Hora planejada AE'] = dados['hora_ae'].strip()
            df.loc[index, 'Chances de fechar'] = dados['chance'].strip()
            df.loc[index, 'Observação'] = dados['observacao'].strip()
            
            # Salva as alterações
            df.to_excel(PLANILHA_PATH, index=False)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # Lê os dados atuais para exibir na página
    leads = carregar_leads()
    return render_template('alterar_dados.html', leads=leads)

@app.route('/excluir_lead', methods=['POST'])
@requer_admin
def excluir_lead():
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'})
    
    try:
        dados = request.get_json()
        index = int(dados['index'])
        df = pd.read_excel(PLANILHA_PATH)
        
        # Remove o lead pelo índice
        df = df.drop(index)
        
        # Reseta os índices
        df = df.reset_index(drop=True)
        
        # Salva as alterações
        df.to_excel(PLANILHA_PATH, index=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mensagem_agendamento', methods=['GET', 'POST'])
def mensagem_agendamento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    leads = carregar_leads()
    print(f"Enviando {len(leads)} leads para o template")
    return render_template('mensagem_agendamento.html', leads=leads)

@app.route('/mensagem_confirmacao')
def mensagem_confirmacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    leads = carregar_leads()
    return render_template('mensagem_confirmacao.html', leads=leads)

if __name__ == '__main__':
    app.run(debug=True)