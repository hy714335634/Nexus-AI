FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app

ENV PYTHONPATH="/app:/app/nexus_utils:$PYTHONPATH"



COPY projects/sports_team_match_predictor/requirements.txt projects/sports_team_match_predictor/requirements.txt
COPY nexus_utils nexus_utils
# Install from requirements file
RUN pip install -r projects/sports_team_match_predictor/requirements.txt




RUN pip install aws-opentelemetry-distro>=0.10.1


# Set AWS region environment variable

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

# Use the full module path

CMD ["opentelemetry-instrument", "python", "-m", "agents.generated_agents.sports_team_match_predictor.sports_team_match_predictor"]
