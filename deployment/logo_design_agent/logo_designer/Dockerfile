FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app

ENV PYTHONPATH="/app:/app/nexus_utils:$PYTHONPATH"

# Copy requirements and dependencies
COPY projects/logo_design_agent/requirements.txt projects/logo_design_agent/requirements.txt
COPY nexus_utils nexus_utils

# Install dependencies
RUN pip install -r projects/logo_design_agent/requirements.txt
RUN pip install aws-opentelemetry-distro>=0.10.1

# Environment configuration
ENV AWS_DEFAULT_REGION="us-west-2"
ENV DOCKER_CONTAINER="1"
ENV PYTHONPATH="/app:/app/nexus_utils:$PYTHONPATH"

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# Expose ports
EXPOSE 8080
EXPOSE 8000

# Copy entire project
COPY . .

# Run agent
CMD ["opentelemetry-instrument", "python", "-m", "agents.generated_agents.logo_design_agent.logo_designer"]