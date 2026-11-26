import os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, session, redirect, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash


# CALCULAR PREÇO FINAL DO PRODUTO

def final_price(p):
    price = p["price"]
    promotional = p["promotional_price"]

    if promotional is not None and 0 <= promotional < price:
        return promotional

    return price

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

DB = os.path.join(app.root_path, 'gearflow.db')


# BANCO DE DADOS

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


@app.teardown_appcontext
def close(e):
    if 'db' in g:
        g.db.close()


with app.app_context():

    db().executescript(
        open(
            os.path.join(app.root_path, 'schema.sql'),
            encoding='utf8'
        ).read()
    )

    # Adicionar CPF e telefone

    colunas = [
        coluna['name']
        for coluna in db().execute("PRAGMA table_info(users)")
    ]

    if 'cpf' not in colunas:
        db().execute("ALTER TABLE users ADD COLUMN cpf TEXT")

    if 'phone' not in colunas:
        db().execute("ALTER TABLE users ADD COLUMN phone TEXT")

        # Atualizar estrutura dos produtos, vendas e itens

    novas_colunas = {
        'products': {
            'image': "TEXT DEFAULT ''",
            'brand': "TEXT DEFAULT ''",
            'model': "TEXT DEFAULT ''",
            'description': "TEXT DEFAULT ''",
            'specifications': "TEXT DEFAULT ''",
            'warranty': "TEXT DEFAULT ''",
            'cost': "INTEGER CHECK(cost >= 0)",
            'promotional_price': "INTEGER CHECK(promotional_price >= 0)"
        },

        'sales': {
            'discount': "INTEGER DEFAULT 0",
            'coupon': "TEXT DEFAULT ''"
        },

        'items': {
            'cost': "INTEGER"
        }
    }

    for tabela, campos in novas_colunas.items():

        colunas_existentes = [
            coluna['name']
            for coluna in db().execute(
                f"PRAGMA table_info({tabela})"
            )
        ]

        for campo, tipo in campos.items():

            if campo not in colunas_existentes:

                db().execute(
                    f"ALTER TABLE {tabela} ADD COLUMN {campo} {tipo}"
                )

    # Contas iniciais

    for role, name in [
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('cliente', 'Cliente')
    ]:
        db().execute(
            'INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)',
            (
                name,
                role + '@gearflow.com',
                generate_password_hash('123456'),
                role
            )
        )

    # Produtos iniciais

    if not db().execute(
        'SELECT 1 FROM settings WHERE id=1'
    ).fetchone():

        db().executemany(
            'INSERT INTO products(name,category,price,stock) VALUES(?,?,?,?)',
            [
                ('Mouse sem fio', 'Periféricos', 8990, 24),
                ('Teclado mecânico', 'Periféricos', 24990, 12),
                ('Monitor 24 polegadas', 'Monitores', 79990, 4),
                ('Headset Bluetooth', 'Áudio', 15990, 18)
            ]
        )

        db().execute('INSERT INTO settings VALUES(1)')

    db().commit()


# AUTENTICAÇÃO E PERMISSÕES

def user():
    return db().execute(
        'SELECT * FROM users WHERE id=? AND active=1',
        (session.get('uid'),)
    ).fetchone()


def allow(*roles):

    def deco(fn):

        @wraps(fn)
        def wrap(*a, **k):

            u = user()

            if not u or (roles and u['role'] not in roles):
                return jsonify(error='Acesso negado'), 403

            if request.method not in ('GET', 'HEAD'):
                if request.headers.get('X-CSRF') != session.get('csrf'):
                    return jsonify(error='Sessão inválida'), 403

            return fn(u, *a, **k)

        return wrap

    return deco


def rows(sql, args=()):
    return [
        dict(r)
        for r in db().execute(sql, args)
    ]


def data():
    return request.get_json() or {}


def err(msg):
    return jsonify(error=msg), 400


@app.errorhandler(ValueError)
@app.errorhandler(KeyError)
@app.errorhandler(TypeError)
@app.errorhandler(sqlite3.IntegrityError)
def invalid(e):
    return err('Dados inválidos ou registro duplicado.')


# PÁGINA INICIAL

@app.get('/')
def home():

    u = user()

    if u:
        return render_template(
            'app.html',
            u=dict(u),
            csrf=session['csrf']
        )

    return render_template('login.html')


# LOGIN

@app.post('/login')
def login():

    d = data()

    u = db().execute(
        'SELECT * FROM users WHERE email=? AND active=1',
        (d.get('email', '').strip().lower(),)
    ).fetchone()

    if not u or not check_password_hash(
        u['password'],
        d.get('password', '')
    ):
        return err('Credenciais inválidas.')

    session.clear()

    session.update(
        uid=u['id'],
        csrf=secrets.token_hex(24)
    )

    return jsonify(ok=True)


# LOGOUT

@app.post('/api/logout')
@allow()
def logout(u):

    session.clear()

    return jsonify(ok=True)


# UPLOAD DE FOTOS

@app.post('/api/upload')
@allow('admin')
def upload_image(u):

    foto = request.files.get('image')

    if not foto or not foto.filename:
        return err('Selecione uma imagem.')

    extensao = os.path.splitext(foto.filename)[1].lower()

    if extensao not in ('.jpg', '.jpeg', '.png', '.webp'):
        return err('Formato de imagem inválido.')

    if len(foto.read(5 * 1024 * 1024 + 1)) > 5 * 1024 * 1024:
        return err('A imagem deve ter até 5 MB.')

    foto.seek(0)

    nome = secrets.token_hex(16) + extensao

    pasta = os.path.join(
        app.root_path,
        'static',
        'images'
    )

    os.makedirs(pasta, exist_ok=True)

    foto.save(os.path.join(pasta, nome))

    return jsonify(
        image='/static/images/' + nome
    )


# CADASTRO E CONSULTA DE PRODUTOS

def product_data(d):

    name = d['name'].strip()
    category = d['category'].strip()
    price = int(d['price'])

    brand = d.get('brand', '').strip()
    model = d.get('model', '').strip()
    description = d.get('description', '').strip()
    specifications = d.get('specifications', '').strip()
    warranty = d.get('warranty', '').strip()

    cost = d.get('cost')
    promotional_price = d.get('promotional_price')

    cost = int(cost) if cost not in (None, '') else None

    promotional_price = (
        int(promotional_price)
        if promotional_price not in (None, '')
        else None
    )

    if not name or not category or price < 0:
        raise ValueError('Produto inválido.')

    if cost is not None and cost < 0:
        raise ValueError('Custo inválido.')

    if promotional_price is not None:
        if promotional_price < 0 or promotional_price >= price:
            raise ValueError('Preço promocional inválido.')

    return (
        name,
        category,
        price,
        brand,
        model,
        description,
        specifications,
        warranty,
        cost,
        promotional_price
    )


@app.route('/api/products', methods=['GET', 'POST'])
@allow()
def products(u):

    if request.method == 'GET':

        result = rows(
            'SELECT * FROM products WHERE active=1 ORDER BY name'
        )

        for p in result:

            promotional = p['promotional_price']

            p['final_price'] = (
                promotional
                if promotional is not None
                and 0 <= promotional < p['price']
                else p['price']
            )

            p['discount_percent'] = (
                round(
                    (1 - p['final_price'] / p['price']) * 100
                )
                if p['price'] > 0
                else 0
            )

            if u['role'] != 'admin':
                p.pop('cost', None)

        return jsonify(result)

    if u['role'] != 'admin':
        return jsonify(error='Acesso negado'), 403

    d = data()

    values = product_data(d)

    stock = int(d.get('stock', 0))
    image = d.get('image', '')

    if stock < 0:
        return err('Estoque inválido.')

    c = db().execute(
        '''
        INSERT INTO products (
            name,
            category,
            price,
            brand,
            model,
            description,
            specifications,
            warranty,
            cost,
            promotional_price,
            stock,
            image
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        values + (stock, image)
    )

    db().execute(
        '''
        INSERT INTO movements
        (product_id, delta, reason)
        VALUES (?,?,?)
        ''',
        (
            c.lastrowid,
            stock,
            'Cadastro'
        )
    )

    db().commit()

    return jsonify(ok=True)


# EDITAR E EXCLUIR PRODUTOS

@app.route('/api/products/<int:i>', methods=['PUT', 'DELETE'])
@allow('admin')
def product(u, i):

    existing = db().execute(
        'SELECT * FROM products WHERE id=?',
        (i,)
    ).fetchone()

    if not existing:
        return err('Produto não encontrado.')

    if request.method == 'DELETE':

        db().execute(
            'UPDATE products SET active=0 WHERE id=?',
            (i,)
        )

    else:

        d = dict(existing)
        d.update(data())

        values = product_data(d)

        image = d.get('image', '')

        db().execute(
            '''
            UPDATE products SET
                name=?,
                category=?,
                price=?,
                brand=?,
                model=?,
                description=?,
                specifications=?,
                warranty=?,
                cost=?,
                promotional_price=?,
                image=?
            WHERE id=?
            ''',
            values + (image, i)
        )

    db().commit()

    return jsonify(ok=True)


# CONTROLE DE ESTOQUE

@app.route('/api/stock', methods=['GET', 'POST'])
@allow('admin')
def stock(u):

    if request.method == 'GET':

        return jsonify(
            rows(
                '''
                SELECT m.*, p.name
                FROM movements m
                JOIN products p ON p.id=m.product_id
                ORDER BY m.id DESC
                '''
            )
        )

    d = data()

    i = int(d['id'])
    delta = int(d['delta'])

    c = db()

    c.execute('BEGIN IMMEDIATE')

    r = c.execute(
        '''
        UPDATE products
        SET stock=stock+?
        WHERE id=? AND active=1 AND stock+?>=0
        ''',
        (delta, i, delta)
    )

    if not r.rowcount or not delta:

        c.rollback()

        return err(
            'Movimentação inválida ou estoque insuficiente.'
        )

    c.execute(
        '''
        INSERT INTO movements
        (product_id,delta,reason)
        VALUES (?,?,?)
        ''',
        (
            i,
            delta,
            d.get('reason', 'Ajuste')
        )
    )

    c.commit()

    return jsonify(ok=True)


# GERENCIAMENTO DE USUÁRIOS

@app.route('/api/users', methods=['GET', 'POST'])
@allow('admin')
def users(u):

    if request.method == 'GET':

        return jsonify(
            rows(
                'SELECT id,name,email,role,active FROM users'
            )
        )

    d = data()

    role = d['role']
    pw = d['password']
    name = d['name'].strip()
    email = d['email'].strip().lower()

    if (
        role not in ('admin', 'vendedor', 'cliente')
        or len(pw) < 6
        or not name
        or '@' not in email
    ):
        return err('Dados inválidos.')

    db().execute(
        '''
        INSERT INTO users
        (name,email,password,role)
        VALUES (?,?,?,?)
        ''',
        (
            name,
            email,
            generate_password_hash(pw),
            role
        )
    )

    db().commit()

    return jsonify(ok=True)


# EDITAR USUÁRIOS

@app.put('/api/users/<int:i>')
@allow('admin')
def edit_user(u, i):

    d = data()

    role = d['role']
    active = int(d['active'])
    name = d['name'].strip()
    email = d['email'].strip().lower()

    if (
        i == u['id']
        or role not in ('admin', 'vendedor', 'cliente')
        or active not in (0, 1)
        or not name
        or '@' not in email
    ):
        return err(
            'Alteração inválida (sua própria conta está protegida).'
        )

    db().execute(
        '''
        UPDATE users
        SET name=?,email=?,role=?,active=?
        WHERE id=?
        ''',
        (
            name,
            email,
            role,
            active,
            i
        )
    )

    db().commit()

    return jsonify(ok=True)


# PERFIL DO USUÁRIO

@app.route('/api/profile', methods=['GET', 'PUT'])
@allow()
def profile(u):

    if request.method == 'GET':

        return jsonify({
            k: u[k]
            for k in ('name', 'email', 'address', 'role')
        })

    d = data()

    name = d['name'].strip()
    email = d['email'].strip().lower()
    pw = d.get('password', '')

    if (
        not name
        or '@' not in email
        or (
            pw and (
                len(pw) < 6
                or not check_password_hash(
                    u['password'],
                    d.get('current', '')
                )
            )
        )
    ):
        return err('Dados ou senha atual inválidos.')

    db().execute(
        '''
        UPDATE users
        SET name=?,email=?,address=?,password=?
        WHERE id=?
        ''',
        (
            name,
            email,
            d.get('address', ''),
            generate_password_hash(pw) if pw else u['password'],
            u['id']
        )
    )

    db().commit()

    return jsonify(ok=True)
# GERENCIAMENTO DE CUPONS

@app.route('/api/coupons', methods=['GET', 'POST'])
@allow('admin')
def coupons(u):

    if request.method == 'GET':
        return jsonify(
            rows('SELECT * FROM coupons ORDER BY id DESC')
        )

    d = data()

    code = d.get('code', '').strip().upper()
    tipo = d.get('type', 'percent')
    discount = int(d.get('discount', 0))
    min_purchase = int(d.get('min_purchase', 0))
    max_uses = d.get('max_uses')
    expires = d.get('expires') or None

    max_uses = (
        int(max_uses)
        if max_uses not in (None, '')
        else None
    )

    if not code or len(code) > 40:
        return err('Código do cupom inválido.')

    if tipo not in ('percent', 'fixed'):
        return err('Tipo de desconto inválido.')

    if discount <= 0:
        return err('Informe um desconto válido.')

    if tipo == 'percent' and discount > 100:
        return err('O desconto não pode superar 100%.')

    if min_purchase < 0:
        return err('Valor mínimo inválido.')

    if max_uses is not None and max_uses <= 0:
        return err('Limite de utilizações inválido.')

    if expires:
        from datetime import date
        try:
            expires = date.fromisoformat(expires).isoformat()
        except ValueError:
            return err('Data de validade inválida.')

    c = db()
    c.execute('BEGIN IMMEDIATE')

    existing = c.execute(
        'SELECT id FROM coupons WHERE UPPER(code)=?',
        (code,)
    ).fetchone()

    if existing:
        c.rollback()
        return err('Este cupom já existe.')

    c.execute(
        '''
        INSERT INTO coupons
        (
            code, type, discount,
            min_purchase, max_uses,
            expires, active, uses, created
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, 0, CURRENT_TIMESTAMP)
        ''',
        (
            code, tipo, discount,
            min_purchase, max_uses, expires
        )
    )

    c.commit()

    return jsonify(ok=True), 201
# EDITAR E EXCLUIR CUPONS

@app.route('/api/coupons/<int:i>', methods=['PUT', 'DELETE'])
@allow('admin')
def edit_coupon(u, i):

    c = db()

    c.execute('BEGIN IMMEDIATE')

    existing = c.execute(
        'SELECT * FROM coupons WHERE id=?',
        (i,)
    ).fetchone()

    if not existing:
        c.rollback()
        return err('Cupom não encontrado.')

    if request.method == 'DELETE':

        c.execute(
            'UPDATE coupons SET active=0 WHERE id=?',
            (i,)
        )

        c.commit()

        return jsonify(ok=True)

    d = dict(existing)
    d.update(data())

    code = d['code'].strip().upper()
    tipo = d['type']
    discount = int(d['discount'])
    min_purchase = int(d['min_purchase'])
    active = int(d['active'])
    expires = d.get('expires') or None

    max_uses = d.get('max_uses')

    max_uses = (
        int(max_uses)
        if max_uses not in (None, '')
        else None
    )

    if (
        not code
        or len(code) > 40
        or tipo not in ('percent', 'fixed')
        or discount <= 0
        or min_purchase < 0
        or active not in (0, 1)
    ):
        c.rollback()
        return err('Dados do cupom inválidos.')

    if tipo == 'percent' and discount > 100:
        c.rollback()
        return err('Desconto máximo de 100%.')

    if max_uses is not None and (
        max_uses <= 0
        or max_uses < (existing['uses'] or 0)
    ):
        c.rollback()
        return err('Limite de utilizações inválido.')

    if expires:
        from datetime import date

        try:
            expires = date.fromisoformat(expires).isoformat()
        except ValueError:
            c.rollback()
            return err('Data de validade inválida.')

    duplicate = c.execute(
        'SELECT id FROM coupons WHERE UPPER(code)=? AND id!=?',
        (code, i)
    ).fetchone()

    if duplicate:
        c.rollback()
        return err('Este código já está cadastrado.')

    c.execute(
        '''
        UPDATE coupons SET
            code=?,
            type=?,
            discount=?,
            min_purchase=?,
            max_uses=?,
            expires=?,
            active=?
        WHERE id=?
        ''',
        (
            code,
            tipo,
            discount,
            min_purchase,
            max_uses,
            expires,
            active,
            i
        )
    )

    c.commit()

    return jsonify(ok=True)
# VALIDAÇÃO DE CUPONS

def find_coupon(code):

    coupon = db().execute(
        '''
        SELECT * FROM coupons
        WHERE UPPER(code)=?
        AND active=1
        AND discount > 0
        AND (
            type='fixed'
            OR (type='percent' AND discount <= 100)
        )
        AND (
            max_uses IS NULL
            OR COALESCE(uses, 0) < max_uses
        )
        AND (
            expires IS NULL
            OR expires=''
            OR DATE(expires) >= DATE('now', 'localtime')
        )
        ''',
        (code.strip().upper(),)
    ).fetchone()

    return coupon
# APLICAR CUPOM NO CHECKOUT

@app.post('/api/coupons/validate')
@allow()
def validate_coupon(u):

    d = data()

    code = d.get('code', '').strip().upper()
    subtotal = int(d.get('subtotal', 0))

    if not code:
        return err('Informe o código do cupom.')

    if subtotal <= 0:
        return err('O carrinho está vazio.')

    coupon = find_coupon(code)

    if not coupon:
        return err('Cupom inválido, expirado ou indisponível.')

    if subtotal < coupon['min_purchase']:

        minimo = coupon['min_purchase'] / 100

        return err(
            f'Compra mínima de R$ {minimo:.2f}.'
        )

    if coupon['type'] == 'percent':

        discount = (
            subtotal * coupon['discount'] + 50
        ) // 100

    else:

        discount = coupon['discount']

    discount = min(discount, subtotal)

    return jsonify(
        ok=True,
        code=coupon['code'],
        type=coupon['type'],
        discount=discount,
        subtotal=subtotal,
        total=subtotal - discount
    )
# VENDAS E PEDIDOS

@app.route('/api/sales', methods=['GET', 'POST'])
@allow()
def sales(u):

    c = db()

    if request.method == 'GET':

        q = '''
        SELECT s.*, u.name AS buyer
        FROM sales s
        JOIN users u ON u.id = s.user_id
        '''

        a = ()

        if u['role'] != 'admin':
            q += ' WHERE s.user_id=?'
            a = (u['id'],)

        result = rows(
            q + ' ORDER BY s.id DESC',
            a
        )

        for s in result:

            s['items'] = rows(
                '''
                SELECT name, qty, price
                FROM items
                WHERE sale_id=?
                ''',
                (s['id'],)
            )

        return jsonify(result)

    d = data()

    method = d.get('method', '')
    address = d.get('address', '').strip()
    items = d.get('items', [])
    installments = int(d.get('installments', 1))
    coupon_code = d.get('coupon', '').strip().upper()

    if method not in (
        'Pix',
        'Dinheiro',
        'Crédito',
        'Débito',
        'Boleto'
    ):
        return err('Forma de pagamento inválida.')

    if not items:
        return err('O carrinho está vazio.')

    if not 1 <= installments <= 12:
        return err('Parcelamento inválido.')

    if method != 'Crédito':
        installments = 1

    if u['role'] == 'cliente' and not address:
        return err('Informe o endereço de entrega.')

    c.execute('BEGIN IMMEDIATE')

    subtotal = 0
    selected = []
    discount = 0

    coupon = None

    if coupon_code:

        coupon = find_coupon(coupon_code)

        if not coupon:
            c.rollback()
            return err('Cupom inválido ou expirado.')

    for item in items:

        i = int(item['id'])
        qty = int(item['qty'])

        p = c.execute(
            '''
            SELECT * FROM products
            WHERE id=? AND active=1
            ''',
            (i,)
        ).fetchone()

        if not p or qty <= 0 or p['stock'] < qty:

            c.rollback()

            return err('Estoque insuficiente.')

        price = final_price(p)

        subtotal += price * qty

        selected.append(
            (
                i,
                p['name'],
                qty,
                price,
                p['cost']
            )
        )

        c.execute(
            '''
            UPDATE products
            SET stock=stock-?
            WHERE id=?
            ''',
            (qty, i)
        )

    if coupon:

        if subtotal < coupon['min_purchase']:

            c.rollback()

            minimo = coupon['min_purchase'] / 100

            return err(
                f'Este cupom exige uma compra mínima de R$ {minimo:.2f}.'
            )

        if coupon['type'] == 'percent':

            discount = (
                subtotal * coupon['discount'] + 50
            ) // 100

        elif coupon['type'] == 'fixed':

            discount = coupon['discount']

        discount = min(discount, subtotal)

    total = subtotal - discount

    status = (
        'Pendente'
        if u['role'] == 'cliente'
        else 'Concluído'
    )

    sid = c.execute(
        '''
        INSERT INTO sales (
            user_id,
            total,
            method,
            address,
            status,
            installments,
            discount,
            coupon
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            u['id'],
            total,
            method,
            address,
            status,
            installments,
            discount,
            coupon_code
        )
    ).lastrowid

    for i, name, qty, price, cost in selected:

        c.execute(
            '''
            INSERT INTO items (
                sale_id,
                product_id,
                name,
                qty,
                price,
                cost
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                sid,
                i,
                name,
                qty,
                price,
                cost
            )
        )

        c.execute(
            '''
            INSERT INTO movements (
                product_id,
                delta,
                reason
            )
            VALUES (?, ?, ?)
            ''',
            (
                i,
                -qty,
                'Venda #' + str(sid)
            )
        )

    if coupon:

        c.execute(
            '''
            UPDATE coupons
            SET uses=uses+1
            WHERE id=?
            ''',
            (coupon['id'],)
        )

    c.commit()

    return jsonify(
        ok=True,
        id=sid,
        subtotal=subtotal,
        discount=discount,
        total=total,
        method=method,
        installments=installments,
        status=status
    )

# ALTERAR STATUS DOS PEDIDOS

@app.put('/api/sales/<int:i>')
@allow('admin')
def sale_status(u, i):

    c = db()

    c.execute('BEGIN IMMEDIATE')

    s = c.execute(
        'SELECT * FROM sales WHERE id=?',
        (i,)
    ).fetchone()

    status = data()['status']

    if (
        not s
        or s['status'] == 'Cancelado'
        or status not in ('Cancelado', 'Concluído', 'Enviado')
    ):

        c.rollback()

        return err('Status inválido.')

    if status == 'Cancelado':

        for item in c.execute(
            'SELECT * FROM items WHERE sale_id=?',
            (i,)
        ).fetchall():

            c.execute(
                'UPDATE products SET stock=stock+? WHERE id=?',
                (
                    item['qty'],
                    item['product_id']
                )
            )

            c.execute(
                '''
                INSERT INTO movements
                (product_id,delta,reason)
                VALUES (?,?,?)
                ''',
                (
                    item['product_id'],
                    item['qty'],
                    'Cancelamento #' + str(i)
                )
            )

    c.execute(
        'UPDATE sales SET status=? WHERE id=?',
        (status, i)
    )

    c.commit()

    return jsonify(ok=True)


# RELATÓRIOS E DASHBOARD FINANCEIRO

@app.get('/api/reports')
@allow('admin')
def reports(u):

    c = db()

    customers = c.execute(
        "SELECT COUNT(*) FROM users WHERE role='cliente'"
    ).fetchone()[0]

    best = rows(
        """
        SELECT i.name, SUM(i.qty) AS qty
        FROM items i
        JOIN sales s ON s.id = i.sale_id
        WHERE s.status IN ('Concluído', 'Enviado')
        GROUP BY i.name
        ORDER BY qty DESC
        """
    )

    financial = rows(
        """
        SELECT
            s.id,
            s.total,
            s.discount,
            s.created,

            CASE
                WHEN COUNT(i.product_id) = 0
                OR COUNT(i.cost) < COUNT(*)
                THEN NULL

                ELSE SUM(i.cost * i.qty)
            END AS cost

        FROM sales s

        LEFT JOIN items i
        ON i.sale_id = s.id

        WHERE s.status IN ('Concluído', 'Enviado')

        GROUP BY s.id

        ORDER BY s.created
        """
    )

    revenue = 0
    total_cost = 0
    profit = 0
    discounts = 0
    unknown_cost = 0
    known_revenue = 0

    monthly = {}

    for sale in financial:

        total = sale['total'] or 0
        cost = sale['cost']
        month = sale['created'][:7]

        revenue += total
        discounts += sale['discount'] or 0

        if month not in monthly:

            monthly[month] = {
                'month': month,
                'revenue': 0,
                'cost': 0,
                'profit': 0,
                'sales': 0,
                'unknown_cost': 0
            }

        monthly[month]['revenue'] += total
        monthly[month]['sales'] += 1

        if cost is None:

            unknown_cost += 1
            monthly[month]['unknown_cost'] += 1

        else:

            sale_profit = total - cost

            known_revenue += total
            total_cost += cost
            profit += sale_profit

            monthly[month]['cost'] += cost
            monthly[month]['profit'] += sale_profit

    total_sales = len(financial)

    average_ticket = (
        round(revenue / total_sales)
        if total_sales else 0
    )

    margin = (
        round(profit / known_revenue * 100, 2)
        if known_revenue else 0
    )

    low_stock = c.execute(
        """
        SELECT COUNT(*)
        FROM products
        WHERE active=1 AND stock <= 5
        """
    ).fetchone()[0]

    pending_orders = c.execute(
        """
        SELECT COUNT(*)
        FROM sales
        WHERE status='Pendente'
        """
    ).fetchone()[0]

    return jsonify(
        customers=customers,
        best=best,
        revenue=revenue,
        total_cost=total_cost,
        profit=profit,
        discounts=discounts,
        total_sales=total_sales,
        average_ticket=average_ticket,
        margin=margin,
        low_stock=low_stock,
        pending_orders=pending_orders,
        unknown_cost=unknown_cost,
        monthly=list(monthly.values())
    )

# PÁGINA DE CADASTRO

@app.get('/cadastro')
def cadastro():

    return render_template('cadastro.html')


# CADASTRO DE CLIENTES E VENDEDORES

@app.post('/api/register')
def register():

    d = request.get_json() or {}

    name = d.get('name', '').strip()
    email = d.get('email', '').strip().lower()
    password = d.get('password', '')
    role = d.get('role', '')
    cpf = d.get('cpf', '').strip()
    phone = d.get('phone', '').strip()

    if role not in ('cliente', 'vendedor'):
        return jsonify(
            error='Tipo de conta inválido.'
        ), 400

    if not name or '@' not in email or len(password) < 6:
        return jsonify(
            error='Preencha os campos corretamente.'
        ), 400

    if not cpf or not phone:
        return jsonify(
            error='Informe o CPF e o telefone.'
        ), 400

    existing = db().execute(
        'SELECT id FROM users WHERE email=?',
        (email,)
    ).fetchone()

    if existing:
        return jsonify(
            error='Este e-mail já está cadastrado.'
        ), 400

    active = 1 if role == 'cliente' else 0

    db().execute(
        '''
        INSERT INTO users
        (name,email,password,role,active,cpf,phone)
        VALUES (?,?,?,?,?,?,?)
        ''',
        (
            name,
            email,
            generate_password_hash(password),
            role,
            active,
            cpf,
            phone
        )
    )

    db().commit()

    return jsonify(ok=True), 201


# INICIAR O SERVIDOR

if __name__ == '__main__':
    app.run(port=5001)