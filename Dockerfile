# Use an official Python runtime as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 5000 available to the world outside this container
#EXPOSE 5432

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "main.py"]