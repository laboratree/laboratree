# Laboratree web (Next.js) image.
FROM node:22-alpine AS deps
WORKDIR /app
# .npmrc carries legacy-peer-deps=true (react-spring/lottie ship stale React<=18 peer ranges).
COPY package.json package-lock.json* .npmrc* ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
EXPOSE 3000
CMD ["npm", "start"]
