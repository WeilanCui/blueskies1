FROM node:22-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --include=optional && \
    case "$(uname -m)" in \
      aarch64) npm install --no-save @tailwindcss/oxide-linux-arm64-gnu lightningcss-linux-arm64-gnu ;; \
      x86_64) npm install --no-save @tailwindcss/oxide-linux-x64-gnu lightningcss-linux-x64-gnu ;; \
    esac

COPY . .

EXPOSE 3000
