# Use a slim Python 3.11 image
FROM python:3.11-slim

# Install system dependencies required by PyMuPDF (fitz)
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install uv (The fast package manager)
RUN pip install uv

# Copy the dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the system environment (since we are in a container)
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the application code
COPY src/ ./src/

# Set the entrypoint to our Typer CLI
ENTRYPOINT ["python", "-m", "src.main"]