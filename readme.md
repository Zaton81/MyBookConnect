# My Book Connect 📚

My Book Connect es una red social para amantes de la lectura que permite conectar con otros lectores, compartir reseñas, descubrir nuevos libros y participar en discusiones literarias.

## 🌟 Características

- Autenticación de usuarios (email/password y Google OAuth)
- Perfiles personalizables con bio y avatar
- Sistema de seguimiento entre usuarios
- Modo privado para perfiles
- API REST con Django REST Framework
- Autenticación JWT
- Frontend React con TypeScript
- Diseño responsive con Tailwind CSS

## 🛠️ Tecnologías

### Backend
- Django 5.0
- Django REST Framework
- PostgreSQL
- Redis (caché)
- JWT Authentication
- Docker

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Flowbite Components

## 📋 Requisitos

- Docker
- Docker Compose

## 🚀 Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/Zaton81/MyBookConnect.git
   cd MyBookConnect
   ```

2. **Configura el entorno:**
   ```bash
   # Copia el archivo de ejemplo
   cp backend/.env.example backend/.env
   
   # Edita backend/.env y establece:
   # - Una SECRET_KEY segura
   # - Credenciales de base de datos
   # - Otros ajustes según necesites
   ```

3. **Construye y levanta los servicios:**
   ```bash
   docker-compose up -d --build
   ```

4. **Crea un superusuario (admin):**
   ```bash
   docker-compose run --rm backend python manage.py createsuperuser
   ```

## 📍 Endpoints

La aplicación estará disponible en:

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **API Backend:** [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
- **Admin Django:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

### API Endpoints principales:

- `POST /api/v1/auth/register/` - Registro de usuario
- `POST /api/v1/auth/token/` - Login (obtener token JWT)
- `POST /api/v1/auth/token/refresh/` - Refrescar token JWT
- `GET /api/v1/auth/profile/` - Ver perfil propio
- `PUT /api/v1/auth/profile/update/` - Actualizar perfil

## 🔧 Desarrollo

Para desarrollo local:

1. **Logs en tiempo real:**
   ```bash
   docker-compose logs -f
   ```

2. **Ejecutar migraciones:**
   ```bash
   docker-compose run --rm backend python manage.py migrate
   ```

3. **Reiniciar servicios:**
   ```bash
   docker-compose restart
   ```

## 🔒 Seguridad

- Los archivos `.env` nunca deben subirse al repositorio
- Usa `.env.example` como plantilla sin datos sensibles
- Las credenciales de producción deben ser diferentes
- Todos los secretos deben cambiarse en producción

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## ✨ Agradecimientos

- [Django](https://www.djangoproject.com/)
- [React](https://reactjs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Flowbite](https://flowbite.com/)
