async function submitJson(form, url) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.fromEntries(new FormData(form)))
  });
  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || 'Não foi possível concluir a solicitação.');
  }

  return result;
}

function showFormMessage(element, message, isError = false) {
  element.textContent = message;
  element.className = `feedback ${isError ? 'error' : 'ok'}`;
}

document.getElementById('loginForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const message = document.getElementById('loginMsg');
  button.disabled = true;
  message.textContent = '';

  try {
    await submitJson(form, '/login');
    window.location.assign('/');
  } catch (error) {
    showFormMessage(message, error.message, true);
  } finally {
    button.disabled = false;
  }
});

document.getElementById('registerForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const message = document.getElementById('registerMsg');
  const role = new FormData(form).get('role');
  button.disabled = true;
  message.textContent = '';

  try {
    await submitJson(form, '/api/register');
    form.reset();
    const successMessage = role === 'vendedor'
      ? 'Cadastro enviado. O acesso de vendedor depende de aprovação do administrador.'
      : 'Cadastro realizado. Você já pode entrar com seu e-mail e senha.';
    showFormMessage(message, successMessage);
  } catch (error) {
    showFormMessage(message, error.message, true);
  } finally {
    button.disabled = false;
  }
});
