# BookStore - Arquitectura de Microservicios

Sistema de tienda de libros implementado con una arquitectura de microservicios.

## Servicios

### 1. Store Service (Puerto 5003)
- CRUD de libros
- Base de datos: MySQL
- Endpoints:
  - GET /books - Listar libros
  - GET /books/<id> - Obtener libro
  - POST /books - Crear libro
  - PUT /books/<id> - Actualizar libro
  - DELETE /books/<id> - Eliminar libro

### 2. Catalog Service (Puerto 5002)
- Consulta de catálogo (read-only)
- Base de datos: SQLite (replicada desde Store via CQRS)
- Endpoints:
  - GET /catalog - Ver catálogo completo

### 3. Auth Service (Puerto 5001)
- Gestión de usuarios y autenticación
- Base de datos: SQLite
- Endpoints:
  - POST /register - Registro de usuario
  - POST /login - Login de usuario

### 4.Frontend
- Parte visual de la app para que se vea como la monolitica.
  
## Infraestructura

- **RabbitMQ**: Message broker para CQRS
  - Management UI: http://localhost:15672 (guest/guest)
  - AMQP: localhost:5672

- **MySQL**: Base de datos principal (Store)
  - Puerto: 3307
  - Credenciales: bookstore_user/bookstore_pass

## Cómo ejecutar

1. Construir y arrancar todos los servicios:
```bash
docker compose up --build -d
```

2. Verificar estado de los servicios:
```bash
docker compose ps
```

3. Ver logs:
```bash
# Todo
docker compose logs -f

# Por servicio
docker compose logs -f store
docker compose logs -f catalog
docker compose logs -f auth
```

## Ejemplos de uso

1. Crear un libro:
```bash
curl -X POST http://localhost:5003/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Mi Libro","author":"Autor","price":29.99,"stock":5}'
```

2. Ver catálogo:
```bash
curl http://localhost:5002/catalog
```

3. Registrar usuario:
```bash
curl -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'
```

## Arquitectura CQRS

- Store (Command) → RabbitMQ → Catalog (Query)
- Eventos: book_created, book_updated, book_deleted
- Replicación asíncrona para eventual consistency
