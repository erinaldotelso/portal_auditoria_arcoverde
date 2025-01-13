from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Importando Flask-Migrate
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from PyPDF2 import PdfWriter, PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import logging
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Altere para uma chave secreta mais robusta

# Configuração do banco de dados SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'auditorias.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)  # Instância do SQLAlchemy
migrate = Migrate(app, db)  # Instância do Migrate

# Definir o diretório base do projeto
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuração dos diretórios
PLANO_AUDITORIA_DIR = os.path.join(basedir, 'uploads', 'plano de auditoria')
PEDIDO_INFORMACAO = os.path.join(basedir, 'uploads', 'pedido de informação')
UPLOADS_DIR = os.path.join(basedir, 'uploads', 'relatorios')
AUDITADOS_RECEBIDOS_DIR = os.path.join(basedir, 'uploads', 'auditados', 'recebidos')
AUDITADOS_ENVIADOS_DIR = os.path.join(basedir, 'uploads', 'auditados', 'enviados')  # Novo diretório para arquivos enviados

# Criação das pastas, se não existirem
os.makedirs(PLANO_AUDITORIA_DIR, exist_ok=True)
os.makedirs(PEDIDO_INFORMACAO, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(AUDITADOS_RECEBIDOS_DIR, exist_ok=True)
os.makedirs(AUDITADOS_ENVIADOS_DIR, exist_ok=True)  # Criar a pasta de enviados se não existir

# Adiciona as configurações ao app.config
app.config['PLANO_AUDITORIA_DIR'] = PLANO_AUDITORIA_DIR
app.config['PEDIDO_INFORMACAO'] = PEDIDO_INFORMACAO
app.config['UPLOADS_DIR'] = UPLOADS_DIR
app.config['AUDITADOS_RECEBIDOS_DIR'] = AUDITADOS_RECEBIDOS_DIR
app.config['AUDITADOS_ENVIADOS_DIR'] = AUDITADOS_ENVIADOS_DIR  # Configuração para enviados


# Modelo da tabela Relatórios
class Relatorio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    departamento = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    arquivo_pdf = db.Column(db.String(200))
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    data_atualizacao = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'departamento': self.departamento,
            'tipo': self.tipo,
            'data_inicio': self.data_inicio.strftime('%d/%m/%Y') if self.data_inicio else '',
            'data_fim': self.data_fim.strftime('%d/%m/%Y') if self.data_fim else '',
            'arquivo_pdf': self.arquivo_pdf,
            'data_criacao': self.data_criacao.strftime('%d/%m/%Y %H:%M:%S') if self.data_criacao else '',
            'data_atualizacao': self.data_atualizacao.strftime('%d/%m/%Y %H:%M:%S') if self.data_atualizacao else ''
        }


# Modelo da tabela Matriz de Planejamento
class MatrizPlanejamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercicio = db.Column(db.String(4), nullable=False)  # Campo para o Exercício (limite de 4 caracteres, ex: "2024")
    responsavel = db.Column(db.String(100), nullable=False)  # Campo para o Responsável Técnico
    auditorias = db.relationship('AuditoriaPlanejamento', backref='matriz', lazy='select')  # Relação com AuditoriaPlanejamento

# Modelo da tabela Auditoria Planejamento
class AuditoriaPlanejamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100), nullable=False)
    objetivo = db.Column(db.String(200), nullable=False)
    metodologia = db.Column(db.String(200), nullable=False)
    periodo = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    matriz_planejamento_id = db.Column(db.Integer, db.ForeignKey('matriz_planejamento.id'), nullable=False)  # Chave estrangeira

# Modelo da tabela Plano de Auditoria
class PlanoAuditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_auditoria = db.Column(db.String(100), nullable=False)  # Campo para armazenar o número da auditoria
    area = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    data = db.Column(db.Date, nullable=False)
    arquivo = db.Column(db.String(200))
      
# Modelo da tabela Auditoria
class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_auditoria = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    departamento = db.Column(db.String(100), nullable=False)
    data = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # Adicionando a coluna 'status'
    
# Modelo da tabela Comunicação
class Comunicacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    data_atualizacao = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'data': self.data.strftime('%Y-%m-%d') if isinstance(self.data, (datetime, date)) else '',
            'mensagem': self.mensagem,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d') if isinstance(self.data_criacao, datetime) else '',
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d') if isinstance(self.data_atualizacao, datetime) else ''
        }

# Modelo da tabela Pedido de Informação
class PedidoInformacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orgao = db.Column(db.String(100), nullable=False)
    processo = db.Column(db.String(100), nullable=False)
    data_envio = db.Column(db.Date, nullable=False)
    prazo = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    data_resposta = db.Column(db.Date)
    arquivo = db.Column(db.String(200), nullable=True)  # Novo campo para armazenar o nome do arquivo

    def __repr__(self):
        return f'<PedidoInformacao {self.id}>'

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    secretaria = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False, unique=True)
    senha = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.username}>'

# Modelo para armazenar documentos
class Documento(db.Model):
    __tablename__ = 'documentos'
    id = db.Column(db.Integer, primary_key=True)
    secretaria = db.Column(db.String(100))
    cargo = db.Column(db.String(100))  # Esta coluna deve estar aqui
    usuario = db.Column(db.String(100))
    tipo_documento = db.Column(db.String(50))
    arquivo = db.Column(db.String(200))
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)

class Resposta(db.Model):
    __tablename__ = 'respostas'

    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id', ondelete='CASCADE'), nullable=False)
    texto_resposta = db.Column(db.Text, nullable=True)
    arquivo_resposta = db.Column(db.String(120), nullable=True)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    secretaria = db.Column(db.String(100))  # Nova coluna para armazenar a secretaria associada

    # Relacionamento com o modelo Documento
    documento = db.relationship('Documento', backref=db.backref('respostas', lazy=True, cascade="all, delete"))
    
#----------------------------------------------------------------------------------------------------------------#
#                                                    login                                                       #
#----------------------------------------------------------------------------------------------------------------#

# Credenciais de login
users = {
    'auditoria@arcoverde.pe.gov.br': {'password': '#aud2025#', 'role': 'auditor'},
    'controladoria@arcoverde.pe.gov.br': {'password': 'cgm2025', 'role': 'controlador'}
}

# Página de login
@app.route('/', methods=['GET'])
def inicio():
    return render_template('inicio.html')

@app.route('/login_auditor', methods=['GET', 'POST'])
def login_auditor():
    if 'logged_in' in session:
        return redirect(url_for('home'))  # Redireciona se já estiver logado

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users.get(email)

        if user and user['password'] == password and user['role'] == 'auditor':
            session['logged_in'] = True
            session['user_role'] = user['role']
            session['email'] = email  # Armazenando o e-mail na sessão

            return redirect(url_for('home'))  # Redireciona para a página do auditor
        else:
            flash('E-mail ou senha inválidos!', 'danger')

    return render_template('login_auditor.html')
    

@app.route('/login_controlador', methods=['GET', 'POST'])
def login_controlador():
    if 'logged_in' in session:
        return redirect(url_for('cgm_home'))  # Redireciona se já estiver logado

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users.get(email)

        if user and user['password'] == password and user['role'] == 'controlador':
            session['logged_in'] = True
            session['user_role'] = user['role']
            session['email'] = email  # Armazenando o e-mail na sessão
            return redirect(url_for('cgm_home'))  # Redireciona para a página do controlador
        else:
            flash('E-mail ou senha inválidos!', 'danger')

    return render_template('login_controlador.html')


# Página inicial (home) do auditor
@app.route('/home')
def home():
    if 'logged_in' not in session or session.get('user_role') != 'auditor':
        return redirect(url_for('login_auditor'))
    return render_template('home.html')

# Página inicial (home) do controlador
@app.route('/cgm_home')
def cgm_home():
    if 'logged_in' not in session or session.get('user_role') != 'controlador':
        return redirect(url_for('login_controlador'))
    return render_template('cgm/home.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()  # Limpa todas as informações da sessão
    return redirect(url_for('login_controlador'))  # Redireciona para a página de login do controlador

#----------------------------------------------------------------------------------------------------------------#
#                                                Páginas base.hhtml                                              #
#----------------------------------------------------------------------------------------------------------------#

# Página de auditoria
@app.route('/auditoria', methods=['GET'])
def auditoria():
    # Verificação de login
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # Obtenção de todas as auditorias
    auditorias = Auditoria.query.all()

    # Extração de todas as secretarias (departamento) e anos únicos
    secretarias = list(set(auditoria.departamento for auditoria in auditorias))
    anos = list(set(auditoria.data.year for auditoria in auditorias))
    anos.sort(reverse=True)

    # Renderização do template com todas as auditorias, secretarias e anos
    return render_template('Auditoria.html', auditorias=auditorias, secretarias=secretarias, anos=anos)


@app.route('/cadastrar_auditoria', methods=['POST'])
def cadastrar_auditoria():
    if request.method == 'POST':
        numero_auditoria = request.form['numero_auditoria']
        area = request.form['area']
        departamento = request.form['departamento']
        data_str = request.form['data']
        status = request.form['status']

        # Validação e conversão da data
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()  # Ajuste o formato para o padrão de entrada do HTML
        except ValueError:
            flash('Formato de data inválido. Use o formato dd/mm/aaaa.', 'danger')
            return redirect(url_for('auditoria'))

        # Criação de uma nova auditoria
        nova_auditoria = Auditoria(numero_auditoria=numero_auditoria, area=area, departamento=departamento, data=data, status=status)
        db.session.add(nova_auditoria)
        db.session.commit()

        flash('Auditoria cadastrada com sucesso!', 'success')

    return redirect(url_for('auditoria'))


# Rota para editar auditoria
@app.route('/editar_auditoria/<int:id>', methods=['GET', 'POST'])
def editar_auditoria(id):
    auditoria = Auditoria.query.get_or_404(id)

    if request.method == 'POST':
        auditoria.numero_auditoria = request.form['numero_auditoria']
        auditoria.area = request.form['area']
        auditoria.departamento = request.form['departamento']
        auditoria.data = datetime.strptime(request.form['data'], '%d/%m/%Y').date()
        auditoria.status = request.form['status']  # Captura o novo status

        db.session.commit()
        flash('Auditoria editada com sucesso!', 'success')
        return redirect(url_for('auditoria'))

    return render_template('editar_auditoria.html', auditoria=auditoria)

@app.route('/excluir_auditoria/<int:id>', methods=['POST'])
def excluir_auditoria(id):
    auditoria = Auditoria.query.get_or_404(id)
    db.session.delete(auditoria)
    db.session.commit()
    flash('Auditoria excluída com sucesso!', 'success')
    return redirect(url_for('auditoria'))

# Página de meus relatórios
@app.route('/meus-relatorios', methods=['GET', 'POST'])
def meus_relatorios():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        relatorio_id = request.form.get('id')
        if relatorio_id:
            try:
                relatorio_id = int(relatorio_id)
                relatorio = Relatorio.query.get(relatorio_id)
                if relatorio:
                    db.session.delete(relatorio)
                    db.session.commit()
            except ValueError as e:
                print(f"Error ao excluir relatório: {e}")
        return redirect(url_for('meus_relatorios'))

    tipo_filtrado = request.args.get('tipo', None)
    ano_filtrado = request.args.get('ano', None)

    query = Relatorio.query

    if tipo_filtrado:
        query = query.filter(Relatorio.tipo == tipo_filtrado)

    if ano_filtrado:
        query = query.filter(db.extract('year', Relatorio.data_fim) == int(ano_filtrado))

    relatorios = query.all()

    # Extraindo anos únicos dos relatórios
    anos = {relatorio.data_fim.year for relatorio in relatorios if relatorio.data_fim}

    tipos_unicos = {relatorio.tipo for relatorio in Relatorio.query.all()}
    relatorios_dict = [relatorio.to_dict() for relatorio in relatorios]

    return render_template('meus_relatorios.html', relatorios=relatorios_dict, tipos=tipos_unicos, anos=sorted(anos))


# Outras rotas (visualizar, editar) devem ser mantidas conforme o seu código atual.



# Página para visualizar relatórios PDF
@app.route('/visualizar-relatorio/<filename>')
def visualizar_relatorio(filename):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.isfile(file_path):
        return "Arquivo não encontrado", 404
    
    return render_template('visualizar_relatorio.html', filename=filename)

# Rota para servir o arquivo PDF
@app.route('/uploads/relatorios/<filename>')
def serve_file(filename):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    return send_from_directory(UPLOADS_DIR, filename)

# Página para editar relatórios
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_relatorio(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    relatorio = Relatorio.query.get_or_404(id)

    if request.method == 'POST':
        relatorio.titulo = request.form.get('titulo')
        relatorio.departamento = request.form.get('departamento')
        relatorio.tipo = request.form.get('tipo')
        try:
            relatorio.data_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
            relatorio.data_fim = datetime.strptime(request.form.get('data_fim'), '%Y-%m-%d').date()
        except ValueError:
            print("Data inválida fornecida")

        if 'relatorio' in request.files:
            file = request.files['relatorio']
            if file and file.filename:
                filename = secure_filename(file.filename)
                caminho_arquivo = os.path.join(UPLOADS_DIR, filename)
                file.save(caminho_arquivo)
                relatorio.arquivo_pdf = filename

        db.session.commit()
        return redirect(url_for('meus_relatorios'))

    return render_template('editar_meus_relatorios.html', relatorio=relatorio)

# Página para criar novos relatórios
# Cria o diretório se não existir
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Página para criar novos relatórios
UPLOADS_DIR = 'C:/Users/erina/Downloads/auditoria_interna/uploads/relatorios'

# Cria o diretório se não existir
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

@app.route('/novo-relatorio', methods=['GET', 'POST'])
def novo_relatorio():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        departamento = request.form.get('departamento')
        tipo = request.form.get('tipo')
        try:
            data_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
            data_fim = datetime.strptime(request.form.get('data_fim'), '%Y-%m-%d').date()
        except ValueError:
            return 'Data inválida fornecida', 400

        arquivo = request.files.get('arquivo_pdf')
        filename = None
        if arquivo and arquivo.filename:
            if arquivo.content_type != 'application/pdf':
                return 'O arquivo deve ser um PDF', 400
            
            filename = secure_filename(arquivo.filename)
            caminho_arquivo = os.path.join(UPLOADS_DIR, filename)
            arquivo.save(caminho_arquivo)

        novo_relatorio = Relatorio(
            titulo=titulo,
            departamento=departamento,
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            arquivo_pdf=filename,
        )

        try:
            db.session.add(novo_relatorio)
            db.session.commit()
            return redirect(url_for('meus_relatorios'))
        except Exception as e:
            db.session.rollback()
            return str(e), 500

    return render_template('novo_relatorio.html')


@app.route('/enviar/<int:id>', methods=['GET'])
def enviar_relatorio(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    relatorio = Relatorio.query.get_or_404(id)
    # Adicione a lógica para enviar o relatório aqui

    return redirect(url_for('meus_relatorios'))

#----------------------------------------------------------------------------------------------------------------#
#                                     Rota para visualizar a Matriz de Risco                                     #
#----------------------------------------------------------------------------------------------------------------#

# Rota para visualizar a Matriz de Risco
@app.route('/matriz_risco')
def visualizar_matriz_risco():
    directory = os.path.join(app.root_path, 'uploads', 'matriz_risco')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('visualizar_matriz_risco.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('visualizar_matriz_risco.html', filename=latest_file)

# Rota para servir os arquivos PDF da Matriz de Risco
@app.route('/uploads/matriz_risco/<path:filename>')
def serve_matriz_risco_pdf(filename):
    directory = os.path.join(app.root_path, 'uploads', 'matriz_risco')
    return send_from_directory(directory, filename)

# Rota para upload de arquivos da Matriz de Risco
@app.route('/upload_matriz_risco', methods=['POST'])
def upload_matriz_risco():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_matriz_risco'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_matriz_risco'))

    # Salvar o arquivo
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_matriz_risco'))

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads', 'matriz_risco')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#----------------------------------------------------------------------------------------------------------------#
#                         Rota para visualizar as Leis do PCCS E Estrutrua da CGM                                #
#----------------------------------------------------------------------------------------------------------------#

@app.route('/leis_018_2020')
def visualizar_leis_018_2020():
    directory = os.path.join(app.root_path, 'uploads', 'Leis')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('visualizar_leis_018_2020.html', filename=None)

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('visualizar_leis_018_2020.html', filename=latest_file)

# Rota para servir os arquivos PDF das Leis 018/2020
@app.route('/uploads/leis_018_2020/<path:filename>')
def serve_leis_018_2020_pdf(filename):
    directory = os.path.join(app.root_path, 'uploads', 'Leis')
    return send_from_directory(directory, filename)

# Rota para upload de arquivos da L C N.° 018/2020
@app.route('/upload_leis_018_2020', methods=['POST'])
def upload_leis_018_2020():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_leis_018_2020'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_leis_018_2020'))

    # Salvar o arquivo
    file.save(os.path.join(app.config['UPLOAD_FOLDER_LEIS'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_leis_018_2020'))  
    
@app.route('/leis_08_2023')
def visualizar_leis_08_2023():
    directory = os.path.join(app.root_path, 'uploads', 'Leis 2')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('visualizar_leis_08_2023.html', filename=None)

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('visualizar_leis_08_2023.html', filename=latest_file)
    
# Rota para servir os arquivos PDF das Leis 08/2023
@app.route('/uploads/leis_2/<path:filename>')
def serve_leis_pdf(filename):
    directory = os.path.join(app.root_path, 'uploads', 'Leis 2')
    return send_from_directory(directory, filename)

# Rota para upload de arquivos da L C N.° 08/2023
@app.route('/upload_leis_08_2023', methods=['POST'])
def upload_leis_08_2023():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_leis_08_2023'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_leis_08_2023'))

    # Salvar o arquivo na nova pasta
    file.save(os.path.join(app.config['UPLOAD_FOLDER_LEIS_2'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_leis_08_2023'))

# Configuração do diretório de uploads para as Leis 2
UPLOAD_FOLDER_LEIS_2 = os.path.join(app.root_path, 'uploads', 'Leis 2')
app.config['UPLOAD_FOLDER_LEIS_2'] = UPLOAD_FOLDER_LEIS_2


#----------------------------------------------------------------------------------------------------------------#
#                                          Rota para plano de auditoria                                          #
#----------------------------------------------------------------------------------------------------------------#

@app.route('/plano_de_auditoria')
def plano_de_auditoria():
    ano = request.args.get('ano')
    tipo = request.args.get('tipo')

    # Obter todos os planos
    query = PlanoAuditoria.query

    # Filtrar por ano
    if ano:
        query = query.filter(PlanoAuditoria.data.ilike(f'{ano}%'))

    # Filtrar por tipo
    if tipo:
        if tipo == 'O':
            query = query.filter(PlanoAuditoria.numero_auditoria.ilike('%- O'))
        elif tipo == 'E':
            query = query.filter(PlanoAuditoria.numero_auditoria.ilike('%- E'))

    planos = query.all()
    auditorias = Auditoria.query.all()

    # Obter lista de anos distintos da tabela PlanoAuditoria
    anos = {plano.data.year for plano in PlanoAuditoria.query.all()}
    
    return render_template('planoauditoria.html', planos=planos, auditorias=auditorias, anos=sorted(anos))

# Rota para adicionar um novo plano de auditoria
@app.route('/adicionar_plano', methods=['POST'])
def adicionar_plano():
    numero_auditoria = request.form['numero_auditoria']  # Captura o número da auditoria
    area = request.form['area']
    descricao = request.form['descricao']
    data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()

    arquivo = request.files.get('arquivo')
    arquivo_nome = None
    if arquivo and arquivo.filename:
        arquivo_nome = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(PLANO_AUDITORIA_DIR, arquivo_nome)
        arquivo.save(caminho_arquivo)

    novo_plano = PlanoAuditoria(
        numero_auditoria=numero_auditoria,  # Armazena o número da auditoria no plano
        area=area,
        descricao=descricao,
        data=data,
        arquivo=arquivo_nome
    )

    db.session.add(novo_plano)
    db.session.commit()

    return redirect(url_for('plano_de_auditoria'))


# Rota para deletar um plano de auditoria
@app.route('/deletar_plano/<int:id>', methods=['POST'])
def deletar_plano(id):
    plano = PlanoAuditoria.query.get_or_404(id)
    db.session.delete(plano)
    db.session.commit()
    flash('Plano de auditoria excluído com sucesso!', 'success')
    return redirect(url_for('plano_de_auditoria'))
    
# Rota para editar um plano de auditoria
@app.route('/editar_plano/<int:id>', methods=['GET', 'POST'])
def editar_plano(id):
    plano = PlanoAuditoria.query.get_or_404(id)

    if request.method == 'POST':
        plano.numero_auditoria = request.form['numero_auditoria']  # Capturando o número da auditoria
        plano.area = request.form['area']
        plano.descricao = request.form['descricao']
        plano.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()

        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            arquivo_nome = secure_filename(arquivo.filename)
            caminho_arquivo = os.path.join(PLANO_AUDITORIA_DIR, arquivo_nome)
            arquivo.save(caminho_arquivo)
            plano.arquivo = arquivo_nome

        db.session.commit()
        return redirect(url_for('plano_de_auditoria'))

    auditorias = Auditoria.query.all()  # Obtendo todas as auditorias para a lista suspensa
    return render_template('editarplano.html', plano=plano, auditorias=auditorias)


@app.route('/uploads/plano_de_auditoria/<filename>')
def serve_plano(filename):
    return send_from_directory(PLANO_AUDITORIA_DIR, filename)

# Rota para visualizar o arquivo do plano de auditoria
@app.route('/visualizar_plano/<int:id>')
def visualizar_plano(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    plano = PlanoAuditoria.query.get_or_404(id)
    
    # Verifica se existe um arquivo anexado
    if plano.arquivo:
        return render_template('visualizar_plano.html', plano=plano)
    else:
        flash('Nenhum arquivo anexado para este plano.', 'warning')
        return redirect(url_for('plano_de_auditoria'))

# Página de comunicações
# Rota para exibir e cadastrar comunicações
@app.route('/comunicacao', methods=['GET', 'POST'])
def comunicacao():
    if request.method == 'POST':
        # Processar o formulário de nova comunicação
        data = request.form.get('data')
        mensagem = request.form.get('mensagem')

        if data and mensagem:
            try:
                nova_comunicacao = Comunicacao(data=datetime.strptime(data, '%Y-%m-%d').date(), mensagem=mensagem)
                db.session.add(nova_comunicacao)
                db.session.commit()
                flash('Comunicação adicionada com sucesso!', 'success')
            except Exception as e:
                flash(f'Ocorreu um erro ao adicionar a comunicação: {e}', 'danger')
        else:
            flash('Por favor, preencha todos os campos.', 'danger')
        
        return redirect(url_for('comunicacao'))

    # Obter todas as comunicações e anos únicos
    comunicacoes = Comunicacao.query.all()
    anos = {comunicacao.data.year for comunicacao in comunicacoes if comunicacao.data}

    return render_template('comunicacao.html', comunicacoes=comunicacoes, anos=sorted(anos))

@app.route('/comunicacao/<int:id>/editar', methods=['GET', 'POST'])
def editar_comunicacao(id):
    comunicacao = Comunicacao.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            comunicacao.data = datetime.strptime(request.form.get('data'), '%Y-%m-%d').date()
            comunicacao.mensagem = request.form.get('mensagem')
            db.session.commit()
            flash('Comunicação atualizada com sucesso!', 'success')
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar a comunicação: {e}', 'danger')
        
        return redirect(url_for('comunicacao'))

    return render_template('editar_comunicacao.html', comunicacao=comunicacao)

@app.route('/comunicacao/<int:id>/excluir', methods=['POST'])
def excluir_comunicacao(id):
    comunicacao = Comunicacao.query.get_or_404(id)
    db.session.delete(comunicacao)
    db.session.commit()
    flash('Comunicação excluída com sucesso!', 'success')
    return redirect(url_for('comunicacao'))

# Página de documentos
@app.route('/documentos')
def documentos():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('documentos.html')

# Configurações para RAINT
UPLOAD_FOLDER_RAINT = os.path.join(app.root_path, 'uploads', 'RAINT')
app.config['UPLOAD_FOLDER_RAINT'] = UPLOAD_FOLDER_RAINT

# Rota para visualizar o RAINT
@app.route('/raint')
def visualizar_raint():
    directory = app.config['UPLOAD_FOLDER_RAINT']
    
    # Listar arquivos .pdf (caso o nome do arquivo seja .PDF ou .pdf)
    files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    
    # Log para verificar a listagem dos arquivos
    print(f"Arquivos encontrados: {files}")
    
    if not files:
        return render_template('visualizar_raint.html', filename=None)  # Passar None para o caso sem arquivos

    # Pega o arquivo mais recente
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    print(f"Arquivo mais recente: {latest_file}")  # Log para verificar o arquivo encontrado
    
    return render_template('visualizar_raint.html', filename=latest_file)

# Rota para servir os arquivos PDF do RAINT
@app.route('/uploads/RAINT/<path:filename>')
def serve_raint_pdf(filename):
    directory = app.config['UPLOAD_FOLDER_RAINT']
    print(f"Servindo o arquivo: {filename}")  # Log para verificar o arquivo sendo servido
    return send_from_directory(directory, filename)

# Rota para upload de arquivos RAINT
@app.route('/upload_raint', methods=['POST'])
def upload_raint():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_raint'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_raint'))

    # Salvar o arquivo
    file.save(os.path.join(app.config['UPLOAD_FOLDER_RAINT'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_raint'))    
# Configurações para PAINT
UPLOAD_FOLDER_PAINT = os.path.join(app.root_path, 'uploads', 'PAINT')
app.config['UPLOAD_FOLDER_PAINT'] = UPLOAD_FOLDER_PAINT

# Rota para visualizar o PAINT
@app.route('/paint')
def visualizar_paint():
    directory = UPLOAD_FOLDER_PAINT
    # Listar arquivos e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('visualizar_paint.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('visualizar_paint.html', filename=latest_file)

# Rota para servir os arquivos PDF do PAINT
@app.route('/uploads/PAINT/<path:filename>')
def serve_paint_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER_PAINT, filename)

# Rota para upload de arquivos PAINT
@app.route('/upload_paint', methods=['POST'])
def upload_paint():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_paint'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_paint'))

    # Salvar o arquivo
    file.save(os.path.join(app.config['UPLOAD_FOLDER_PAINT'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_paint'))

@app.route('/visualizar_manual')
def visualizar_manual():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    return render_template('visualizar_manual.html')

@app.route('/uploads/Documentos/manual.pdf')
def serve_manual_pdf():
    return send_from_directory('uploads/Documentos', 'Instrução Normativa 01-2024.pdf')

@app.route('/visualizar_decreto')
def visualizar_decreto():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    return render_template('visualizar_decreto.html')

@app.route('/uploads/Documentos/decreto.pdf')
def serve_decreto_pdf():
    return send_from_directory('uploads/Documentos', 'Decreto Municipal 88-2024.pdf')


#-----------------------------------------------------------------------------------------------------------------------#
#                                         Rota para Matriz de Planejamento                                              #
#-----------------------------------------------------------------------------------------------------------------------#

@app.route('/visualizar_matriz_planejamento')
def visualizar_matriz_planejamento():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    directory = os.path.join(app.root_path, 'uploads', 'Documentos')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('visualizar_matriz_planejamento.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('visualizar_matriz_planejamento.html', filename=latest_file)

@app.route('/uploads/Documentos/<path:filename>')
def serve_matriz_planejamento_pdf(filename):
    directory = os.path.join(app.root_path, 'uploads', 'Documentos')
    return send_from_directory(directory, filename)

@app.route('/upload_matriz_planejamento', methods=['POST'])
def upload_matriz_planejamento():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.')
        return redirect(url_for('visualizar_matriz_planejamento'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('visualizar_matriz_planejamento'))

    # Salvar o arquivo
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    flash('Arquivo enviado com sucesso!')
    
    return redirect(url_for('visualizar_matriz_planejamento'))

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads', 'Documentos')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#-----------------------------------------------------------------------------------------------------------------------#
#                                                  Rota para Dashboard                                                  #
#-----------------------------------------------------------------------------------------------------------------------#

def obter_auditorias_por_ano(ano=None):
    query = db.session.query(Auditoria)
    if ano:
        query = query.filter(Auditoria.data.like(f"{ano}-%"))  # Assumindo que `data` está no formato 'YYYY-MM-DD'
    return query.all()

def obter_relatorios_por_ano(ano=None):
    query = db.session.query(Relatorio)
    if ano:
        query = query.filter(Relatorio.data.like(f"{ano}-%"))  # Mesmo formato de data
    return query.all()

@app.route('/dashboard', methods=['GET'])
def dashboard():
    ano = request.args.get('ano')  # Obter o ano do filtro, se fornecido

    auditorias = obter_auditorias_por_ano(ano)
    relatorios = obter_relatorios_por_ano(ano)
    
    # Contagem de status das auditorias
    status_counts = {'Concluído': 0, 'Em andamento': 0, 'Suspenso': 0}
    for auditoria in auditorias:
        status_counts[auditoria.status] += 1

    # Contagem de tipos de relatórios
    tipo_counts = {'Ordinário': 0, 'Extraordinário': 0}
    for relatorio in relatorios:
        tipo_counts[relatorio.tipo] += 1

    # Retorna os anos disponíveis para o filtro (baseados nos registros existentes)
    anos_disponiveis = db.session.query(db.func.strftime('%Y', Auditoria.data)).distinct().all()
    anos_disponiveis = [ano[0] for ano in anos_disponiveis]

    return render_template('Dashboard.html', 
                           status_counts=status_counts, 
                           tipo_counts=tipo_counts, 
                           anos_disponiveis=anos_disponiveis, 
                           ano_selecionado=ano)
    
#-----------------------------------------------------------------------------------------------------------------------#
#                                              Rota para Pedido de Informação                                           #
#-----------------------------------------------------------------------------------------------------------------------#

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_pedido_by_id(id):
    # Fetch the pedido details from the database
    pedido = db.session.query(PedidoInformacao).filter(PedidoInformacao.id == id).first()
    return pedido

@app.route('/pedido_informacao', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        orgao = request.form['orgao']
        processo = request.form['processo']
        data_envio = request.form['data_envio']
        prazo = int(request.form['prazo'])

        novo_pedido = PedidoInformacao(
            orgao=orgao,
            processo=processo,
            data_envio=datetime.strptime(data_envio, '%Y-%m-%d').date(),
            prazo=prazo,
            status='Pendente'
        )
        db.session.add(novo_pedido)
        db.session.commit()
        return redirect(url_for('cadastrar'))

    unidades = [
        (1, 'Secretaria Municipal de Planejamento'),
        (2, 'Secretaria Municipal de Desenvolvimento Econômico'),
        (3, 'Secretaria Municipal de Finanças'),
        (4, 'Secretaria Municipal de Agricultura'),
        (5, 'Secretaria Municipal de Desenvolvimento Urbano'),
        (6, 'Secretaria Municipal de Esportes'),
        (7, 'Secretaria Municipal de Serviços Públicos e Meio Ambiente'),
        (8, 'Secretaria Municipal de Cultura'),
        (9, 'Secretaria Municipal de Turismo e Eventos'),
        (10, 'Secretaria da Mulher'),
        (11, 'Secretaria Municipal de Administração e Patrimônio'),
        (12, 'Secretaria Municipal de Educação'),
        (13, 'Secretaria Municipal de Saúde'),
        (14, 'Secretaria Municipal de Assistência Social')
    ]

    pedidos = PedidoInformacao.query.all()  # Busca do banco de dados
    current_date = datetime.now().date()
    return render_template('pedido_informacao.html', unidades=unidades, pedidos=pedidos, current_date=current_date)

@app.route('/responder/<int:id>', methods=['POST'])
def responder(id):
    pedido = PedidoInformacao.query.get_or_404(id)
    data_resposta = request.form['data_resposta']
    pedido.data_resposta = datetime.strptime(data_resposta, '%Y-%m-%d').date()
    pedido.status = 'Respondido'
    db.session.commit()
    return redirect(url_for('cadastrar'))

@app.route('/editar_pedido/<int:id>', methods=['GET', 'POST'])
def editar_pedido(id):
    pedido = PedidoInformacao.query.get_or_404(id)
    unidades = [
        (1, 'Secretaria Municipal de Planejamento'),
        (2, 'Secretaria Municipal de Desenvolvimento Econômico'),
        (3, 'Secretaria Municipal de Finanças'),
        (4, 'Secretaria Municipal de Agricultura'),
        (5, 'Secretaria Municipal de Desenvolvimento Urbano'),
        (6, 'Secretaria Municipal de Esportes'),
        (7, 'Secretaria Municipal de Serviços Públicos e Meio Ambiente'),
        (8, 'Secretaria Municipal de Cultura'),
        (9, 'Secretaria Municipal de Turismo e Eventos'),
        (10, 'Secretaria da Mulher'),
        (11, 'Secretaria Municipal de Administração e Patrimônio'),
        (12, 'Secretaria Municipal de Educação'),
        (13, 'Secretaria Municipal de Saúde'),
        (14, 'Secretaria Municipal de Assistência Social')
    ]
    
    if request.method == 'POST':
        pedido.orgao = request.form['orgao']
        pedido.processo = request.form['processo']
        pedido.data_envio = datetime.strptime(request.form['data_envio'], '%Y-%m-%d').date()
        pedido.prazo = int(request.form['prazo'])
        
        # Handle the file upload
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and allowed_file(arquivo.filename):
                arquivo.save(os.path.join(PEDIDO_INFORMACAO, arquivo.filename))
                pedido.arquivo = arquivo.filename  # Update the pedido record with the new filename

        db.session.commit()
        flash('Pedido atualizado com sucesso!', 'success')
        return redirect(url_for('cadastrar'))  # Certifique-se de que esta rota existe
    
    return render_template('editar_pedido.html', pedido=pedido, unidades=unidades)

@app.route('/excluir_pedido/<int:id>', methods=['POST'])
def excluir_pedido(id):
    pedido = PedidoInformacao.query.get_or_404(id)
    try:
        db.session.delete(pedido)
        db.session.commit()
        flash('Pedido excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o pedido: {str(e)}', 'danger')
    return redirect(url_for('cadastrar'))

@app.route('/uploads/pedido_de_informacao/<filename>')
def serve_pedido(filename):
    return send_from_directory(PEDIDO_INFORMACAO, filename)

@app.route('/listar_pedidos')
def listar_pedidos():
    pedidos = PedidoInformacao.query.all()
    return render_template('listar_pedidos.html', pedidos=pedidos)

@app.route('/visualizar_pedido/<int:id>')
def visualizar_pedido(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    pedido = PedidoInformacao.query.get_or_404(id)

    # Renderiza a página com os detalhes do pedido
    return render_template('visualizar_pedido.html', pedido=pedido)




#----------------------------------------------------------------------------------------------------------------------#
#                                        Rotas do Controlador Geral do Município                                       #
#----------------------------------------------------------------------------------------------------------------------#

@app.route('/auditorias')
def cgm_auditoria():
    # Obter todas as auditorias do banco de dados
    auditorias = Auditoria.query.all()  # Ajuste conforme seu ORM

    # Obter uma lista única de anos das auditorias (supondo que há uma data associada)
    anos = set(auditoria.data.year for auditoria in auditorias)  # Supondo que `data` seja um campo de data

    return render_template('cgm/Auditorias.html', auditorias=auditorias, anos=sorted(anos))

    
#----------------------------------------------------------------------------------------------------------------------#
@app.route('/meus-relatorios-cgm', methods=['GET', 'POST'])
def meus_relatorios_cgm():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        relatorio_id = request.form.get('id')
        if relatorio_id:
            try:
                relatorio_id = int(relatorio_id)
                relatorio = Relatorio.query.get(relatorio_id)
                if relatorio:
                    db.session.delete(relatorio)
                    db.session.commit()
            except ValueError as e:
                print(f"Error ao excluir relatório: {e}")
        return redirect(url_for('meus_relatorios_cgm'))

    tipo_filtrado = request.args.get('tipo', None)
    ano_filtrado = request.args.get('ano', None)

    query = Relatorio.query

    if tipo_filtrado:
        query = query.filter(Relatorio.tipo == tipo_filtrado)

    if ano_filtrado:
        query = query.filter(db.extract('year', Relatorio.data_fim) == int(ano_filtrado))

    relatorios = query.all()

    # Extraindo anos únicos dos relatórios
    anos = {relatorio.data_fim.year for relatorio in relatorios if relatorio.data_fim}

    tipos_unicos = {relatorio.tipo for relatorio in Relatorio.query.all()}
    relatorios_dict = [relatorio.to_dict() for relatorio in relatorios]

    return render_template('cgm/meus_relatorios.html', relatorios=relatorios_dict, tipos=tipos_unicos, anos=sorted(anos))

@app.route('/visualizar-relatorio-cgm/<filename>')
def visualizar_relatorio_cgm(filename):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.isfile(file_path):
        return "Arquivo não encontrado", 404
    
    return render_template('cgm/visualizar_relatorio.html', filename=filename)

#----------------------------------------------------------------------------------------------------------------------#
    
@app.route('/cgm/plano_de_auditoria')
def cgm_plano_de_auditoria():
    ano = request.args.get('ano')
    tipo = request.args.get('tipo')

    # Obter todos os planos
    query = PlanoAuditoria.query

    # Filtrar por ano
    if ano:
        query = query.filter(PlanoAuditoria.data.ilike(f'{ano}%'))

    # Filtrar por tipo
    if tipo:
        if tipo == 'Ordinária':
            query = query.filter(PlanoAuditoria.numero_auditoria.ilike('%- O'))
        elif tipo == 'Extraordinária':
            query = query.filter(PlanoAuditoria.numero_auditoria.ilike('%- E'))

    planos = query.all()
    auditorias = Auditoria.query.all()

    # Obter lista de anos distintos da tabela PlanoAuditoria
    anos = {plano.data.year for plano in PlanoAuditoria.query.all()}
    
    return render_template('cgm/planoauditoria.html', planos=planos, auditorias=auditorias, anos=sorted(anos))


# Rota para visualizar o arquivo do plano de auditoria na nova localização do template
@app.route('/cgm/visualizar_plano/<int:id>')
def cgm_visualizar_plano(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    plano = PlanoAuditoria.query.get_or_404(id)
    
    # Verifica se existe um arquivo anexado
    if plano.arquivo:
        return render_template('cgm/visualizar_plano.html', plano=plano)
    else:
        flash('Nenhum arquivo anexado para este plano.', 'warning')
        return redirect(url_for('cgm_plano_de_auditoria'))

#----------------------------------------------------------------------------------------------------------------------#

@app.route('/cgm/documentos')
def documentos_view():
    return render_template('cgm/documentos.html')

@app.route('/cgm/raint')
def visualizar_raint_cgm():
    directory = os.path.join(app.root_path, 'uploads', 'RAINT')
    # Listar arquivos e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    
    if not files:
        return render_template('cgm/visualizar_raint.html', ano=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_raint.html', ano=latest_file)

@app.route('/cgm/paint')
def visualizar_paint_cgm():
    directory = UPLOAD_FOLDER_PAINT
    # Listar arquivos e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('cgm/visualizar_paint.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_paint.html', filename=latest_file)

# Rota para a matriz de risco na nova localização do template
@app.route('/cgm/matriz_risco')
def visualizar_matriz_risco_cgm():
    directory = os.path.join(app.root_path, 'uploads', 'matriz_risco')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('cgm/visualizar_matriz_risco.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_matriz_risco.html', filename=latest_file)

@app.route('/cgm/visualizar_matriz_planejamento')
def visualizar_matriz_planejamento_cgm():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    directory = os.path.join(app.root_path, 'uploads', 'Documentos')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('cgm/visualizar_matriz_planejamento.html', filename=None)  # Caso não haja arquivos

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_matriz_planejamento.html', filename=latest_file)

@app.route('/cgm/visualizar_manual')
def visualizar_manual_cgm():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    return render_template('cgm/visualizar_manual.html')

@app.route('/uploads/Documentos/manual.pdf')
def serve_manual_pdf_new():
    return send_from_directory('uploads/Documentos', 'Instrução Normativa 01-2024.pdf')

@app.route('/cgm/visualizar_decreto')
def visualizar_decreto_cgm():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    return render_template('cgm/visualizar_decreto.html')

@app.route('/uploads/Documentos/decreto.pdf')
def serve_decreto_pdf_new():
    return send_from_directory('uploads/Documentos', 'Decreto Municipal 88-2024.pdf')

@app.route('/cgm/leis_08_2023')
def visualizar_leis_08_2023_cgm():
    directory = os.path.join(app.root_path, 'uploads', 'Leis 2')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('cgm/visualizar_leis_08_2023.html', filename=None)

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_leis_08_2023.html', filename=latest_file)

@app.route('/cgm/leis_018_2020')
def visualizar_leis_018_2020_cgm():
    directory = os.path.join(app.root_path, 'uploads', 'Leis')
    
    # Listar os arquivos na pasta e pegar o mais recente
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    if not files:
        return render_template('cgm/visualizar_leis_018_2020.html', filename=None)

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return render_template('cgm/visualizar_leis_018_2020.html', filename=latest_file)



#----------------------------------------------------------------------------------------------------------------------#



# Rota para exibir o pedido de informações no novo local do template
@app.route('/cgm/pedido_informacao', methods=['GET', 'POST'])
def cadastrar_cgm():
    if request.method == 'POST':
        orgao = request.form['orgao']
        processo = request.form['processo']
        data_envio = request.form['data_envio']
        prazo = int(request.form['prazo'])

        novo_pedido = PedidoInformacao(
            orgao=orgao,
            processo=processo,
            data_envio=datetime.strptime(data_envio, '%Y-%m-%d').date(),
            prazo=prazo,
            status='Pendente'
        )
        db.session.add(novo_pedido)
        db.session.commit()
        return redirect(url_for('cadastrar'))

    unidades = [
        (1, 'Secretaria Municipal de Planejamento'),
        (2, 'Secretaria Municipal de Desenvolvimento Econômico'),
        (3, 'Secretaria Municipal de Finanças'),
        (4, 'Secretaria Municipal de Agricultura'),
        (5, 'Secretaria Municipal de Desenvolvimento Urbano'),
        (6, 'Secretaria Municipal de Esportes'),
        (7, 'Secretaria Municipal de Serviços Públicos e Meio Ambiente'),
        (8, 'Secretaria Municipal de Cultura'),
        (9, 'Secretaria Municipal de Turismo e Eventos'),
        (10, 'Secretaria da Mulher'),
        (11, 'Secretaria Municipal de Administração e Patrimônio'),
        (12, 'Secretaria Municipal de Educação'),
        (13, 'Secretaria Municipal de Saúde'),
        (14, 'Secretaria Municipal de Assistência Social')
    ]

    pedidos = PedidoInformacao.query.all()  # Busca do banco de dados
    current_date = datetime.now().date()
    return render_template('cgm/pedido_informacao.html', unidades=unidades, pedidos=pedidos, current_date=current_date)

#----------------------------------------------------------------------------------------------------------------------#   

@app.route('/dashboard/cgm', methods=['GET'])
def dashboard_cgm():
    ano = request.args.get('ano')  # Obter o ano do filtro, se fornecido

    auditorias = obter_auditorias_por_ano(ano)
    relatorios = obter_relatorios_por_ano(ano)

    # Contagem de status das auditorias
    status_counts = {'Concluído': 0, 'Em andamento': 0, 'Suspenso': 0}
    for auditoria in auditorias:
        status_counts[auditoria.status] += 1

    # Contagem de tipos de relatórios
    tipo_counts = {'Ordinário': 0, 'Extraordinário': 0}
    for relatorio in relatorios:
        tipo_counts[relatorio.tipo] += 1

    # Retorna os anos disponíveis para o filtro (baseados nos registros existentes)
    anos_disponiveis = db.session.query(db.func.strftime('%Y', Auditoria.data)).distinct().all()
    anos_disponiveis = [ano[0] for ano in anos_disponiveis]

    return render_template(
        'cgm/Dashboard.html',
        status_counts=status_counts,
        tipo_counts=tipo_counts,
        anos_disponiveis=anos_disponiveis,
        ano_selecionado=ano
    )


#----------------------------------------------------------------------------------------------------------------------#
#                                                Rotas Cadastro de Auditado                                            #
#----------------------------------------------------------------------------------------------------------------------#

@app.route('/usuarios')
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('gestao_usuarios.html', usuarios=usuarios)

@app.route('/usuarios/atualizar/<int:id>', methods=['POST'])
def atualizar_usuario(id):
    # Aqui você deve incluir a lógica para atualizar o usuário no banco de dados
    # E, em seguida, redirecionar para a lista de usuários
    return redirect(url_for('listar_usuarios'))


@app.route('/usuarios/cadastrar', methods=['POST'])
def cadastrar_usuario():
    secretaria = request.form['secretaria']
    cargo = request.form['cargo']
    username = request.form['username']
    senha = request.form['senha']
    
    novo_usuario = Usuario(secretaria=secretaria, cargo=cargo, username=username, senha=senha)
    db.session.add(novo_usuario)
    db.session.commit()
    
    flash('Usuário cadastrado com sucesso!')
    return redirect(url_for('listar_usuarios'))

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.secretaria = request.form['secretaria']
        usuario.cargo = request.form['cargo']
        usuario.username = request.form['username']
        usuario.senha = request.form['senha']
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!')
        return redirect(url_for('listar_usuarios'))

    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário excluído com sucesso!')
    return redirect(url_for('listar_usuarios'))

# Rota para a página específica do auditado
@app.route('/pagina_auditado')
def pagina_auditado():
    if 'logged_in' not in session or session.get('user_role') != 'auditado':
        return redirect(url_for('login_auditado'))
    return render_template('pagina_auditado.html')  # Crie este template conforme necessário  

#----------------------------------------------------------------------------------------------------------------------#
#                                          Rotas Enviar Arquivo ao Auditado                                            #
#----------------------------------------------------------------------------------------------------------------------#

from datetime import datetime
from werkzeug.utils import secure_filename

@app.route('/anexar_documento', methods=['GET', 'POST'])
def anexar_documento():
    if request.method == 'POST':
        secretaria = request.form['secretaria']
        tipo_documento = request.form['tipo_documento']
        arquivo = request.files['arquivo']

        if arquivo:
            filename = secure_filename(arquivo.filename)
            arquivo.save(os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename))

            novo_documento = Documento(
                secretaria=secretaria,
                tipo_documento=tipo_documento,
                arquivo=filename
            )
            db.session.add(novo_documento)
            db.session.commit()

            flash('Documento enviado com sucesso!')
            return redirect(url_for('anexar_documento'))

    # Dados para preencher a tabela de documentos enviados
    documentos = Documento.query.all()

    # Dados para preencher a tabela de respostas recebidas
    respostas = Resposta.query.all()

    secretarias = db.session.query(Usuario.secretaria).distinct().all()

    return render_template('auditado/anexar_documento.html', documentos=documentos, respostas=respostas, secretarias=secretarias)



@app.route('/get_cargo_usuario')
def get_cargo_usuario():
    secretaria = request.args.get('secretaria')
    
    usuario = db.session.query(Usuario.cargo, Usuario.username).filter(Usuario.secretaria == secretaria).first()

    if usuario:
        return {'cargo': usuario.cargo, 'usuario': usuario.username}
    else:
        return {}

@app.route('/baixar_documento/<filename>')
def baixar_documento(filename):
    # Define o diretório onde os arquivos estão salvos
    diretorio_arquivos = os.path.join(app.root_path, 'uploads', 'auditados', 'recebidos')

    try:
        # Envia o arquivo para abrir diretamente no navegador
        return send_from_directory(diretorio_arquivos, filename)
    except FileNotFoundError:
        abort(404)

@app.route('/excluir_documento/<int:id>', methods=['POST'])
def excluir_documento(id):
    documento = Documento.query.get(id)
    if documento:
        db.session.delete(documento)
        db.session.commit()
        flash('Documento excluído com sucesso!')
    else:
        flash('Documento não encontrado.')
    return redirect(url_for('anexar_documento'))

#----------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------------------Auditado---------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#

@app.route('/login_auditado', methods=['GET', 'POST'])
def login_auditado():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        # Verificar as credenciais no banco de dados
        usuario_db = db.session.query(Usuario).filter_by(username=usuario, senha=senha).first()

        if usuario_db:
            # Armazenar informações do usuário na sessão
            session['logged_in'] = True
            session['user_role'] = 'auditado'
            session['user_secretaria'] = usuario_db.secretaria  # Armazenar a secretaria na sessão
            return redirect(url_for('home_auditado'))  # Redireciona para a página do auditado
        else:
            flash('Usuário ou senha incorretos. Tente novamente.')

    return render_template('login_auditado.html')



@app.route('/home_auditado', methods=['GET'])
def home_auditado():
    return render_template('home_auditado.html')

@app.route('/visualizar_pedido_informacao')
def visualizar_pedido_informacao():
    if 'user_secretaria' in session:
        documentos = Documento.query.filter_by(secretaria=session['user_secretaria'], tipo_documento='Solicitação de Informação').all()
        return render_template('auditado/visualizar_pedido_informacao.html', documentos=documentos)
    else:
        flash('Usuário não autenticado.')
        return redirect(url_for('login_auditado'))


# Rota para visualizar o documento diretamente no navegador
@app.route('/visualizar_documento/<filename>')
def visualizar_documento(filename):
    if 'user_secretaria' in session:
        # Serve o arquivo diretamente para visualização no navegador
        return send_from_directory(app.config['AUDITADOS_RECEBIDOS_DIR'], filename)
    else:
        flash('Usuário não autenticado.')
        return redirect(url_for('login_auditado'))

@app.route('/visualizar_plano_auditoria')
def visualizar_plano_auditoria():
    if 'user_secretaria' in session:
        # Filtrar documentos do tipo 'Plano de Auditoria'
        documentos = Documento.query.filter_by(secretaria=session['user_secretaria'], tipo_documento='Plano de Auditoria').all()
        return render_template('auditado/visualizar_plano_auditoria.html', documentos=documentos)
    else:
        flash('Usuário não autenticado.')
        return redirect(url_for('login_auditado'))

@app.route('/visualizar_nota_tecnica')
def visualizar_nota_tecnica():
    if 'user_secretaria' in session:
        documentos = Documento.query.filter_by(secretaria=session['user_secretaria'], tipo_documento='Nota Técnica').all()
        return render_template('auditado/visualizar_nota_tecnica.html', documentos=documentos)
    else:
        flash('Usuário não autenticado.')
        return redirect(url_for('login_auditado'))


@app.route('/responder_nota_tecnica/<int:nota_id>', methods=['GET'])
def responder_nota_tecnica(nota_id):
    tipo_documento = request.args.get('tipo_documento', 'Nota Técnica')
    nota = Documento.query.get_or_404(nota_id)

    # Obtenha os detalhes ou informações adicionais associados à nota
    respostas = nota.respostas

    return render_template('auditado/responder_nota_tecnica.html', nota=nota, tipo_documento=tipo_documento, respostas=respostas)

@app.route('/editar_resposta_nota_tecnica/<int:resposta_id>', methods=['GET', 'POST'])
def editar_resposta_nota_tecnica(resposta_id):
    # Recupera a resposta pelo ID
    resposta = Resposta.query.get_or_404(resposta_id)
    
    if request.method == 'POST':
        # Atualizar o texto da resposta
        resposta.texto_resposta = request.form['texto_resposta']
        
        # Verificar se um novo arquivo foi enviado
        arquivo_resposta = request.files['arquivo_resposta']
        if arquivo_resposta and arquivo_resposta.filename:
            upload_dir = os.path.join(app.root_path, 'uploads', 'auditados', 'recebidos')
            os.makedirs(upload_dir, exist_ok=True)
            arquivo_path = os.path.join(upload_dir, arquivo_resposta.filename)
            arquivo_resposta.save(arquivo_path)
            resposta.arquivo_resposta = arquivo_resposta.filename
        
        # Salvar alterações no banco de dados
        db.session.commit()
        flash("Resposta editada com sucesso.", "success")
        return redirect(url_for('responder_nota_tecnica', nota_id=resposta.documento_id))
    
    # Renderizar página de edição no método GET
    return render_template('auditado/editar_resposta_nota_tecnica.html', resposta=resposta)


@app.route('/enviar_resposta_nota_tecnica/<int:nota_id>', methods=['POST'])
def enviar_resposta_nota_tecnica(nota_id):
    texto_resposta = request.form.get('texto_resposta')
    arquivo_resposta = request.files.get('arquivo_resposta')

    # Recupera o documento original (nota técnica) para pegar a secretaria
    documento = Documento.query.get_or_404(nota_id)

    # Define o caminho para o arquivo de resposta, se existir
    if arquivo_resposta:
        filename = secure_filename(arquivo_resposta.filename)
        caminho_arquivo = os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename)
        arquivo_resposta.save(caminho_arquivo)
    else:
        caminho_arquivo = None

    # Cria uma nova resposta associada ao documento original, incluindo a secretaria
    nova_resposta = Resposta(
        documento_id=documento.id,
        texto_resposta=texto_resposta,
        arquivo_resposta=filename if arquivo_resposta else None,
        secretaria=documento.secretaria  # Preenche a secretaria do documento original
    )

    # Salva a nova resposta no banco de dados
    db.session.add(nova_resposta)
    db.session.commit()

    flash("Resposta à nota técnica enviada com sucesso!")
    return redirect(url_for('visualizar_nota_tecnica'))

@app.route('/anexar_documento_nota_tecnica', methods=['POST'])
def anexar_documento_nota_tecnica():
    # Função para anexar documento na pasta recebidos
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    file = request.files['arquivo']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename))
        flash('Arquivo anexado com sucesso!')
        return redirect(url_for('visualizar_nota_tecnica'))
    
    flash('Tipo de arquivo inválido. Apenas PDFs são permitidos.')
    return redirect(request.url)


# Rota para servir arquivos do diretório 'uploads/auditados/recebidos'
@app.route('/uploads/auditados/recebidos/<filename>')
def serve_uploaded_file(filename):
    # Caminho para o diretório onde os arquivos estão armazenados
    upload_folder = os.path.join(os.getcwd(), 'uploads', 'auditados', 'recebidos')
    
    # Serve o arquivo solicitado
    return send_from_directory(upload_folder, filename)
    

@app.route('/visualizar_relatorios_preliminares')
def visualizar_relatorios_preliminares():
    if 'user_secretaria' in session:
        documentos = Documento.query.filter_by(secretaria=session['user_secretaria'], tipo_documento='Relatório Preliminar').all()
        return render_template('auditado/visualizar_relatorios_preliminares.html', documentos=documentos)
    else:
        flash('Usuário não autenticado.')
        return redirect(url_for('login_auditado'))

@app.route('/responder_relatorios_preliminares/<int:relatorio_id>', methods=['GET'])
def responder_relatorio_preliminar(relatorio_id):
    tipo_documento = request.args.get('tipo_documento', 'Relatório Preliminar')
    relatorio = Documento.query.get_or_404(relatorio_id)
    
    # Obtenha as respostas associadas ao relatório
    respostas = relatorio.respostas
    
    return render_template('auditado/responder_relatorios_preliminares.html', relatorio=relatorio, tipo_documento=tipo_documento, respostas=respostas)


@app.route('/editar_resposta_relatorio_preliminar/<int:resposta_id>', methods=['GET', 'POST'])
def editar_resposta_relatorio_preliminar(resposta_id):
    resposta = Resposta.query.get_or_404(resposta_id)

    if request.method == 'POST':
        resposta.texto_resposta = request.form['texto_resposta']
        arquivo_resposta = request.files['arquivo_resposta']
        if arquivo_resposta and arquivo_resposta.filename:
            upload_dir = os.path.join(app.root_path, 'uploads', 'auditados', 'recebidos')
            os.makedirs(upload_dir, exist_ok=True)
            arquivo_path = os.path.join(upload_dir, arquivo_resposta.filename)
            arquivo_resposta.save(arquivo_path)
            resposta.arquivo_resposta = arquivo_resposta.filename

        db.session.commit()
        flash("Resposta editada com sucesso.", "success")
        return redirect(url_for('responder_relatorio_preliminar', relatorio_id=resposta.documento_id))

    return render_template('auditado/editar_resposta_relatorio_preliminar.html', resposta=resposta)

@app.route('/enviar_resposta_relatorio_preliminar/<int:relatorio_id>', methods=['POST'])
def enviar_resposta_relatorio_preliminar(relatorio_id):
    # Recupera o relatório preliminar
    relatorio = Documento.query.get_or_404(relatorio_id)
    
    # Recupera os dados do formulário
    texto_resposta = request.form.get('texto_resposta')
    arquivo_resposta = request.files.get('arquivo_resposta')
    secretaria = relatorio.secretaria  # Obtém a secretaria associada ao relatório
    
    # Verifica se um arquivo foi enviado
    if arquivo_resposta and arquivo_resposta.filename:
        # Define o caminho para salvar os arquivos
        upload_dir = os.path.join(app.root_path, 'uploads', 'auditados', 'recebidos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Define o caminho completo do arquivo
        arquivo_path = os.path.join(upload_dir, arquivo_resposta.filename)
        
        # Salva o arquivo
        arquivo_resposta.save(arquivo_path)
        
        # Cria uma nova resposta com a secretaria associada
        resposta = Resposta(
            documento_id=relatorio.id,
            texto_resposta=texto_resposta,
            arquivo_resposta=arquivo_resposta.filename,
            secretaria=secretaria
        )
        db.session.add(resposta)
        db.session.commit()
        flash("Resposta enviada com sucesso.", "success")
    else:
        flash("Por favor, anexe um arquivo PDF antes de enviar.", "warning")
    
    return redirect(url_for('responder_relatorio_preliminar', relatorio_id=relatorio_id))


@app.route('/anexar_documento_relatorio_preliminar', methods=['POST'])
def anexar_documento_relatorio_preliminar():
    # Função para anexar documento na pasta recebidos
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    file = request.files['arquivo']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename))
        flash('Arquivo anexado com sucesso!')
        return redirect(url_for('visualizar_relatorios_preliminares'))
    
    flash('Tipo de arquivo inválido. Apenas PDFs são permitidos.')
    return redirect(request.url)


@app.route('/visualizar_relatorios_finais')
def visualizar_relatorios_finais():
    if 'user_secretaria' in session:
        # Filtrar documentos do tipo 'Relatório Final de Auditoria' da secretaria do usuário
        documentos = Documento.query.filter_by(
            secretaria=session['user_secretaria'], 
            tipo_documento='Relatório Final de Auditoria'
        ).all()
        return render_template('auditado/visualizar_relatorios_finais.html', documentos=documentos)
    else:
        # Redirecionar para login se o usuário não estiver autenticado
        flash('Usuário não autenticado. Por favor, faça login.')
        return redirect(url_for('login_auditado'))

@app.route('/anexar_documento_recebidos', methods=['POST'])
def anexar_documento_recebidos():
    # Função para anexar documento na pasta recebidos
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    file = request.files['arquivo']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename))
        flash('Arquivo anexado com sucesso!')
        return redirect(url_for('visualizar_pedido_informacao'))
    
    flash('Tipo de arquivo inválido. Apenas PDFs são permitidos.')
    return redirect(request.url)

@app.route('/responder_pedido_informacao/<int:pedido_id>', methods=['GET'])
def responder_pedido_informacao(pedido_id):
    tipo_documento = request.args.get('tipo_documento', 'Solicitação de Informação')
    pedido = Documento.query.get_or_404(pedido_id)
    
    # Obtenha as respostas associadas ao pedido
    respostas = pedido.respostas
    
    return render_template('auditado/responder_pedido_informacao.html', pedido=pedido, tipo_documento=tipo_documento, respostas=respostas)

@app.route('/enviar_resposta/<int:pedido_id>', methods=['POST'])
def enviar_resposta(pedido_id):
    texto_resposta = request.form.get('texto_resposta')
    arquivo_resposta = request.files.get('arquivo_resposta')
    
    # Recupera o documento original (pedido de informação) para pegar a secretaria
    documento = Documento.query.get_or_404(pedido_id)
    
    # Define o caminho para o arquivo de resposta, se existir
    if arquivo_resposta:
        filename = secure_filename(arquivo_resposta.filename)
        caminho_arquivo = os.path.join(app.config['AUDITADOS_RECEBIDOS_DIR'], filename)
        arquivo_resposta.save(caminho_arquivo)
    else:
        caminho_arquivo = None

    # Cria uma nova resposta associada ao documento original, incluindo a secretaria
    nova_resposta = Resposta(
        documento_id=documento.id,
        texto_resposta=texto_resposta,
        arquivo_resposta=filename if arquivo_resposta else None,
        secretaria=documento.secretaria  # Preenche a secretaria do documento original
    )

    # Salva a nova resposta no banco de dados
    db.session.add(nova_resposta)
    db.session.commit()
    
    flash("Resposta enviada com sucesso!")
    return redirect(url_for('visualizar_pedido_informacao'))

@app.route('/editar_resposta/<int:resposta_id>', methods=['GET', 'POST'])
def editar_resposta(resposta_id):
    resposta = Resposta.query.get_or_404(resposta_id)
    
    if request.method == 'POST':
        # Atualiza o texto da resposta
        resposta.texto_resposta = request.form['texto_resposta']
        
        # Atualiza o arquivo da resposta, se um novo for enviado
        if 'arquivo_resposta' in request.files:
            arquivo = request.files['arquivo_resposta']
            if arquivo and arquivo.filename:
                # Salve o arquivo e atualize o campo arquivo_resposta
                arquivo_path = os.path.join('caminho_para_arquivos', arquivo.filename)
                arquivo.save(arquivo_path)
                resposta.arquivo_resposta = arquivo.filename
        
        db.session.commit()
        flash("Resposta atualizada com sucesso.", "success")
        return redirect(url_for('responder_pedido_informacao', pedido_id=resposta.documento_id))

    return render_template('auditado/editar_resposta.html', resposta=resposta)

#----------------------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------Logout---------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#

@app.route('/logout', endpoint='logout_user')
def logout_user():
    session.clear('logged_in', None)
    return redirect(url_for('login'))

#----------------------------------------------------------------------------------------------------------------------#


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
    app.run(host='0.0.0.0', port=5000, debug=True)

