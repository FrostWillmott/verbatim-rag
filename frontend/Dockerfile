# Pinned by digest, not by tag: a tag is mutable, so `python:3.11-slim` today and
# tomorrow can be different images, and the lockfile below then constrains packages
# on top of an OS layer nobody chose. Refresh with:
#   docker buildx imagetools inspect <image>:<tag> --format '{{.Manifest.Digest}}'
# The digest is the manifest list, so the same line builds on arm64 and x86_64.
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine@sha256:db35bfc6b2951e7f8a72db5db120288c127ffaeeb4a6d4b95a26fead017d5913
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
