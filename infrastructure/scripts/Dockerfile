FROM public.ecr.aws/lambda/python:3.12

# Install build dependencies
RUN dnf install -y gcc gcc-c++ && dnf clean all

# Copy project structure
COPY api ${LAMBDA_TASK_ROOT}/api/
COPY nexus_utils ${LAMBDA_TASK_ROOT}/nexus_utils/
COPY agents ${LAMBDA_TASK_ROOT}/agents/
COPY tools ${LAMBDA_TASK_ROOT}/tools/
COPY prompts ${LAMBDA_TASK_ROOT}/prompts/
COPY config ${LAMBDA_TASK_ROOT}/config/
COPY __init__.py ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir \
    strands-agents[otel] \
    strands-agents-tools \
    bedrock-agentcore \
    bedrock-agentcore-starter-toolkit \
    tooluniverse \
    boto3 \
    botocore \
    neo4j \
    fastapi \
    uvicorn[standard] \
    requests \
    redis \
    celery \
    pydantic \
    pydantic-settings \
    python-dotenv

# Set the CMD to your handler
CMD [ "api.main.lambda_handler" ]
