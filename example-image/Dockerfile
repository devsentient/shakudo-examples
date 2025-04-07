FROM gcr.io/devsentient-infra/dev/jhub-basic:v1.0.0

# Install gorilla and aider
RUN pip install gorilla-cli==0.0.9 aider-chat==0.45.0

# Install goose CLI
RUN curl -fsSL https://github.com/block/goose/releases/download/latest/goose-installer.sh | sh
# Add goose to the PATH (the installer should do this, but adding explicitly to ensure it is available)
ENV PATH="/root/.local/bin:${PATH}"
