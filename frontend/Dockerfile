# syntax=docker/dockerfile:1

# ---- deps: node_modules, shared by dev and the production build --------------
FROM node:22-bookworm-slim AS deps

WORKDIR /app

COPY package*.json ./
COPY scripts/install-container-deps.sh ./scripts/install-container-deps.sh
RUN FRONTEND_INSTALL_MODE=ci sh scripts/install-container-deps.sh

# ---- dev: used by docker-compose, which bind-mounts source over /app --------
FROM deps AS dev

COPY . .

EXPOSE 3000

# ---- builder: next build -> .next/standalone --------------------------------
FROM deps AS builder

COPY . .

# next.config.ts resolves rewrites() at BUILD time and bakes the destinations into
# the route manifest, so the backend address must be present now -- setting it only
# at runtime silently yields rewrites pointing at the fallback.
ARG SERVER_API_BASE_URL=http://backend:8000
ENV SERVER_API_BASE_URL=${SERVER_API_BASE_URL}
ENV NEXT_TELEMETRY_DISABLED=1

# postbuild runs scripts/sync-standalone-assets.sh, which copies .next/static and
# public/ into .next/standalone.
RUN npm run build

# ---- prod: standalone server, without the build toolchain -------------------
FROM node:22-bookworm-slim AS prod

WORKDIR /app

# curl is required by the stack file's healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/.next/standalone ./

EXPOSE 3000

CMD ["node", "server.js"]
