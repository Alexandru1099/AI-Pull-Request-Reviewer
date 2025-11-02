FROM node:20-alpine AS base

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app
RUN chown appuser:appgroup /app

USER appuser

COPY --chown=appuser:appgroup package.json yarn.lock* ./
RUN yarn install --frozen-lockfile || yarn install

COPY --chown=appuser:appgroup . .

ENV NEXT_TELEMETRY_DISABLED=1

RUN yarn build

EXPOSE 3000

CMD ["yarn", "start", "-p", "3000"]

