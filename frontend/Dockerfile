FROM node:20-alpine

WORKDIR /app

# Copy package lists
COPY package.json ./

# Install packages
RUN npm install

# Copy source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run the app
CMD ["npm", "run", "dev"]
