# Lightweight Node image for dev
FROM node:20-alpine

WORKDIR /app

# Install dependencies first to leverage layer cache
COPY package*.json ./
RUN npm ci --silent

# Copy source
COPY . .


EXPOSE 5173

# Start Vite dev server, listen on all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
