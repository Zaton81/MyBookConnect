# My Book Connect

My Book Connect es una aplicación para conectar con otros lectores. EN DESARROLLO

## Requisitos

- Docker
- Docker Compose

## Cómo empezar

1.  **Clona el repositorio:**
    ```bash
    git clone <https://github.com/Zaton81/MyBookConnect>
    cd MyBookConnect
    ```

2.  **Configura las variables de entorno:**
    Crea un archivo `.env` a partir del ejemplo y rellena las variables. Puedes copiar el ejemplo directamente:
    ```bash
    cp .env.example .env
    ```

3.  **Levanta los servicios con Docker Compose:**
    ```bash
    docker-compose up -d --build
    ```

4.  **Accede a la aplicación:**
    -   **Frontend:** [http://localhost:5173](http://localhost:5173)
    -   **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)
