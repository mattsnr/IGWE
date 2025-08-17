# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /igwe-project

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY ./app /igwe-project/app

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variable
ENV FLASK_APP app/app.py

# Command to run the application using Gunicorn (a production-ready server)
# It will look for the 'app' object in the 'app.app' module.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app.app:app"]