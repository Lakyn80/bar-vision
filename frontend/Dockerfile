FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY scripts ./scripts

RUN npm ci \
    --no-audit \
    --no-fund \
    && echo "$(cksum package-lock.json | awk '{print $1"-"$2}')" > node_modules/.deps-fingerprint

COPY . .

ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
