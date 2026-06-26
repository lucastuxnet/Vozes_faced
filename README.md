# Repositório Acessível – PPGED/FACED/UFU

Plataforma web acessível para pessoas com deficiência visual acessarem áudios dos resumos
de dissertações e teses do PPGED/UFU.

## Funcionalidades

- Listagem pública de dissertações e teses com player de áudio nativo
- Busca por título, autor, ano ou palavras do resumo
- Filtro por tipo (dissertação / tese)
- Link para o repositório UFU de cada trabalho
- Upload de arquivos de áudio (MP3, WAV, OGG, M4A, AAC – até 50 MB)
- Sistema de login e senha para administradores
- Gerenciamento de usuários (adicionar / remover)
- Totalmente acessível: aria-labels, skip-link, alto contraste, reduced-motion

## Requisitos

- Python 3.8+
- pip

## Instalação

```bash
# 1. Clone ou copie a pasta do projeto
cd ppged-audio

# 2. Crie e ative um ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. (Opcional) Defina uma chave secreta segura
export SECRET_KEY="sua-chave-secreta-aqui"

# 5. Inicie o servidor
python app.py
```

Acesse em http://localhost:5000

## Login padrão

- **Usuário:** `admin`
- **Senha:** `ppged2024`

> ⚠️ Altere a senha após o primeiro acesso em Painel → Gerenciar Usuários.

## Deploy em produção (Linux)

Para produção, use Gunicorn + Nginx:

```bash
pip install gunicorn

# Rodar com gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Exemplo de configuração Nginx:

```nginx
server {
    listen 80;
    server_name seu-dominio.ufu.br;

    client_max_body_size 55M;

    location /static/ {
        alias /caminho/para/ppged-audio/static/;
    }

    location /audio/ {
        alias /caminho/para/ppged-audio/static/audio/;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Estrutura de arquivos

```
ppged-audio/
├── app.py               # Aplicação Flask principal
├── requirements.txt
├── data.json            # Dados (gerado automaticamente)
├── users.json           # Usuários (gerado automaticamente)
├── static/
│   ├── css/style.css
│   ├── js/player.js
│   ├── img/             # Logos
│   └── audio/           # Arquivos de áudio (uploads)
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── admin.html
    ├── add_item.html
    ├── edit_item.html
    └── users.html
```
