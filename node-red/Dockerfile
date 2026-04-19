FROM nodered/node-red:latest

# Change to the user data directory
WORKDIR /data

# Install node-red-dashboard in the user directory
RUN npm install --unsafe-perm node-red-dashboard

# Reset to the default Node-RED working directory for startup
WORKDIR /usr/src/node-red
