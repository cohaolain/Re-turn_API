# Use the official Python image as a base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY src/ src/
COPY start.sh .

# Ensure the start.sh script is executable
RUN chmod +x start.sh

# Expose the port the app runs on
EXPOSE 13534

# Run the application
CMD ["./start.sh"]
