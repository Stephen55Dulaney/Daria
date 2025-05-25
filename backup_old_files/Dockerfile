FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p data/interviews

# Expose port
EXPOSE 5025

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "run_interview_api.py", "--port", "5025"] 