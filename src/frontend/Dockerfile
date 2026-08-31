FROM node:22-slim

WORKDIR /app

# Install dependencies first, before copying the rest of the source.
# Docker caches each step — this way, editing a .vue file later doesn't
# force npm install to re-run, only actual dependency changes do.
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 80

# --host 0.0.0.0 is required, not optional: Vite's dev server binds to
# localhost only by default, which is invisible from outside the container
# even with the port mapped. --host makes it listen on all interfaces.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]