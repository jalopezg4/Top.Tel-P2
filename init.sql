-- Crear el usuario con permisos desde cualquier host
CREATE USER IF NOT EXISTS 'bookstore_user'@'%' IDENTIFIED BY 'bookstore_pass';
GRANT ALL PRIVILEGES ON bookstore.* TO 'bookstore_user'@'%';
FLUSH PRIVILEGES;
