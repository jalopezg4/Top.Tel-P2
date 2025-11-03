from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secretkey-for-frontend')

# URLs de los microservicios
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:5000')
CATALOG_SERVICE_URL = os.getenv('CATALOG_SERVICE_URL', 'http://catalog_service:5000')
STORE_SERVICE_URL = os.getenv('STORE_SERVICE_URL', 'http://store_service:5000')

# Simulación de flask-login con sesiones
def get_current_user():
    """Retorna el usuario actual de la sesión o None"""
    return session.get('user')

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Debes iniciar sesión primero')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== HOME ====================
@app.route('/')
def home():
    return render_template('home.html')

# ==================== AUTH ROUTES ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            response = requests.post(
                f'{AUTH_SERVICE_URL}/login',
                json={'username': email, 'password': password},
                timeout=5
            )
            
            if response.status_code == 200:
                user_data = response.json().get('user', {})
                # Simular estructura de usuario del monolito
                session['user'] = {
                    'id': user_data.get('id'),
                    'username': user_data.get('username'),
                    'email': email,
                    'name': user_data.get('name') or user_data.get('username')  # Usar name si existe, sino username
                }
                flash('Inicio de sesión exitoso')
                return redirect(url_for('catalog'))
            else:
                flash('Login failed')
        except requests.exceptions.RequestException as e:
            flash(f'Error de conexión con el servicio de autenticación')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            response = requests.post(
                f'{AUTH_SERVICE_URL}/register',
                json={'username': email, 'password': password, 'name': name},
                timeout=5
            )
            
            if response.status_code == 201:
                flash('Registro exitoso. Por favor inicia sesión.')
                return redirect(url_for('login'))
            else:
                flash('Error al registrar usuario')
        except requests.exceptions.RequestException as e:
            flash(f'Error de conexión con el servicio de autenticación')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ==================== BOOK ROUTES ====================
@app.route('/book/catalog')
def catalog():
    try:
        response = requests.get(f'{CATALOG_SERVICE_URL}/books', timeout=5)
        if response.status_code == 200:
            books = response.json()
        else:
            books = []
            flash('Error al obtener el catálogo')
    except requests.exceptions.RequestException as e:
        books = []
        flash(f'Error de conexión con el servicio de catálogo')
    
    return render_template('catalog.html', books=books)

@app.route('/book/my_books')
@login_required
def my_books():
    try:
        # Obtener todos los libros del store service
        response = requests.get(f'{STORE_SERVICE_URL}/books', timeout=5)
        if response.status_code == 200:
            all_books = response.json()
            # Filtrar solo los libros del usuario actual (por seller_id)
            user_id = session.get('user', {}).get('id')
            books = [book for book in all_books if book.get('seller_id') == user_id]
        else:
            books = []
            flash('Error al obtener tus libros')
    except requests.exceptions.RequestException as e:
        books = []
        flash(f'Error de conexión')
    
    return render_template('my_books.html', books=books)

@app.route('/book/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        user_id = session.get('user', {}).get('id')
        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'description': request.form.get('description'),
            'price': float(request.form.get('price')),
            'stock': int(request.form.get('stock')),
            'seller_id': user_id
        }
        
        try:
            response = requests.post(
                f'{STORE_SERVICE_URL}/books',
                json=book_data,
                timeout=5
            )
            
            if response.status_code == 201:
                return redirect(url_for('catalog'))
            else:
                flash('Error al agregar el libro')
        except requests.exceptions.RequestException as e:
            flash(f'Error de conexión')
    
    return render_template('add_book.html')

@app.route('/book/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    user_id = session.get('user', {}).get('id')
    
    if request.method == 'POST':
        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'description': request.form.get('description'),
            'price': float(request.form.get('price')),
            'stock': int(request.form.get('stock')),
            'seller_id': user_id
        }
        
        try:
            # Primero verificar que el libro pertenezca al usuario
            get_response = requests.get(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
            if get_response.status_code == 200:
                book = get_response.json()
                if book.get('seller_id') != user_id:
                    return "No tienes permiso para editar este libro.", 403
                
                # Actualizar el libro
                response = requests.put(
                    f'{STORE_SERVICE_URL}/books/{book_id}',
                    json=book_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    return redirect(url_for('catalog'))
                else:
                    flash('Error al actualizar el libro')
        except requests.exceptions.RequestException as e:
            flash(f'Error de conexión')
    
    # GET: Obtener datos del libro
    try:
        response = requests.get(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
        if response.status_code == 200:
            book = response.json()
            if book.get('seller_id') != user_id:
                return "No tienes permiso para editar este libro.", 403
        else:
            flash('Libro no encontrado')
            return redirect(url_for('my_books'))
    except requests.exceptions.RequestException as e:
        flash(f'Error de conexión')
        return redirect(url_for('my_books'))
    
    return render_template('edit_book.html', book=book)

@app.route('/book/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    user_id = session.get('user', {}).get('id')
    
    try:
        # Primero verificar que el libro pertenezca al usuario
        get_response = requests.get(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
        if get_response.status_code == 200:
            book = get_response.json()
            if book.get('seller_id') != user_id:
                return "No tienes permiso para eliminar este libro.", 403
            
            # Eliminar el libro
            response = requests.delete(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
            if response.status_code in [200, 204]:
                flash('Libro eliminado exitosamente')
            else:
                flash('Error al eliminar el libro')
    except requests.exceptions.RequestException as e:
        flash(f'Error de conexión')
    
    return redirect(url_for('catalog'))

# ==================== PURCHASE ROUTES ====================
@app.route('/buy/<int:book_id>', methods=['POST'])
@login_required
def buy(book_id):
    quantity = int(request.form.get('quantity'))
    price = float(request.form.get('price'))
    user_id = session.get('user', {}).get('id')
    
    try:
        # Obtener información del libro
        book_response = requests.get(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
        if book_response.status_code != 200:
            flash('Libro no encontrado')
            return redirect(url_for('catalog'))
        
        book = book_response.json()
        
        if book.get('stock', 0) < quantity:
            flash('No hay suficiente stock disponible')
            return redirect(url_for('catalog'))
        
        # Calcular precio total
        total_price = price * quantity
        
        # Crear compra (esto se implementaría en un servicio de compras)
        # Por ahora solo reducimos el stock
        updated_stock = book.get('stock') - quantity
        update_data = {
            'title': book.get('title'),
            'author': book.get('author'),
            'description': book.get('description'),
            'price': book.get('price'),
            'stock': updated_stock,
            'seller_id': book.get('seller_id')
        }
        
        update_response = requests.put(
            f'{STORE_SERVICE_URL}/books/{book_id}',
            json=update_data,
            timeout=5
        )
        
        if update_response.status_code == 200:
            flash(f'Compra realizada exitosamente. Total: ${total_price:.2f}')
            # Aquí se redirigiría a payment_page, pero por ahora volvemos al catálogo
            return redirect(url_for('catalog'))
        else:
            flash('Error al procesar la compra')
    except requests.exceptions.RequestException as e:
        flash(f'Error de conexión')
    
    return redirect(url_for('catalog'))

# ==================== PAYMENT ROUTES ====================
@app.route('/payment/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def payment_page(purchase_id):
    if request.method == 'POST':
        method = request.form.get('method')
        flash(f'Pago procesado con {method}')
        return redirect(url_for('catalog'))
    
    return render_template('payment.html')

# ==================== DELIVERY ROUTES ====================
@app.route('/delivery/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def select_delivery(purchase_id):
    if request.method == 'POST':
        provider_id = request.form.get('provider')
        flash(f'Entrega seleccionada para la compra {purchase_id}')
        return redirect(url_for('catalog'))
    
    # Mock de proveedores (en el monolito viene de la BD)
    providers = [
        {'id': 1, 'name': 'DHL', 'coverage_area': 'Internacional', 'cost': 50.0},
        {'id': 2, 'name': 'FedEx', 'coverage_area': 'Internacional', 'cost': 45.0},
        {'id': 3, 'name': 'Envia', 'coverage_area': 'Nacional', 'cost': 20.0},
        {'id': 4, 'name': 'Servientrega', 'coverage_area': 'Nacional', 'cost': 15.0},
    ]
    
    return render_template('delivery_options.html', providers=providers, purchase_id=purchase_id)

# ==================== ADMIN ROUTES ====================
@app.route('/admin/users')
@login_required
def list_users():
    try:
        response = requests.get(f'{AUTH_SERVICE_URL}/users', timeout=5)
        if response.status_code == 200:
            users_data = response.json()
            # Ahora el auth_service ya retorna name, username y id
            users = []
            for user in users_data:
                users.append({
                    'id': user['id'],
                    'name': user.get('name') or user['username'],  # Usar name si existe, sino username
                    'email': user['username']  # username es el email
                })
            return render_template('list_users.html', users=users)
        else:
            flash('Error al obtener la lista de usuarios')
            return render_template('list_users.html', users=[])
    except Exception as e:
        print(f"Error getting users: {e}")
        flash('Error de conexión con el servicio de autenticación')
        return render_template('list_users.html', users=[])

# ==================== HEALTH CHECK ====================
@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Verificar conectividad con servicios
        auth_status = requests.get(f'{AUTH_SERVICE_URL}/', timeout=2).status_code == 200
        catalog_status = requests.get(f'{CATALOG_SERVICE_URL}/', timeout=2).status_code == 200
        store_status = requests.get(f'{STORE_SERVICE_URL}/', timeout=2).status_code == 200
        
        return {
            'status': 'healthy' if all([auth_status, catalog_status, store_status]) else 'degraded',
            'services': {
                'auth': 'up' if auth_status else 'down',
                'catalog': 'up' if catalog_status else 'down',
                'store': 'up' if store_status else 'down'
            }
        }, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 503

# Context processor para hacer current_user disponible en templates
@app.context_processor
def inject_user():
    user = get_current_user()
    # Crear objeto simulado que tenga is_authenticated
    class CurrentUser:
        def __init__(self, user_data):
            self._data = user_data or {}
            
        @property
        def is_authenticated(self):
            return self._data is not None and bool(self._data)
        
        @property
        def name(self):
            return self._data.get('name', '') if self._data else ''
        
        @property
        def id(self):
            return self._data.get('id') if self._data else None
    
    return dict(current_user=CurrentUser(user))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
