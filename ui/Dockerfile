# Hot-reload development server
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies (use npm install for better compatibility)
RUN npm install --legacy-peer-deps

EXPOSE 5173

# Vite dev server with hot-reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
