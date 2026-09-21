FROM node:20-alpine

RUN corepack enable && corepack prepare pnpm@12.4.2 --activate
WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY infra/realtime/package.json infra/realtime/package.json
RUN pnpm install --prod --frozen-lockfile --filter @manobal/realtime-local
WORKDIR /workspace/infra/realtime
COPY infra/realtime/server.mjs ./

USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
