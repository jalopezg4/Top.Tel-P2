from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secretkey-for-frontend')

# URLs de los microservicios
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:5001')
CATALOG_SERVICE_URL = os.getenv('CATALOG_SERVICE_URL', 'http://catalog_service:5002')
STORE_SERVICE_URL = os.getenv('STORE_SERVICE_URL', 'http://store_service:5003')

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
                session['user'] = {
                    'id': user_data.get('id'),
                    'username': user_data.get('username'),
                    'email': email,
                    'name': user_data.get('username')
                }
                flash('Inicio de sesión exitoso')
                return redirect(url_for('catalog'))
            else:
                flash('Credenciales inválidas')
        except requests.exceptions.RequestException as e:
            flash('Error de conexión con el servicio de autenticación')
    
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
                json={'username': email, 'password': password},
                timeout=5
            )
            
            if response.status_code == 201:
                flash('Registro exitoso. Por favor inicia sesión.')
                return redirect(url_for('login'))
            else:
                flash('Error al registrar usuario')
        except requests.exceptions.RequestException as e:
            flash('Error de conexión con el servicio de autenticación')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    flash('Sesión cerrada')
    return redirect(url_for('home'))

# ==================== BOOK ROUTES ====================
@app.route('/catalog')
def catalog():
    try:
        response = requests.get(f'{CATALOG_SERVICE_URL}/catalog', timeout=5)
        if response.status_code == 200:
            books = response.json()
        else:
            books = []
            flash('Error al obtener el catálogo')
    except requests.exceptions.RequestException as e:
        books = []
        flash('Error de conexión con el servicio de catálogo')
    
    return render_template('catalog.html', books=books)

@app.route('/my_books')
@login_required
def my_books():
    user_id = session.get('user', {}).get('id')
    try:
        response = requests.get(f'{STORE_SERVICE_URL}/books', timeout=5)
        if response.status_code == 200:
            all_books = response.json()
            # Filtrar libros del usuario actual (si tuviera seller_id)
            books = all_books
        else:
            books = []
            flash('Error al obtener tus libros')
    except requests.exceptions.RequestException as e:
        books = []
        flash('Error de conexión')
    
    return render_template('my_books.html', books=books)

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        user_id = session.get('user', {}).get('id')
        
        try:
            response = requests.post(
                f'{STORE_SERVICE_URL}/books',
                json={
                    'title': title,
                    'author': author,
                    'description': description,
                    'price': price,
                    'stock': stock
                },
                timeout=5
            )
            
            if response.status_code == 201:
                flash('Libro agregado exitosamente')
                return redirect(url_for('my_books'))
            else:
                flash('Error al agregar el libro')
        except requests.exceptions.RequestException as e:
            flash('Error de conexión')
    
    return render_template('add_book.html')

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        
        try:
            response = requests.put(
                f'{STORE_SERVICE_URL}/books/{book_id}',
                json={
                    'title': title,
                    'author': author,
                    'description': description,
                    'price': price,
                    'stock': stock
                },
                timeout=5
            )
            
            if response.status_code == 200:
                flash('Libro actualizado exitosamente')
                return redirect(url_for('my_books'))
            else:
                flash('Error al actualizar el libro')
        except requests.exceptions.RequestException as e:
            flash('Error de conexión')
    
    # GET: obtener datos del libro
    try:
        response = requests.get(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
        if response.status_code == 200:
            book = response.json()
            return render_template('edit_book.html', book=book)
        else:
            flash('Libro no encontrado')
            return redirect(url_for('my_books'))
    except requests.exceptions.RequestException as e:
        flash('Error de conexión')
        return redirect(url_for('my_books'))

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    try:
        response = requests.delete(f'{STORE_SERVICE_URL}/books/{book_id}', timeout=5)
        if response.status_code == 204:
            flash('Libro eliminado exitosamente')
        else:
            flash('Error al eliminar el libro')
    except requests.exceptions.RequestException as e:
        flash('Error de conexión')
    
    return redirect(url_for('my_books'))

# ==================== PURCHASE/PAYMENT/DELIVERY ====================
@app.route('/buy/<int:book_id>', methods=['POST'])
@login_required
def buy(book_id):
    quantity = int(request.form.get('quantity', 1))
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
        
        # Reducir stock
        updated_stock = book.get('stock') - quantity
        update_data = {
            'title': book.get('title'),
            'author': book.get('author'),
            'price': book.get('price'),
            'stock': updated_stock
        }
        
        update_response = requests.put(
            f'{STORE_SERVICE_URL}/books/{book_id}',
            json=update_data,
            timeout=5
        )
        
        if update_response.status_code == 200:
            # Crear un ID de compra simulado y guardarlo en sesión
            import time
            purchase_id = int(time.time())
            session['current_purchase'] = {
                'id': purchase_id,
                'book_id': book_id,
                'book_title': book.get('title'),
                'quantity': quantity,
                'total_price': total_price,
                'user_id': user_id,
                'status': 'Pending Payment'
            }
            # Redirigir a la página de pago
            return redirect(url_for('payment_page', purchase_id=purchase_id))
        else:
            flash('Error al procesar la compra')
    except requests.exceptions.RequestException as e:
        flash('Error de conexión')
    
    return redirect(url_for('catalog'))

@app.route('/payment/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def payment_page(purchase_id):
    # Obtener datos de la compra actual
    purchase = session.get('current_purchase')
    
    if not purchase or purchase.get('id') != purchase_id:
        flash('Compra no encontrada')
        return redirect(url_for('catalog'))
    
    if request.method == 'POST':
        method = request.form.get('method')
        amount = request.form.get('amount')
        
        # Actualizar estado de la compra
        purchase['status'] = 'Paid'
        purchase['payment_method'] = method
        session['current_purchase'] = purchase
        
        flash(f'Pago de ${amount} procesado con {method}')
        
        # Redirigir a opciones de entrega
        return redirect(url_for('select_delivery', purchase_id=purchase_id))
    
    # Pasar información de la compra al template
    return render_template('payment.html', purchase=purchase, purchase_id=purchase_id)

@app.route('/delivery/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def select_delivery(purchase_id):
    # Obtener datos de la compra actual
    purchase = session.get('current_purchase')
    
    if not purchase or purchase.get('id') != purchase_id:
        flash('Compra no encontrada')
        return redirect(url_for('catalog'))
    
    if request.method == 'POST':
        provider_id = request.form.get('provider')
        
        # Mock de proveedores
        providers = [
            {'id': '1', 'name': 'DHL'},
            {'id': '2', 'name': 'FedEx'},
            {'id': '3', 'name': 'Envia'},
            {'id': '4', 'name': 'Servientrega'},
        ]
        provider_name = next((p['name'] for p in providers if p['id'] == provider_id), 'Desconocido')
        
        flash(f'Compra completada! Entrega asignada a {provider_name}. Libro: {purchase.get("book_title")}')
        
        # Limpiar la compra de la sesión
        session.pop('current_purchase', None)
        
        return redirect(url_for('catalog'))
    
    # Mock de proveedores (en el monolito viene de la BD)
    providers = [
        {'id': 1, 'name': 'DHL', 'coverage_area': 'Internacional', 'cost': 50.0},
        {'id': 2, 'name': 'FedEx', 'coverage_area': 'Internacional', 'cost': 45.0},
        {'id': 3, 'name': 'Envia', 'coverage_area': 'Nacional', 'cost': 20.0},
        {'id': 4, 'name': 'Servientrega', 'coverage_area': 'Nacional', 'cost': 15.0},
    ]
    
    return render_template('delivery_options.html', providers=providers, purchase_id=purchase_id)

@app.route('/admin/users')
@login_required
def list_users():
    try:
        response = requests.get(f'{AUTH_SERVICE_URL}/users', timeout=5)
        if response.status_code == 200:
            users_data = response.json()
            users = []
            for user in users_data:
                users.append({
                    'id': user['id'],
                    'name': user['username'],
                    'email': user['username']
                })
            return render_template('list_users.html', users=users)
        else:
            flash('Error al obtener usuarios')
            return render_template('list_users.html', users=[])
    except Exception as e:
        flash('Error de conexión')
        return render_template('list_users.html', users=[])

# Context processor para hacer current_user disponible en templates
@app.context_processor
def inject_user():
    user = get_current_user()
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
    app.run(host='0.0.0.0', port=5000, debug=True)
