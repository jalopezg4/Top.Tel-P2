from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'auth.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route('/')
def index():
    return jsonify({"service": "auth", "status": "ok"})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')  # Obtener el nombre
    if not username or not password:
        abort(400, 'username and password required')
    if User.query.filter_by(username=username).first():
        abort(400, 'username already exists')
    u = User(username=username, password_hash=generate_password_hash(password), name=name)
    db.session.add(u)
    db.session.commit()
    return jsonify({'id': u.id, 'username': u.username, 'name': u.name}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        abort(400, 'username and password required')
    u = User.query.filter_by(username=username).first()
    if not u or not u.check_password(password):
        abort(401, 'invalid credentials')
    # For now return a simple success message; token-based auth can be added later
    return jsonify({'message': 'logged_in', 'user': {'id': u.id, 'username': u.username, 'name': u.name}})

@app.route('/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'name': u.name} for u in users])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
