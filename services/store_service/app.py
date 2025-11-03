from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import os
import pika
import json
from threading import Lock
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://bookstore_user:bookstore_pass@db/bookstore')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# RabbitMQ setup with reconnection
rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://rabbitmq')
rabbitmq_lock = Lock()
rabbitmq_channel = None

def get_rabbitmq_channel():
    global rabbitmq_channel
    with rabbitmq_lock:
        if rabbitmq_channel is None or rabbitmq_channel.is_closed:
            retries = 5
            while retries > 0:
                try:
                    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
                    rabbitmq_channel = connection.channel()
                    rabbitmq_channel.exchange_declare(exchange='book_events', 
                                                   exchange_type='fanout', 
                                                   durable=True)
                    break
                except pika.exceptions.AMQPConnectionError:
                    retries -= 1
                    if retries == 0:
                        raise
                    time.sleep(2)
        return rabbitmq_channel

def publish_event(event_type, book_data):
    try:
        channel = get_rabbitmq_channel()
        message = {
            'type': event_type,
            'book': book_data
        }
        channel.basic_publish(
            exchange='book_events',
            routing_key='',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
    except Exception as e:
        app.logger.error(f"Failed to publish event: {e}")
        # Continue anyway - eventual consistency

db = SQLAlchemy(app)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "user_id": self.user_id
        }

@app.route('/')
def index():
    return jsonify({"service": "store", "status": "ok"})

# CRUD endpoints for books
@app.route('/books', methods=['GET'])
def list_books():
    user_id = request.args.get('user_id', type=int)
    if user_id is not None:
        books = Book.query.filter_by(user_id=user_id).all()
    else:
        books = Book.query.all()
    return jsonify([b.to_dict() for b in books])

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify(book.to_dict())

@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json() or {}
    if 'title' not in data:
        abort(400, 'title is required')
    if 'user_id' not in data:
        abort(400, 'user_id is required')
    book = Book(
        title=data['title'],
        author=data.get('author'),
        description=data.get('description'),
        price=data.get('price', 0.0),
        stock=data.get('stock', 0),
        user_id=data['user_id']
    )
    db.session.add(book)
    db.session.commit()
    # Publish book created event
    book_data = book.to_dict()
    publish_event('book_created', book_data)
    return jsonify(book_data), 201

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    data = request.get_json() or {}
    book.title = data.get('title', book.title)
    book.author = data.get('author', book.author)
    book.description = data.get('description', book.description)
    book.price = data.get('price', book.price)
    book.stock = data.get('stock', book.stock)
    db.session.commit()
    # Publish book updated event
    book_data = book.to_dict()
    publish_event('book_updated', book_data)
    return jsonify(book_data)

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    book_data = book.to_dict()  # Get data before deletion
    db.session.delete(book)
    db.session.commit()
    # Publish book deleted event
    publish_event('book_deleted', book_data)
    return '', 204

if __name__ == '__main__':
    # create tables on startup (idempotent)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
