import sqlite3
from pathlib import Path

banco = Path(__file__).resolve().parent / 'gearflow.db'

if not banco.is_file():
    raise FileNotFoundError('Banco de dados não encontrado.')

c = sqlite3.connect(banco)

try:
    c.execute('BEGIN IMMEDIATE')

    c.execute('ALTER TABLE coupons RENAME TO coupons_antiga')

    c.execute('''
        CREATE TABLE coupons (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            type TEXT NOT NULL DEFAULT 'percent'
                CHECK(type IN ('percent', 'fixed')),
            discount INTEGER NOT NULL CHECK(discount > 0),
            min_purchase INTEGER NOT NULL DEFAULT 0
                CHECK(min_purchase >= 0),
            expires TEXT,
            max_uses INTEGER DEFAULT 100
                CHECK(max_uses > 0),
            uses INTEGER NOT NULL DEFAULT 0
                CHECK(uses >= 0),
            active INTEGER NOT NULL DEFAULT 1
                CHECK(active IN (0, 1)),
            created TEXT DEFAULT CURRENT_TIMESTAMP,
            CHECK(type != 'percent' OR discount <= 100)
        )
    ''')

    c.execute('''
        INSERT INTO coupons (
            id, code, type, discount,
            min_purchase, expires, max_uses,
            uses, active, created
        )
        SELECT
            id, code, type, discount,
            min_purchase, expires, max_uses,
            COALESCE(uses, 0),
            COALESCE(active, 1),
            COALESCE(created, CURRENT_TIMESTAMP)
        FROM coupons_antiga
    ''')

    c.execute('DROP TABLE coupons_antiga')

    c.commit()

    print('Migração realizada com sucesso!')

except Exception as erro:

    c.rollback()

    print('Erro na migração:', erro)

finally:

    c.close()