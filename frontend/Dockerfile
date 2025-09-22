# ─── Etapa de Desarrollo ───
FROM node:20-alpine AS development
WORKDIR /app
RUN npm install -g pnpm
ENV NODE_ENV=development
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install
COPY . .
EXPOSE 5173
# El server.host en vite.config.js se encarga de que sea accesible
CMD ["pnpm", "dev"]

# ─── Etapa de Build (Production) ───
FROM development AS build
RUN pnpm build

# ─── Etapa Final (Production) ───
FROM nginx:1.25-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
