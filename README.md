# GearFlow

Protótipo de um sistema de gestão para uma loja de informática, desenvolvido
como projeto de estudo e apresentação de portfólio.

> **Estado do projeto:** este repositório apresenta o código da aplicação, mas
> não contém as pastas da interface (`templates/` e `static/`). Portanto, o
> site não está pronto para executar ao clonar este repositório e não está
> publicado como aplicação online.

## Sobre

O GearFlow explora um fluxo de gestão de produtos e vendas, com backend em
Python/Flask e persistência local em SQLite.

## Funcionalidades previstas no código

- Login com senha armazenada em hash e controle de acesso por perfil.
- Cadastro e gestão de produtos, estoque e movimentações.
- Cadastro de usuários e edição de perfil.
- Cupons de desconto e validação no checkout.
- Registro e consulta de vendas, com resumo para relatórios.
- Criação automática do banco SQLite e de dados iniciais de demonstração.

## Tecnologias

- Python e Flask
- SQLite
- HTML, CSS e JavaScript (interface não incluída neste repositório)

## Estrutura

- `app.py` — rotas, autenticação e regras da aplicação.
- `schema.sql` — tabelas e estrutura do banco de dados.
- `migrar_cupons.py` — script de migração do banco.
- `requirements.txt` — dependências Python.
- `roteiro_vibe_coding_interativo (1).html` — página HTML independente, incluída
  como material separado; não faz parte da interface do GearFlow.

## Para executar

Este checkout não pode ser executado como aplicação completa porque faltam
`templates/login.html`, `templates/app.html`, `templates/cadastro.html` e os
arquivos estáticos referenciados pela interface. Ele está sendo compartilhado
para apresentação do código-fonte, não como demonstração online.

Quando os arquivos da interface estiverem disponíveis, será possível instalar
as dependências com `python -m pip install -r requirements.txt` e iniciar o
servidor com `python app.py`.

## Dados e segurança

O banco SQLite é criado localmente. Arquivos de banco e configurações locais
estão excluídos pelo `.gitignore` para não publicar dados pessoais ou segredos.
As credenciais e configurações de demonstração do código não devem ser usadas
em uma implantação pública.

## Publicar no GitHub

Crie um repositório vazio no GitHub e, nesta pasta, configure o endereço do
repositório e envie a branch principal:

```bash
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
git push -u origin main
```

O GitHub hospeda o código-fonte; para executar o Flask online é necessário um
serviço de hospedagem compatível com Python.
