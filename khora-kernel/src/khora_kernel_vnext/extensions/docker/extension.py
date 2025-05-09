import argparse
import logging
from pathlib import Path

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
from pyscaffold.templates import get_template

_logger = logging.getLogger(__name__)

class DockerExtension(Extension):
    """Generates a docker-compose.yml file for the project."""

    name = "khora_docker"  # kebab-case for the CLI flag

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Add Docker containerization to the project",
        )
        return self

    def activate(self, actions: list[Action]) -> list[Action]:
        """Activate extension rules. See :obj:`pyscaffold.actions.Action`."""
        
        # Check if the khora tool and docker feature are enabled in pyproject.toml
        # This logic will need to be more robust, likely by parsing pyproject.toml
        # For now, we assume it's enabled if the extension is explicitly called.
        # A more complete implementation would involve accessing the parsed manifest
        # from the core extension.

        actions = self.register(actions, add_docker_compose_file, after="define_structure")
        return actions


def add_docker_compose_file(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """Add the docker-compose.yml file to the project structure.

    Args:
        struct: project representation as (possibly) nested :obj:`dict`.
        opts: given options, see :obj:`create_project` for an example.

    Returns:
        Project structure and options
    """
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        _logger.warning("Khora config not found in opts. Skipping docker-compose.yml generation.")
        return struct, opts
        
    # Check if the docker feature is enabled
    if not getattr(khora_config.features, "docker", False):
        _logger.info("Khora Docker feature not enabled. Skipping docker-compose.yml generation.")
        return struct, opts

    # Get paths and other config from khora_config
    api_dir = getattr(khora_config.paths, "api_dir", "api") # Default to 'api' if not specified
    http_port = getattr(khora_config.ports, "http", 8000) # Default to 8000
    
    # Get Docker-specific config
    docker_config = getattr(khora_config.plugins_config, "docker", {})
    api_service_name = getattr(docker_config, "api_service_name", "api") # Default to 'api'

    # Get database, broker and observability features
    database = getattr(khora_config.features, "database", "none")
    broker = getattr(khora_config.features, "broker", "none")
    observability = getattr(khora_config.features, "observability", False)
    
    # Prepare environment variables and service dependencies for the API service
    api_env_vars = ""
    api_depends_on = ""
    depends_list = []  # Track dependencies
    
    # Prepare PostgreSQL or SQLite configuration
    postgres_service = ""
    volumes = ""
    
    if database == "postgres":
        # Add PostgreSQL service
        postgres_service = """postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5"""
        
        # Add volume for PostgreSQL
        volumes = "volumes:\n  db-data:"
        
        # Add dependency for API service
        depends_list.append("postgres")
        
        # Add DATABASE_URL environment variable
        api_env_vars += """environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/app_db"""
        
    elif database == "sqlite":
        # For SQLite, add a volume and mount point
        volumes = "volumes:\n  db-data:"
        
        # Updating mounts for API service
        api_env_vars += """environment:
      DATABASE_URL: sqlite:////app/data/local.db
    volumes:
      - ./${api_dir}:/app/${api_dir}
      - db-data:/app/data"""
    
    # Prepare Redis broker configuration
    redis_service = ""
    
    if broker == "redis":
        # Add Redis service
        redis_service = """redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5"""
        
        # Add dependency for API service
        depends_list.append("redis")
        
        # Add REDIS_URL environment variable
        if api_env_vars:
            # If environment block already exists, just add the variable
            api_env_vars = api_env_vars.replace("environment:", "environment:\n      REDIS_URL: redis://redis:6379/0")
        else:
            # Otherwise, create the environment block
            api_env_vars += """environment:
      REDIS_URL: redis://redis:6379/0"""
    
    # Prepare observability stack configuration
    otel_collector_service = ""
    prometheus_service = ""
    grafana_service = ""
    
    if observability:
        # Add OpenTelemetry Collector service
        otel_collector_service = """otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "4317"]
      interval: 10s
      timeout: 5s
      retries: 5"""
        
        # Add Prometheus service
        prometheus_service = """prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    healthcheck:
      test: ["CMD", "wget", "-q", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      - otel-collector"""
        
        # Add Grafana service
        grafana_service = """grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus"""
        
        # Add dependencies for API service
        depends_list.append("otel-collector")
        
        # Add OTEL environment variables
        if api_env_vars:
            # If environment block already exists, just add the variables
            otel_vars = """
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: ${api_service_name}
      OTEL_TRACES_EXPORTER: otlp
      OTEL_METRICS_EXPORTER: otlp
      OTEL_LOGS_EXPORTER: otlp"""
            api_env_vars = api_env_vars.replace("environment:", f"environment:{otel_vars}")
        else:
            # Otherwise, create the environment block with OTEL variables
            api_env_vars += """environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: ${api_service_name}
      OTEL_TRACES_EXPORTER: otlp
      OTEL_METRICS_EXPORTER: otlp
      OTEL_LOGS_EXPORTER: otlp"""
        
        # Add volumes for Prometheus and Grafana data
        if volumes:
            # If volumes section already exists, add to it
            volumes += "\n  prometheus-data:\n  grafana-data:"
        else:
            # Otherwise, create the volumes section
            volumes = "volumes:\n  prometheus-data:\n  grafana-data:"
    
    # Build depends_on section if we have dependencies
    if depends_list:
        api_depends_on = "depends_on:\n"
        for dep in depends_list:
            api_depends_on += f"      - {dep}\n"
    
    # Template for docker-compose.yml
    docker_compose_template = get_template("docker_compose_yml", relative_to="khora_kernel_vnext.extensions.docker")
    
    # Get the project name from khora_config or fall back to opts['name']
    project_name = getattr(khora_config, "project_name", None)
    if not project_name:
        project_name = opts.get("name", "khora-project")  # PyScaffold sets 'name', but as fallback use a default
        _logger.info(f"Using project name from PyScaffold: {project_name}")
    
    docker_compose_content = docker_compose_template.substitute(
        api_dir=api_dir,
        http_port=http_port,
        api_service_name=api_service_name,
        project_name=project_name,  # Use the project name we got from config or opts
        api_env_vars=api_env_vars,
        api_depends_on=api_depends_on,
        postgres_service=postgres_service,
        redis_service=redis_service,
        otel_collector_service=otel_collector_service,
        prometheus_service=prometheus_service,
        grafana_service=grafana_service,
        volumes=volumes
    )

    # Add the docker-compose.yml to the root of the project
    struct["docker-compose.yml"] = (docker_compose_content, no_overwrite())
    
    _logger.info(f"Generated docker-compose.yml for service '{api_service_name}' in '{api_dir}' on port {http_port}.")
    
    # Generate observability config files if the feature is enabled
    if observability:
        # Generate Prometheus config
        prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
        
  - job_name: 'api'
    static_configs:
      - targets: ['${api_service_name}:${http_port}/metrics']
"""
        struct["prometheus.yml"] = (prometheus_config, no_overwrite())
        
        # Generate OpenTelemetry Collector config
        otel_collector_config = """
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: "${project_name}"
    
  logging:
    loglevel: info
    
  otlp:
    endpoint: "jaeger:4317"
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging, otlp]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging, prometheus]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
"""
        struct["otel-collector-config.yaml"] = (otel_collector_config, no_overwrite())
        
        _logger.info("Generated observability configuration files.")

    return struct, opts
