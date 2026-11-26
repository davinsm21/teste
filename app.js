const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
let productsCache = [];
let cart = [];
let appliedCoupon = null;

function formatBRL(cents) {
  return ((cents || 0) / 100).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  });
}

function showFeedback(text, isError = false) {
  const el = document.getElementById('appFeedback');
  if (!el) return;
  el.textContent = text;
  el.className = `feedback ${isError ? 'error' : 'ok'}`;
}

async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.method && options.method !== 'GET' && options.method !== 'HEAD') {
    headers['X-CSRF'] = csrfToken;
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
  }
  const res = await fetch(url, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || 'Erro na requisição.');
  }
  return data;
}

// Navegação entre abas
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`)?.classList.add('active');
    if (btn.dataset.tab === 'sales') loadSales();
  });
});

document.getElementById('logoutBtn')?.addEventListener('click', async () => {
  await apiFetch('/api/logout', { method: 'POST' });
  window.location.href = '/';
});

// Catálogo
async function loadProducts() {
  productsCache = await apiFetch('/api/products');
  renderCatalog();
}

function renderCatalog() {
  const grid = document.getElementById('catalogGrid');
  const query = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();

  const filtered = productsCache.filter((p) =>
    p.name.toLowerCase().includes(query) || p.category.toLowerCase().includes(query)
  );

  if (!filtered.length) {
    grid.innerHTML = '<p class="muted">Nenhum produto encontrado.</p>';
    return;
  }

  grid.innerHTML = filtered
    .map((p) => {
      const hasPromo = p.final_price < p.price;
      return `
        <article class="card">
          <small class="muted">${p.category} • Estoque: ${p.stock}</small>
          <h3>${p.name}</h3>
          <p class="muted">${p.description || ''}</p>
          <div class="price">
            ${hasPromo ? `<span class="old-price">${formatBRL(p.price)}</span>` : ''}
            ${formatBRL(p.final_price)}
          </div>
          <button
            type="button"
            class="btn primary"
            ${p.stock <= 0 ? 'disabled' : ''}
            onclick="addToCart(${p.id})"
          >
            ${p.stock > 0 ? 'Adicionar ao carrinho' : 'Sem estoque'}
          </button>
        </article>
      `;
    })
    .join('');
}

document.getElementById('searchInput')?.addEventListener('input', renderCatalog);

// Carrinho e checkout
window.addToCart = function addToCart(productId) {
  const prod = productsCache.find((p) => p.id === productId);
  if (!prod || prod.stock <= 0) return;

  const existing = cart.find((item) => item.id === productId);
  if (existing) {
    if (existing.qty >= prod.stock) {
      showFeedback('Quantidade máxima em estoque atingida.', true);
      return;
    }
    existing.qty += 1;
  } else {
    cart.push({ id: prod.id, name: prod.name, price: prod.final_price, qty: 1 });
  }

  appliedCoupon = null;
  renderCart();
  showFeedback(`${prod.name} adicionado ao carrinho.`);
};

function getSubtotal() {
  return cart.reduce((sum, item) => sum + item.price * item.qty, 0);
}

function renderCart() {
  const container = document.getElementById('cartItems');
  const countEl = document.getElementById('cartCount');
  countEl.textContent = String(cart.reduce((sum, item) => sum + item.qty, 0));

  if (!cart.length) {
    container.innerHTML = '<p class="muted">Seu carrinho está vazio.</p>';
  } else {
    container.innerHTML = cart
      .map(
        (item) => `
          <div class="cart-item">
            <div>
              <strong>${item.name}</strong>
              <div class="muted">${item.qty}x ${formatBRL(item.price)}</div>
            </div>
            <strong>${formatBRL(item.price * item.qty)}</strong>
          </div>
        `
      )
      .join('');
  }

  const subtotal = getSubtotal();
  const discount = appliedCoupon ? Math.min(appliedCoupon.discount, subtotal) : 0;
  const total = Math.max(0, subtotal - discount);

  document.getElementById('subtotalText').textContent = formatBRL(subtotal);
  document.getElementById('discountText').textContent = formatBRL(discount);
  document.getElementById('totalText').textContent = formatBRL(total);
}

document.getElementById('applyCouponBtn')?.addEventListener('click', async () => {
  const code = document.getElementById('couponCode').value.trim();
  const subtotal = getSubtotal();
  try {
    const data = await apiFetch('/api/coupons/validate', {
      method: 'POST',
      body: JSON.stringify({ code, subtotal })
    });
    appliedCoupon = data;
    renderCart();
    showFeedback(`Cupom ${data.code} aplicado!`);
  } catch (err) {
    appliedCoupon = null;
    renderCart();
    showFeedback(err.message, true);
  }
});

document.getElementById('payMethod')?.addEventListener('change', (e) => {
  const wrap = document.getElementById('installmentsWrap');
  wrap.classList.toggle('hidden', e.target.value !== 'Crédito');
});

document.getElementById('checkoutForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const res = await apiFetch('/api/sales', {
      method: 'POST',
      body: JSON.stringify({
        method: document.getElementById('payMethod').value,
        installments: Number(document.getElementById('installments').value || 1),
        address: document.getElementById('deliveryAddress').value.trim(),
        coupon: appliedCoupon ? appliedCoupon.code : '',
        items: cart.map(({ id, qty }) => ({ id, qty }))
      })
    });

    cart = [];
    appliedCoupon = null;
    document.getElementById('couponCode').value = '';
    renderCart();
    await loadProducts();
    showFeedback(`Pedido #${res.id} registrado (${res.status}).`);
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// Pedidos
async function loadSales() {
  const list = document.getElementById('salesList');
  try {
    const sales = await apiFetch('/api/sales');
    if (!sales.length) {
      list.innerHTML = '<p class="muted">Nenhum pedido registrado.</p>';
      return;
    }
    list.innerHTML = sales
      .map(
        (s) => `
          <div class="card">
            <strong>Pedido #${s.id}</strong> • ${s.status} • ${s.method}
            <div class="muted">Comprador: ${s.buyer} • Total: ${formatBRL(s.total)}</div>
          </div>
        `
      )
      .join('');
  } catch (err) {
    list.innerHTML = `<p class="feedback error">${err.message}</p>`;
  }
}

// Cadastro de produto (admin)
document.getElementById('createProductForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  try {
    await apiFetch('/api/products', {
      method: 'POST',
      body: JSON.stringify({
        name: formData.get('name'),
        category: formData.get('category'),
        price: Number(formData.get('price')),
        stock: Number(formData.get('stock')),
        description: formData.get('description')
      })
    });
    e.target.reset();
    await loadProducts();
    showFeedback('Produto cadastrado com sucesso!');
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// Inicialização
loadProducts();
renderCart();