FROM node:22-bookworm-slim

WORKDIR /app

COPY package*.json ./
COPY scripts/install-container-deps.sh ./scripts/install-container-deps.sh
RUN FRONTEND_INSTALL_MODE=ci sh scripts/install-container-deps.sh

COPY . .

EXPOSE 3000
