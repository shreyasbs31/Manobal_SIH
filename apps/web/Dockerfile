FROM node:20-alpine AS dependencies

RUN corepack enable && corepack prepare pnpm@12.4.2 --activate
WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/i18n/package.json packages/i18n/package.json
COPY infra/realtime/package.json infra/realtime/package.json
COPY e2e/package.json e2e/package.json
RUN pnpm install --frozen-lockfile --filter @manobal/web...

FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@12.4.2 --activate
WORKDIR /workspace
COPY --from=dependencies /workspace/node_modules ./node_modules
COPY --from=dependencies /workspace/apps/web/node_modules ./apps/web/node_modules
COPY --from=dependencies /workspace/packages ./packages
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web apps/web
COPY packages/ui packages/ui
COPY packages/contracts packages/contracts
COPY packages/i18n packages/i18n
ARG NEXT_PUBLIC_ENGINE_URL=http://localhost:8000
ARG NEXT_PUBLIC_MANOBAL_MODE=demo
ENV NEXT_PUBLIC_ENGINE_URL=$NEXT_PUBLIC_ENGINE_URL
ENV NEXT_PUBLIC_MANOBAL_MODE=$NEXT_PUBLIC_MANOBAL_MODE
RUN corepack pnpm --filter @manobal/web build

FROM node:20-alpine AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
COPY --from=builder --chown=node:node /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=node:node /workspace/apps/web/.next/static ./apps/web/.next/static
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
