# MyBookConnect Architecture

## Overview

MyBookConnect is a full-stack web application with a decoupled frontend and backend. The application is containerized using Docker for consistent development and deployment environments.

## Backend

The backend is a monolithic application built with Python and the Django framework.

- **Framework:** Django
- **API:** A RESTful API is provided using Django Rest Framework.
- **Authentication:** User authentication is handled via JSON Web Tokens (JWT) using the `djangorestframework-simplejwt` library.
- **Database:** The primary database is PostgreSQL, managed by the `psycopg2-binary` driver.
- **CORS:** Cross-Origin Resource Sharing is enabled with `django-cors-headers` to allow the frontend to communicate with the backend API.
- **Apps:** The backend is organized into several Django apps:
    - `users`: Manages user registration, profiles, and authentication.
    - `books`: Manages book information, user libraries, and related features.
    - `app`: Appears to be a core or general-purpose app.
- **Production Server:** Gunicorn is used as the WSGI HTTP server for production deployments.
- **Cache:** Redis is used for caching, improving performance.

## Frontend

The frontend is a modern single-page application (SPA).

- **Framework:** Built with React and TypeScript.
- **Bundler:** Vite is used for fast development and optimized builds.
- **Routing:** Client-side routing is managed by React Router.
- **State Management:** Global state, particularly for authentication, is handled by Zustand.
- **Styling:** The UI is styled using Tailwind CSS, complemented by the Flowbite component library.
- **API Communication:** The frontend communicates with the backend REST API using the Axios HTTP client.

## Containerization

The entire application is orchestrated using Docker and Docker Compose.

- **`docker-compose.yml`:** Defines the services for the application:
    - `backend`: The Django service.
    - `frontend`: The React service (for development).
    - `db`: The PostgreSQL database service.
    - `cache`: The Redis caching service.
- **`docker-compose.prod.yml`:** A separate compose file likely exists for production, potentially with optimizations like using a production-ready web server for the frontend and different volume configurations.
- **`Dockerfile`:** Each service (`frontend` and `backend`) has its own Dockerfile to define its image.

## Authentication Flow

1.  A user registers or logs in through the React frontend.
2.  The frontend sends a request with user credentials to the backend's `/api/token/` endpoint (a standard for `simple-jwt`).
3.  The Django backend validates the credentials and, if successful, returns an access token and a refresh token.
4.  The frontend stores these tokens (e.g., in local storage) and uses the access token in the `Authorization` header for subsequent API requests.
5.  The `Zustand` store manages the user's authentication state throughout the application.
6.  Protected routes in the frontend ensure that only authenticated users can access certain pages.
