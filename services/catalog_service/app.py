from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import pika
import json
import threading
import time

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "catalog.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# RabbitMQ setup
rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://rabbitmq')

def process_book_event(ch, method, properties, body):
    try:
        with app.app_context():
            event = json.loads(body)
            event_type = event['type']
            book_data = event['book']
            
            if event_type == 'book_created':
                book = Book(id=book_data['id'],
                           title=book_data['title'],
                           author=book_data['author'],
                           price=book_data['price'],
                           stock=book_data['stock'])
                db.session.merge(book)
            elif event_type == 'book_updated':
                book = Book.query.get(book_data['id'])
                if book:
                    book.title = book_data['title']
                    book.author = book_data['author']
                    book.price = book_data['price']
                    book.stock = book_data['stock']
            elif event_type == 'book_deleted':
                book = Book.query.get(book_data['id'])
                if book:
                    db.session.delete(book)
            
            db.session.commit()
            app.logger.info(f"Processed {event_type} event for book {book_data['id']}")
    except Exception as e:
        app.logger.error(f"Error processing event: {e}")
        
def start_event_consumer():
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()
            
            channel.exchange_declare(exchange='book_events',
                                  exchange_type='fanout',
                                  durable=True)
            
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.queue_bind(exchange='book_events',
                             queue=queue_name)
            
            channel.basic_consume(queue=queue_name,
                                on_message_callback=process_book_event,
                                auto_ack=True)
            
            app.logger.info("Started consuming book events")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            app.logger.error("Lost connection to RabbitMQ, reconnecting...")
            time.sleep(5)
        except Exception as e:
            app.logger.error(f"Unexpected error in consumer: {e}")
            time.sleep(5)

class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    author = db.Column(db.String(200))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "author": self.author, "price": self.price, "stock": self.stock}

@app.route('/')
def index():
    return jsonify({"service": "catalog", "status": "ok"})

@app.route('/catalog')
def catalog():
    # For early victory this service reads directly from store DB
    books = Book.query.all()
    return jsonify([b.to_dict() for b in books])

if __name__ == '__main__':
    # Create tables and start consumer in background thread
    with app.app_context():
        db.create_all()
    
    # Start event consumer in background thread
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    app.run(host='0.0.0.0', port=5002, debug=True)
