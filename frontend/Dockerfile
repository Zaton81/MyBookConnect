# ─── Etapa de Desarrollo ───
FROM node:20-alpine AS development
WORKDIR /app
RUN npm install -g pnpm@8.15.4
ENV PNPM_STORE_PATH=/app/.pnpm-store
ENV NODE_ENV=development
COPY package.json pnpm-lock.yaml* ./
RUN pnpm config set store-dir /app/.pnpm-store --global
# El lockfile puede estar desfasado tras cambios en package.json
RUN pnpm install --no-frozen-lockfile
COPY . .
EXPOSE 5173
# El server.host en vite.config.js se encarga de que sea accesible
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# ─── Etapa de Build (Production) ───
FROM development AS build
RUN pnpm build

# ─── Etapa Final (Production) ───
FROM nginx:1.25-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
