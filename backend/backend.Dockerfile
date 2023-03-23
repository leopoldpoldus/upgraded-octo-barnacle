# Start from a base image with Python installed
FROM python:3.10-slim-buster

#name of the container
LABEL maintainer="Spoken Conversation AI"


# Create a directory for the app and copy the requirements.txt file
RUN mkdir -p /app
COPY requirements.txt /app/



# Install dependencies
RUN pip install -r /app/requirements.txt

# Copy the rest of the app's code
COPY . /app

# Set the working directory
RUN cd /app


# Expose port 5000 and run the app
EXPOSE 5000
CMD ["flask", "run"]