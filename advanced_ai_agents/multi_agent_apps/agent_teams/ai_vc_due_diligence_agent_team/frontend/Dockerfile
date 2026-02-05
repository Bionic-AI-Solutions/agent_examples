FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory for agents
WORKDIR /agents

# Create the vc_diligence agent directory (underscore, not hyphen - required by ADK)
RUN mkdir -p vc_diligence

# Copy project files into the agent directory
COPY requirements.txt vc_diligence/
COPY agent.py vc_diligence/
COPY tools.py vc_diligence/
COPY __init__.py vc_diligence/

# Install Python dependencies
RUN pip install --no-cache-dir -r vc_diligence/requirements.txt

# Create necessary directories
RUN mkdir -p .adk/artifacts

# Expose ADK web default port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV ADK_FORCE_LOCAL_STORAGE=0

# Run ADK web server from the parent directory
# This way ADK will detect "vc_diligence" as an agent
# Use local storage which will be mounted as a persistent volume
CMD ["python", "-m", "google.adk.cli", "web", "--host", "0.0.0.0", "--port", "8080", "--use_local_storage", "."]
