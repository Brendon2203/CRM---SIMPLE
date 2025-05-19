from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify, flash
import pandas as pd
from datetime import datetime
import os
import re
import bcrypt
from config import USERNAME, PASSWORD
import locale

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Caminhos dos arquivos Excel
PLANILHA_PATH = 'clientes.xlsx'
USUARIOS_PATH = 'usuarios.xlsx'

# Configurar locale para português
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

def formatar_data(data_str):
    try:
        if pd.isna(data_str):
            return ''
            
        # Se já for datetime ou timestamp
        if isinstance(data_str, (datetime, pd.Timestamp)):
            data = data_str
        else:
            # Converter a string da data para objeto datetime
            try:
                data = datetime.strptime(str(data_str).strip(), '%d/%m/%Y')
            except:
                return "Data inválida"
        
        # Dicionário de dias da semana em português
        dias = {
            'Monday': 'Segunda',
            'Tuesday': 'Terça',
            'Wednesday': 'Quarta',
            'Thursday': 'Quinta',
            'Friday': 'Sexta',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        # Obter o nome do dia em inglês e converter para português
        dia_semana = dias[data.strftime('%A')]
        # Formatar a data no padrão brasileiro
        data_formatada = data.strftime('%d/%m/%Y')
        return f"{dia_semana} - {data_formatada}"
    except Exception as e:
        print(f"Erro ao formatar data: {e}")
        return "Data inválida"

def carregar_dados():
    df = pd.read_excel(PLANILHA_PATH)
    # Garantir que a coluna de data está no formato correto
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    return df

def salvar_dados(df):
    # Garantir que a data seja salva no formato DD/MM/YYYY
    if 'data' in df.columns:
        df['data'] = df['data'].dt.strftime('%d/%m/%Y')
    df.to_excel(PLANILHA_PATH, index=False)

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
        
        # Garante que a coluna 'Tipo aluno' existe
        if 'Tipo aluno' not in df.columns:
            df['Tipo aluno'] = ''
            df.to_excel(PLANILHA_PATH, index=False)
            
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

            # Validação do campo Lead (obrigatório)
            origem_lead = request.form['origem_lead'].strip()
            if not origem_lead or origem_lead not in ['Whatsapp', 'Instagram', 'Facebook', 'Google', 'Indicação']:
                return render_template('adicionar.html',
                    erro='Por favor, selecione uma origem válida para o lead.',
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
                "Ligação": request.form['ligacao'].strip(),
                "Lead": origem_lead,
                "Tipo aluno": request.form['tipo_aluno'].strip()
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
            
            # Validação do número de telefone (obrigatório)
            numero = dados['numero'].strip()
            if not numero or not re.match(r'^\(\d{2}\)[9]?\d{4}-\d{4}$', numero):
                return jsonify({'success': False, 'error': 'Número de telefone inválido.'})

            # Verifica se o número já existe em outro registro
            df = pd.read_excel(PLANILHA_PATH)
            numeros_existentes = df['Número'].astype(str).str.strip().tolist()
            if numero in numeros_existentes and numeros_existentes.index(numero) != index:
                return jsonify({'success': False, 'error': 'Este número já existe no banco de dados.'})

            # Processa a data de contato (obrigatório)
            data_contato = dados['data_contato'].strip()
            if data_contato.lower() == 'hoje':
                data_contato = datetime.today().strftime("%d/%m/%Y")
            else:
                try:
                    # Valida o formato da data
                    datetime.strptime(data_contato, "%d/%m/%Y")
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data de contato inválida. Use o formato DD/MM/AAAA ou a palavra "hoje".'})

            # Validação do campo Lead (obrigatório)
            origem_lead = dados['origem_lead'].strip()
            if not origem_lead or origem_lead not in ['Whatsapp', 'Instagram', 'Facebook', 'Google', 'Indicação']:
                return jsonify({'success': False, 'error': 'Por favor, selecione uma origem válida para o lead.'})

            # Validações opcionais
            responsavel = dados['responsavel'].strip().title()
            aluno = dados['aluno'].strip().title()
            
            # Valida nome do responsável se fornecido
            if responsavel and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', responsavel):
                return jsonify({'success': False, 'error': 'O nome do responsável deve conter apenas letras e ter no mínimo 3 caracteres.'})

            # Valida nome do aluno se fornecido
            if aluno and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', aluno):
                return jsonify({'success': False, 'error': 'O nome do aluno deve conter apenas letras e ter no mínimo 3 caracteres.'})

            # Valida idade se fornecida
            idade = None
            if dados['idade'].strip():
                try:
                    idade = int(dados['idade'])
                    if idade < 4 or idade > 99:
                        return jsonify({'success': False, 'error': 'Idade inválida. Deve ser um número entre 4 e 99.'})
                except ValueError:
                    return jsonify({'success': False, 'error': 'Idade inválida. Deve ser um número entre 4 e 99.'})

            # Valida data da AE se fornecida
            data_ae = dados['data_ae'].strip()
            if data_ae:
                try:
                    datetime.strptime(data_ae, "%d/%m/%Y")
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data da AE inválida. Use o formato DD/MM/AAAA.'})

            # Valida hora da AE se fornecida
            hora_ae = dados['hora_ae'].strip()
            if hora_ae and not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', hora_ae):
                return jsonify({'success': False, 'error': 'Hora da AE inválida. Use o formato HH:MM.'})
            
            # Atualiza os dados do lead
            df.loc[index, 'Nome do responsável'] = responsavel
            df.loc[index, 'Número'] = numero
            df.loc[index, 'Data de contato'] = data_contato
            df.loc[index, 'Nome do aluno'] = aluno
            df.loc[index, 'Idade do aluno'] = idade if idade is not None else ''
            df.loc[index, 'Curso'] = dados['curso'].strip()
            df.loc[index, 'Data AE'] = data_ae
            df.loc[index, 'Hora planejada AE'] = hora_ae
            df.loc[index, 'Chances de fechar'] = dados['chance'].strip()
            df.loc[index, 'Observação'] = dados['observacao'].strip()
            df.loc[index, 'Ligação'] = dados['ligacao'].strip()
            df.loc[index, 'Lead'] = origem_lead
            df.loc[index, 'Tipo aluno'] = dados['tipo_aluno'].strip()
            
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

@app.route('/mensagem_confirmacao', methods=['GET', 'POST'])
def mensagem_confirmacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    leads = carregar_leads()
    return render_template('mensagem_confirmacao.html', leads=leads)

@app.route('/analise_dados')
def analise_dados():
    try:
        # Lê o arquivo Excel
        df = pd.read_excel(PLANILHA_PATH)
        
        # Métricas principais
        total_leads = len(df)
        leads_convertidos = len(df[df['Tipo aluno'].isin(['cna', 'ctrlplay'])])
        alunos_cna = len(df[df['Tipo aluno'] == 'cna'])
        ligacoes_atendidas = len(df[df['Ligação'] == 'Atendeu'])
        
        # Cálculo das taxas
        taxa_conversao = round((leads_convertidos / total_leads * 100), 1) if total_leads > 0 else 0
        taxa_cna = round((alunos_cna / total_leads * 100), 1) if total_leads > 0 else 0
        taxa_atendimento = round((ligacoes_atendidas / total_leads * 100), 1) if total_leads > 0 else 0
        
        # Origem dos leads
        origem_leads = df['Lead'].value_counts().to_dict()
        
        # Status das ligações
        status_ligacoes = df['Ligação'].value_counts().to_dict()
        
        # Distribuição por curso
        distribuicao_cursos = df['Curso'].value_counts().to_dict()
        
        # Taxa de conversão por origem
        conversao_por_origem = {}
        for origem in origem_leads.keys():
            leads_origem = df[df['Lead'] == origem]
            convertidos_origem = len(leads_origem[leads_origem['Tipo aluno'].isin(['cna', 'ctrlplay'])])
            taxa = round((convertidos_origem / len(leads_origem) * 100), 1) if len(leads_origem) > 0 else 0
            conversao_por_origem[origem] = taxa
        
        return render_template('analise_dados.html',
                             total_leads=total_leads,
                             leads_convertidos=leads_convertidos,
                             alunos_cna=alunos_cna,
                             taxa_conversao=taxa_conversao,
                             taxa_cna=taxa_cna,
                             taxa_atendimento=taxa_atendimento,
                             origem_leads=origem_leads,
                             status_ligacoes=status_ligacoes,
                             distribuicao_cursos=distribuicao_cursos,
                             conversao_por_origem=conversao_por_origem)
    except Exception as e:
        flash(f'Erro ao carregar dados: {str(e)}', 'error')
        return redirect(url_for('menu'))

if __name__ == '__main__':
    app.run(debug=True)