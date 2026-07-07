FROM node:20-alpine

WORKDIR /app

# 仅装依赖（利用 Docker 层缓存）
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY . .

# 生产构建 + 启动。Next.js standalone 输出更轻量，但此处保持简单用默认 start
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "run", "start"]
