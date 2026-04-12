FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV HOST=0.0.0.0
ENV PORT=5173

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
