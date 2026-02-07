# Frontend Independent Dockerfile
# Stage 1: Build the application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependency definitions
COPY package.json package-lock.json* ./
COPY setup.yaml ./

# Install dependencies
# Note: In a real independent build, we might use env_manager,
# but for pure frontend, npm ci is standard and efficient.
RUN npm ci

# Copy source code
COPY . .

# Build the application
# Assumes the build script outputs to /app/dist
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
