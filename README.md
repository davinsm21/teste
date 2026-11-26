# GearFlow

Aplicação de demonstração para gestão de uma loja de informática. O projeto
inclui autenticação, catálogo de produtos, estoque, cupons e registro de
pedidos, usando Flask e SQLite.

## Requisitos

- Python 3.9 ou superior
- Git (para clonar ou publicar o repositório)

## Executar localmente

```bash
git clone URL_DO_REPOSITORIO
cd NOME_DO_REPOSITORIO
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Linux/macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instale as dependências e inicie a aplicação:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>. O banco `gearflow.db` é criado automaticamente
na primeira execução e fica apenas na máquina local.

### Contas de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | `admin@gearflow.com` | `123456` |
| Vendedor | `vendedor@gearflow.com` | `123456` |
| Cliente | `cliente@gearflow.com` | `123456` |

Essas contas são exclusivamente para demonstração. Não use essas credenciais
nem os dados de exemplo em uma implantação real.

## Estrutura

- `app.py` — aplicação Flask, rotas e regras de negócio.
- `schema.sql` — esquema inicial do banco SQLite.
- `templates/` — páginas HTML renderizadas pelo Flask.
- `static/css/` e `static/js/` — estilos e scripts do navegador.
- `migrar_cupons.py` — migração manual de bancos legados.
- `requirements.txt` — dependências Python.

## Configuração

O servidor local usa `127.0.0.1:5000` por padrão. É possível definir `HOST`,
`PORT` e `SECRET_KEY` por variáveis de ambiente. Se `SECRET_KEY` não for
definida, a aplicação gera uma chave temporária ao iniciar; sessões existentes
serão invalidadas quando o processo reiniciar.

## Publicar no GitHub

1. Crie um repositório vazio no GitHub.
2. Na pasta deste projeto, configure o endereço do repositório e envie a branch:

```bash
git add .
git commit -m "Preparar projeto GearFlow"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
git push -u origin main
```

Não publique arquivos `.env`, bancos SQLite (`*.db`, `*.sqlite*`) ou imagens
enviadas durante o uso; esses arquivos são ignorados pelo `.gitignore`.
Publicar o código no GitHub não hospeda a aplicação: para deixá-la acessível
online, será necessário configurar um serviço de hospedagem compatível com
Python e definir uma chave `SECRET_KEY` segura.
