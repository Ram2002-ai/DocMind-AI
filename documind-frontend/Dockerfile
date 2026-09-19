FROM node:20-alpine AS build

WORKDIR /app

COPY documind-frontend/package*.json ./
RUN npm ci

COPY documind-frontend/ ./
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_USE_MOCK_API=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_USE_MOCK_API=$VITE_USE_MOCK_API
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY documind-frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]