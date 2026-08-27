FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN npm run build

# Switch to the node user that comes with the image
USER node

EXPOSE 3000

CMD ["npm", "start"]
