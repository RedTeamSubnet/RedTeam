# Use the official Python image as the base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt
RUN python -m nltk.downloader stopwords

# Download BGE model for ctranslate2
RUN ct2-transformers-converter --model BAAI/bge-small-en-v1.5 --output_dir /app/bge-small-en-v1.5 --force

# Set the environment variable
ENV MODEL_PATH="/app/bge-small-en-v1.5"
ENV VLLM_URL="http://storage.redteam.technology/v1"
ENV VLLM_API_KEY="your-api-key"
ENV VLLM_MODEL="unsloth/Meta-Llama-3.1-8B-Instruct"
ENV OPENAI_API_KEY="your-api-key"

# Copy the rest of the application code to the container
COPY . .

# Expose the port that FastAPI will be running on
EXPOSE 10001

# Command to run the FastAPI application using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10001"]
