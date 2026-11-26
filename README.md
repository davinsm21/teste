# GearFlow — nova versão
Projeto independente, em português, com Flask, SQLite, HTML, CSS e JavaScript puro. SQLite é criado automaticamente; valores monetários são armazenados em centavos. Sessões e hashes Werkzeug controlam acesso, com validação de perfil no servidor e token CSRF nas operações autenticadas.

## Executar no Windows / VS Code
1. Extraia o ZIP em uma pasta nova. Abra a pasta GearFlow_Novo no VS Code.
2. Abra Terminal > Novo terminal. Execute um comando por vez:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

3. Abra http://127.0.0.1:5000 no navegador. Deixe o terminal aberto. Se a porta estiver ocupada pelo projeto antigo, encerre o servidor antigo com Ctrl+C.

## Contas de demonstração
- admin@gearflow.com
- vendedor@gearflow.com
- cliente@gearflow.com
- Senha inicial de todas: 123456

O administrador cria outras contas em Usuários. O banco local é independente do projeto anterior. Os produtos iniciais são fictícios.

## Estrutura
- app.py: rotas, autenticação, permissões, transações de estoque e pedidos.
- schema.sql: tabelas do banco.
- templates/: login e estrutura do painel.
- static/css/: identidade visual responsiva.
- static/js/: módulos de navegação, catálogo, estoque, vendas e usuários.

## Limites desta versão local
Pagamentos são registros manuais, sem Pix real, integração de cartão ou comprovante fiscal. Pedidos do cliente ficam pendentes e reservam estoque; cancelamento pelo administrador devolve estoque. Vendas operacionais são concluídas manualmente. Permissões são fixas por perfil, sem exceções individuais. Exclusão de produto é lógica para preservar histórico. Destaques do catálogo são produtos de demonstração, sem motor de promoções. Carrinho fica em memória durante a sessão da página. Não publicar na internet sem revisar segurança, configurar SECRET_KEY persistente, trocar senhas de demonstração, HTTPS e servidor de produção. Não há migração do banco antigo.
