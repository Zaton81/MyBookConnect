# ─── Etapa de Desarrollo ───
FROM node:22-alpine AS development
WORKDIR /app
RUN npm install -g pnpm@10
ENV PNPM_STORE_PATH=/app/.pnpm-store
ENV NODE_ENV=development
COPY package.json pnpm-lock.yaml* ./
RUN pnpm config set store-dir /app/.pnpm-store --global
RUN pnpm install --no-frozen-lockfile
COPY . .
EXPOSE 5173
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# ─── Etapa de Build (Production) ───
FROM development AS build
RUN pnpm build

# ─── Etapa Final (Production) ───
FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -q --spider http://localhost:80/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
