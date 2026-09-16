FROM node:20-alpine

RUN corepack enable && corepack prepare pnpm@12.4.2 --activate
WORKDIR /app
COPY infra/realtime/package.json ./
RUN pnpm install --prod --no-frozen-lockfile
COPY infra/realtime/server.mjs ./

USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
