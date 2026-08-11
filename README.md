# Repositório Acessível – PPGED/FACED/UFU

Plataforma web acessível para pessoas com deficiência visual acessarem áudios dos resumos de dissertações e teses do Programa de Pós-Graduação em Educação (PPGED) da Faculdade de Educação (FACED) da Universidade Federal de Uberlândia.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-app-lightgrey)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Ubuntu](https://img.shields.io/badge/Ubuntu%20Server-26.04-E95420)

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Conteúdo do repositório](#conteúdo-do-repositório)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Execução local (desenvolvimento)](#execução-local-desenvolvimento)
- [Deploy com Docker no Ubuntu Server 26](#deploy-com-docker-no-ubuntu-server-26)
  - [1. Preparar o servidor](#1-preparar-o-servidor)
  - [2. Instalar o Docker Engine](#2-instalar-o-docker-engine)
  - [3. Preparar o diretório da aplicação](#3-preparar-o-diretório-da-aplicação)
  - [4. Arquivos do container](#4-arquivos-do-container)
  - [5. Persistência de dados](#5-persistência-de-dados)
  - [6. Subir a aplicação](#6-subir-a-aplicação)
  - [7. Comandos do dia a dia](#7-comandos-do-dia-a-dia)
- [Nginx como proxy reverso e HTTPS](#nginx-como-proxy-reverso-e-https)
- [Firewall (UFW)](#firewall-ufw)
- [Backup e restauração](#backup-e-restauração)
- [Atualização da aplicação](#atualização-da-aplicação)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Troubleshooting](#troubleshooting)
- [Checklist de segurança](#checklist-de-segurança)

---

## Funcionalidades

- Listagem pública de dissertações e teses com player de áudio nativo
- Busca por título, autor, ano ou palavras do resumo
- Filtro por tipo (dissertação / tese)
- Link para o repositório institucional da UFU de cada trabalho
- Upload de arquivos de áudio (MP3, WAV, OGG, M4A, AAC – até 50 MB)
- Sistema de login e senha para administradores
- Gerenciamento de usuários (adicionar / remover)
- Acessibilidade: `aria-labels`, skip-link, alto contraste, `prefers-reduced-motion`

---

## Conteúdo do repositório

O código-fonte é distribuído em tarballs versionados na raiz do repositório:

| Arquivo | Descrição |
|---|---|
| `ppged-audio.tar.gz` | Versão atual da aplicação |
| `ppged-audio_v1.tar.gz` | Versão 1 (histórica) |
| `README.md` | Este documento |

Para extrair:

```bash
git clone https://github.com/lucastuxnet/Vozes_faced.git
cd Vozes_faced
tar -xzf ppged-audio.tar.gz
cd ppged-audio
```

> Confira o conteúdo antes de extrair com `tar -tzf ppged-audio.tar.gz | head -30`.
> Se o tarball extrair os arquivos diretamente na pasta atual (sem a pasta `ppged-audio/`),
> ajuste os caminhos dos passos seguintes.

---

## Estrutura do projeto

```
ppged-audio/
├── app.py               # Aplicação Flask principal
├── requirements.txt
├── data.json            # Dados das obras (gerado automaticamente)
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

Os três caminhos que precisam de persistência são **`data.json`**, **`users.json`** e **`static/audio/`**. Todo o resto é código e pode ser recriado a partir da imagem.

---

## Execução local (desenvolvimento)

```bash
cd ppged-audio

python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

export SECRET_KEY="troque-esta-chave"
python app.py
```

Acesse <http://localhost:5000>.

**Login padrão:** usuário `admin` / senha `ppged2024`
> ⚠️ Troque a senha no primeiro acesso em **Painel → Gerenciar Usuários**.

---

## Deploy com Docker no Ubuntu Server 26

Cenário-alvo: Ubuntu Server 26.04 LTS, aplicação em container, dados persistidos em bind mounts no host, Nginx no host fazendo proxy reverso e TLS.

### 1. Preparar o servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git tar
sudo timedatectl set-timezone America/Sao_Paulo
```

### 2. Instalar o Docker Engine

```bash
# Chave GPG oficial
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Repositório
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable --now docker
docker --version && docker compose version
```

> **Se o `apt update` retornar 404 no repositório do Docker:** releases muito recentes do Ubuntu
> podem ainda não ter diretório próprio no repositório oficial. Nesse caso, substitua
> `$(. /etc/os-release && echo "$VERSION_CODENAME")` pelo codename LTS anterior suportado
> (ex.: `noble`) no arquivo `/etc/apt/sources.list.d/docker.list` e rode `sudo apt update` novamente.
> Alternativa imediata: `sudo apt install -y docker.io docker-compose-v2` (pacotes do próprio Ubuntu).

Usar Docker sem `sudo` (opcional, requer novo login):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Preparar o diretório da aplicação

```bash
sudo mkdir -p /opt/vozes-faced
sudo chown "$USER":"$USER" /opt/vozes-faced
cd /opt/vozes-faced

git clone https://github.com/lucastuxnet/Vozes_faced.git src
tar -xzf src/ppged-audio.tar.gz -C /opt/vozes-faced
# Resultado esperado: /opt/vozes-faced/ppged-audio/app.py
ls ppged-audio
```

Antes de seguir, **confirme os nomes dos arquivos de dados** usados pelo `app.py` (eles precisam bater com os mounts):

```bash
grep -nE "data\.json|users\.json|UPLOAD_FOLDER|MAX_CONTENT_LENGTH|app\.run" ppged-audio/app.py
```

Se os caminhos forem diferentes dos assumidos aqui, ajuste o `docker-compose.yml` do passo 4.

### 4. Arquivos do container

Crie os três arquivos abaixo **dentro de `/opt/vozes-faced/ppged-audio/`**.

#### `Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn

COPY . .

# Usuário não-root com UID 1000 (mesmo dono dos bind mounts no host)
RUN useradd -u 1000 -m appuser \
 && mkdir -p /app/static/audio \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:5000/ || exit 1

# timeout alto para uploads de áudio de até 50 MB
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "180", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
```

#### `.dockerignore`

```
venv/
__pycache__/
*.pyc
.git/
.env
dados/
static/audio/*
data.json
users.json
*.tar.gz
```

#### `docker-compose.yml`

```yaml
services:
  web:
    build: .
    image: vozes-faced:latest
    container_name: vozes-faced
    restart: unless-stopped
    env_file: .env
    ports:
      # só o localhost do host acessa; o Nginx faz o proxy
      - "127.0.0.1:5000:5000"
    volumes:
      - ./dados/data.json:/app/data.json
      - ./dados/users.json:/app/users.json
      - ./dados/audio:/app/static/audio
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

> Para acessar direto pelo IP do servidor (sem Nginx), troque a porta por `"5000:5000"`.

#### `.env`

```bash
cd /opt/vozes-faced/ppged-audio
cat > .env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production
TZ=America/Sao_Paulo
EOF
chmod 600 .env
```

### 5. Persistência de dados

Bind mounts de **arquivo** exigem que o arquivo já exista no host — caso contrário o Docker cria um diretório com esse nome e a aplicação quebra. A forma mais segura de gerar `data.json` e `users.json` no formato correto é deixar a própria aplicação criá-los na primeira execução e copiá-los para fora:

```bash
cd /opt/vozes-faced/ppged-audio
mkdir -p dados/audio

docker compose build

# sobe um container temporário só para gerar os arquivos
docker run --rm -d --name vozes-seed vozes-faced:latest
sleep 8
curl -s http://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' vozes-seed):5000/ > /dev/null || true

docker cp vozes-seed:/app/data.json  ./dados/data.json  2>/dev/null || echo '[]' > ./dados/data.json
docker cp vozes-seed:/app/users.json ./dados/users.json
docker cp vozes-seed:/app/static/audio/. ./dados/audio/ 2>/dev/null || true

docker rm -f vozes-seed
sudo chown -R 1000:1000 dados
ls -l dados dados/audio
```

Se `docker cp` do `users.json` falhar, significa que o arquivo só é criado no primeiro login — nesse caso rode a aplicação uma vez sem o mount de `users.json`, faça login e então copie o arquivo gerado.

### 6. Subir a aplicação

```bash
cd /opt/vozes-faced/ppged-audio
docker compose up -d
docker compose ps
docker compose logs -f web
```

Teste local no servidor:

```bash
curl -I http://127.0.0.1:5000/
```

O container sobe sozinho após reboot graças a `restart: unless-stopped` + `systemctl enable docker`.

### 7. Comandos do dia a dia

```bash
docker compose ps                 # status
docker compose logs -f web        # logs em tempo real
docker compose logs --tail 100 web
docker compose restart web        # reiniciar
docker compose down               # parar e remover container
docker compose up -d --build      # rebuild após alterar o código
docker compose exec web sh        # shell dentro do container
docker stats vozes-faced          # consumo de CPU/RAM
```

---

## Nginx como proxy reverso e HTTPS

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/vozes-faced
```

```nginx
server {
    listen 80;
    server_name vozes.faced.ufu.br;   # ajuste para o seu domínio

    # precisa ser maior que o limite de upload da aplicação (50 MB)
    client_max_body_size 55M;

    access_log /var/log/nginx/vozes-faced.access.log;
    error_log  /var/log/nginx/vozes-faced.error.log;

    # áudios servidos direto pelo Nginx (bind mount no host)
    location /static/audio/ {
        alias /opt/vozes-faced/ppged-audio/dados/audio/;
        add_header Accept-Ranges bytes;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vozes-faced /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

O Nginx precisa de permissão de travessia até a pasta de áudios:

```bash
sudo chmod o+x /opt/vozes-faced /opt/vozes-faced/ppged-audio /opt/vozes-faced/ppged-audio/dados
```

### Certificado TLS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d vozes.faced.ufu.br
sudo systemctl status certbot.timer     # renovação automática
```

> Em domínios `.ufu.br` o certificado normalmente é emitido pelo CTI/DTI da universidade.
> Nesse caso, instale o `.crt` e a chave manualmente e configure `ssl_certificate` /
> `ssl_certificate_key` no bloco `server`.

---

## Firewall (UFW)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status verbose
```

Com a porta publicada como `127.0.0.1:5000`, a aplicação não fica exposta diretamente na rede — apenas via Nginx.

---

## Backup e restauração

Tudo que importa está em `dados/`.

```bash
# backup manual
cd /opt/vozes-faced/ppged-audio
tar -czf ~/vozes-backup-$(date +%F).tar.gz dados/
```

Backup diário via cron (03:00, mantendo 14 dias):

```bash
sudo mkdir -p /var/backups/vozes-faced
sudo crontab -e
```

```cron
0 3 * * * tar -czf /var/backups/vozes-faced/vozes-$(date +\%F).tar.gz -C /opt/vozes-faced/ppged-audio dados/ && find /var/backups/vozes-faced -name 'vozes-*.tar.gz' -mtime +14 -delete
```

Restauração:

```bash
cd /opt/vozes-faced/ppged-audio
docker compose down
rm -rf dados
tar -xzf /var/backups/vozes-faced/vozes-2026-08-11.tar.gz -C .
sudo chown -R 1000:1000 dados
docker compose up -d
```

---

## Atualização da aplicação

```bash
cd /opt/vozes-faced

# backup antes de qualquer coisa
tar -czf ~/vozes-pre-update-$(date +%F).tar.gz ppged-audio/dados/

# baixar a nova versão
cd src && git pull && cd ..
mv ppged-audio ppged-audio.bak
tar -xzf src/ppged-audio.tar.gz -C /opt/vozes-faced

# recuperar configuração e dados
cp ppged-audio.bak/Dockerfile ppged-audio.bak/docker-compose.yml \
   ppged-audio.bak/.dockerignore ppged-audio.bak/.env ppged-audio/
cp -a ppged-audio.bak/dados ppged-audio/

cd ppged-audio
docker compose up -d --build
docker compose logs -f web
```

Confirmando que subiu tudo certo, remova `ppged-audio.bak`.

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | gerada pelo app | Chave de assinatura das sessões Flask. **Defina em produção** — sem ela, todas as sessões caem a cada restart. |
| `TZ` | `UTC` | Fuso horário do container. |
| `FLASK_ENV` | — | Use `production`. Nunca `development` em servidor. |

Todas são lidas do arquivo `.env` pelo `docker compose`.

---

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `data.json` ou `users.json` virou uma pasta | O bind mount foi criado antes do arquivo existir | `docker compose down`, `rm -rf dados/data.json`, refazer o passo 5 |
| `Permission denied` ao salvar dados/upload | Dono dos arquivos no host ≠ UID 1000 | `sudo chown -R 1000:1000 dados` |
| Upload falha com **413** | Limite do Nginx | Aumentar `client_max_body_size` (≥ 55M) e recarregar o Nginx |
| Upload falha com **502** em arquivos grandes | Timeout do gunicorn/proxy | Aumentar `--timeout` no `CMD` e `proxy_read_timeout` |
| Container reiniciando em loop | Erro na inicialização do app | `docker compose logs --tail 100 web` |
| Áudio não toca / 404 | `alias` do Nginx aponta para caminho errado | Conferir o caminho em `location /static/audio/` e as permissões `o+x` |
| Sessões caem a cada restart | `SECRET_KEY` não definida | Definir no `.env` e `docker compose up -d` |
| Página 502 logo após deploy | Container ainda subindo | Aguardar o healthcheck: `docker compose ps` deve mostrar `healthy` |
| Disco enchendo | Imagens e logs antigos | `docker system prune -a` (cuidado) e checar `dados/audio` |

Diagnóstico rápido:

```bash
docker compose ps
docker inspect --format='{{.State.Health.Status}}' vozes-faced
docker compose exec web ls -la /app/data.json /app/users.json /app/static/audio
sudo tail -50 /var/log/nginx/vozes-faced.error.log
df -h /
```

---

## Checklist de segurança

- [ ] Senha do `admin` alterada (padrão `ppged2024` é público neste README)
- [ ] `SECRET_KEY` aleatória definida no `.env`, com `chmod 600`
- [ ] Aplicação publicada apenas em `127.0.0.1:5000`, exposta via Nginx
- [ ] HTTPS ativo e redirecionamento de HTTP → HTTPS
- [ ] UFW habilitado com apenas SSH e HTTP/HTTPS liberados
- [ ] Container rodando como usuário não-root (`USER appuser` no Dockerfile)
- [ ] Backup automatizado de `dados/` e restauração testada pelo menos uma vez
- [ ] `unattended-upgrades` ativo no host: `sudo apt install -y unattended-upgrades`
- [ ] Rebuild periódico da imagem para trazer patches da base `python:3.12-slim`

---

## Créditos

Projeto desenvolvido para o PPGED / Faculdade de Educação (FACED) / Universidade Federal de Uberlândia.

Mantenedor: [@lucastuxnet](https://github.com/lucastuxnet)
