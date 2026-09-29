import os
import json
import uuid
import mimetypes
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, jsonify, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ppged-ufu-secret-key-2024-change-in-production')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, 'static', 'audio')
DATA_DIR  = os.environ.get('DATA_DIR', BASE_DIR)
DATA_FILE  = os.path.join(DATA_DIR, 'data.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'oga', 'opus', 'm4a', 'aac'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Rótulo único usado nas mensagens e nos formulários
FORMATOS_LABEL = 'MP3, WAV, OGG, OPUS, M4A ou AAC'

# MIME types por extensão. O .opus (Opus dentro de contêiner Ogg) não é
# reconhecido por padrão em várias instalações do Python, por isso é
# registrado explicitamente — sem isso o arquivo é servido como
# application/octet-stream e o navegador se recusa a tocar.
AUDIO_MIMETYPES = {
    'mp3':  'audio/mpeg',
    'wav':  'audio/wav',
    'ogg':  'audio/ogg',
    'oga':  'audio/ogg',
    'opus': 'audio/ogg; codecs=opus',
    'm4a':  'audio/mp4',
    'aac':  'audio/aac',
}

mimetypes.add_type('audio/ogg', '.opus')
mimetypes.add_type('audio/ogg', '.oga')

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# ─── Data helpers ────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"dissertacoes": [], "teses": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    if not os.path.exists(USERS_FILE):
        # Default admin
        users = {"admin": generate_password_hash("ppged2024")}
        save_users(users)
        return users
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def audio_mime(filename):
    """MIME type do áudio a partir da extensão (fallback: audio/mpeg)."""
    if not filename or '.' not in filename:
        return 'audio/mpeg'
    ext = filename.rsplit('.', 1)[1].lower()
    return AUDIO_MIMETYPES.get(ext, 'audio/mpeg')


# Disponibiliza o helper nos templates: {{ item.audio|audio_mime }}
app.jinja_env.filters['audio_mime'] = audio_mime


# ─── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Faça login para acessar esta área.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    data = load_data()
    query = request.args.get('q', '').strip().lower()
    tipo = request.args.get('tipo', 'todos')

    dissertacoes = data.get('dissertacoes', [])
    teses = data.get('teses', [])

    if query:
        dissertacoes = [d for d in dissertacoes if
                        query in d.get('titulo', '').lower() or
                        query in d.get('autor', '').lower() or
                        query in d.get('ano', '').lower() or
                        query in d.get('resumo', '').lower()]
        teses = [t for t in teses if
                 query in t.get('titulo', '').lower() or
                 query in t.get('autor', '').lower() or
                 query in t.get('ano', '').lower() or
                 query in t.get('resumo', '').lower()]

    return render_template('index.html',
                           dissertacoes=dissertacoes,
                           teses=teses,
                           query=query,
                           tipo=tipo,
                           is_admin='username' in session)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        users = load_users()
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            flash(f'Bem-vindo, {username}!', 'success')
            return redirect(url_for('admin'))
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin():
    data = load_data()
    return render_template('admin.html',
                           dissertacoes=data.get('dissertacoes', []),
                           teses=data.get('teses', []),
                           username=session['username'])


@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        tipo = request.form.get('tipo')  # 'dissertacoes' or 'teses'
        titulo = request.form.get('titulo', '').strip()
        autor = request.form.get('autor', '').strip()
        ano = request.form.get('ano', '').strip()
        resumo = request.form.get('resumo', '').strip()
        url_repositorio = request.form.get('url_repositorio', '').strip()
        audio_file = request.files.get('audio')

        if not titulo or not autor or not tipo:
            flash('Título, autor e tipo são obrigatórios.', 'danger')
            return render_template('add_item.html')

        audio_filename = None
        if audio_file and audio_file.filename:
            if not allowed_file(audio_file.filename):
                flash(f'Formato de áudio inválido. Use {FORMATOS_LABEL}.', 'danger')
                return render_template('add_item.html')
            ext = audio_file.filename.rsplit('.', 1)[1].lower()
            audio_filename = f"{uuid.uuid4().hex}.{ext}"
            audio_file.save(os.path.join(AUDIO_DIR, audio_filename))

        item = {
            "id": uuid.uuid4().hex,
            "titulo": titulo,
            "autor": autor,
            "ano": ano,
            "resumo": resumo,
            "url_repositorio": url_repositorio,
            "audio": audio_filename,
            "criado_em": datetime.now().isoformat(),
            "criado_por": session['username']
        }

        data = load_data()
        if tipo not in data:
            data[tipo] = []
        data[tipo].append(item)
        save_data(data)

        tipo_label = "Dissertação" if tipo == "dissertacoes" else "Tese"
        flash(f'{tipo_label} "{titulo}" adicionada com sucesso!', 'success')
        return redirect(url_for('admin'))

    return render_template('add_item.html')


@app.route('/admin/edit/<tipo>/<item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(tipo, item_id):
    if tipo not in ('dissertacoes', 'teses'):
        abort(404)
    data = load_data()
    items = data.get(tipo, [])
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        abort(404)

    if request.method == 'POST':
        item['titulo'] = request.form.get('titulo', '').strip()
        item['autor'] = request.form.get('autor', '').strip()
        item['ano'] = request.form.get('ano', '').strip()
        item['resumo'] = request.form.get('resumo', '').strip()
        item['url_repositorio'] = request.form.get('url_repositorio', '').strip()

        audio_file = request.files.get('audio')
        if audio_file and audio_file.filename:
            if not allowed_file(audio_file.filename):
                flash(f'Formato de áudio inválido. Use {FORMATOS_LABEL}.', 'danger')
                return render_template('edit_item.html', item=item, tipo=tipo)
            # Remove old audio
            if item.get('audio'):
                old_path = os.path.join(AUDIO_DIR, item['audio'])
                if os.path.exists(old_path):
                    os.remove(old_path)
            ext = audio_file.filename.rsplit('.', 1)[1].lower()
            audio_filename = f"{uuid.uuid4().hex}.{ext}"
            audio_file.save(os.path.join(AUDIO_DIR, audio_filename))
            item['audio'] = audio_filename

        save_data(data)
        flash('Atualizado com sucesso!', 'success')
        return redirect(url_for('admin'))

    return render_template('edit_item.html', item=item, tipo=tipo)


@app.route('/admin/delete/<tipo>/<item_id>', methods=['POST'])
@login_required
def delete_item(tipo, item_id):
    if tipo not in ('dissertacoes', 'teses'):
        abort(404)
    data = load_data()
    items = data.get(tipo, [])
    item = next((i for i in items if i['id'] == item_id), None)
    if item:
        if item.get('audio'):
            audio_path = os.path.join(AUDIO_DIR, item['audio'])
            if os.path.exists(audio_path):
                os.remove(audio_path)
        data[tipo] = [i for i in items if i['id'] != item_id]
        save_data(data)
        flash('Item removido com sucesso.', 'success')
    return redirect(url_for('admin'))


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files — read only, no auth required for public listening."""
    safe = secure_filename(filename)
    mime = audio_mime(safe)
    # conditional=True mantém as requisições de intervalo (Range), necessárias
    # para arrastar a barra de progresso em arquivos longos.
    return send_from_directory(AUDIO_DIR, safe, mimetype=mime, conditional=True)


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    users = load_users()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            new_user = request.form.get('new_username', '').strip()
            new_pass = request.form.get('new_password', '')
            if new_user and new_pass:
                if new_user in users:
                    flash('Usuário já existe.', 'danger')
                else:
                    users[new_user] = generate_password_hash(new_pass)
                    save_users(users)
                    flash(f'Usuário "{new_user}" criado.', 'success')
            else:
                flash('Nome de usuário e senha são obrigatórios.', 'danger')
        elif action == 'delete':
            del_user = request.form.get('del_username')
            if del_user == session['username']:
                flash('Você não pode remover seu próprio usuário.', 'danger')
            elif del_user in users:
                del users[del_user]
                save_users(users)
                flash(f'Usuário "{del_user}" removido.', 'success')
    users = load_users()
    return render_template('users.html', users=list(users.keys()), current=session['username'])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
