"""
Tests for the Docker extension's database and broker service integration.
"""
import pytest
import yaml
from pathlib import Path

from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraFeaturesConfig,
    KhoraPathsConfig,
    KhoraPortsConfig,
    KhoraPluginsConfig,
    KhoraDockerPluginConfig,
)
from khora_kernel_vnext.extensions.docker.extension import add_docker_compose_file
from pyscaffold.actions import ScaffoldOpts, Structure


@pytest.fixture
def base_khora_config(tmp_path: Path):
    """Create a base Khora config with Docker enabled."""
    project_path = tmp_path / "test_project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    return KhoraManifestConfig(
        project_name="test_project",
        project_description="Test project for Docker extension",
        python_version="3.11",
        paths=KhoraPathsConfig(api_dir="api", docs_dir="docs"),
        features=KhoraFeaturesConfig(docker=True),
        ports=KhoraPortsConfig(http=8080),
        plugins_config=KhoraPluginsConfig(
            docker=KhoraDockerPluginConfig(api_service_name="api_service")
        )
    )


@pytest.fixture
def mock_opts(base_khora_config):
    """Create a mock opts dictionary for testing."""
    return {
        "project_name": "test_project",
        "khora_config": base_khora_config,
    }


def test_docker_compose_with_postgres(mock_opts, base_khora_config):
    """Test that docker-compose.yml includes PostgreSQL service when database=postgres."""
    # Configure for PostgreSQL
    base_khora_config.features.database = "postgres"
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_docker_compose_file(struct, mock_opts)
    
    # Check that docker-compose.yml was generated
    assert "docker-compose.yml" in result_struct
    
    # Parse the YAML content
    docker_compose_content = result_struct["docker-compose.yml"][0]
    compose_config = yaml.safe_load(docker_compose_content)
    
    # Check for PostgreSQL service
    assert "postgres" in compose_config["services"]
    postgres_service = compose_config["services"]["postgres"]
    
    # Check PostgreSQL configuration
    assert postgres_service["image"] == "postgres:15"
    assert "POSTGRES_USER" in postgres_service["environment"]
    assert "POSTGRES_PASSWORD" in postgres_service["environment"]
    assert "POSTGRES_DB" in postgres_service["environment"]
    assert "5432:5432" in postgres_service["ports"]
    assert "db-data:/var/lib/postgresql/data" in postgres_service["volumes"]
    assert "healthcheck" in postgres_service
    
    # Check that API service depends on PostgreSQL
    api_service = compose_config["services"]["api_service"]
    assert "depends_on" in api_service
    assert "postgres" in api_service["depends_on"]
    
    # Check DATABASE_URL environment variable
    assert "environment" in api_service
    assert "DATABASE_URL" in api_service["environment"]
    assert "postgresql://" in api_service["environment"]["DATABASE_URL"]
    
    # Check for volume definition
    assert "volumes" in compose_config
    assert "db-data" in compose_config["volumes"]


def test_docker_compose_with_sqlite(mock_opts, base_khora_config):
    """Test that docker-compose.yml includes SQLite configuration when database=sqlite."""
    # Configure for SQLite
    base_khora_config.features.database = "sqlite"
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_docker_compose_file(struct, mock_opts)
    
    # Check that docker-compose.yml was generated
    assert "docker-compose.yml" in result_struct
    
    # Parse the YAML content
    docker_compose_content = result_struct["docker-compose.yml"][0]
    compose_config = yaml.safe_load(docker_compose_content)
    
    # Check API service configuration for SQLite
    api_service = compose_config["services"]["api_service"]
    assert "environment" in api_service
    assert "DATABASE_URL" in api_service["environment"]
    assert "sqlite://" in api_service["environment"]["DATABASE_URL"]
    
    # Check for volume mounts
    assert "volumes" in api_service
    assert any("db-data:/app/data" in vol for vol in api_service["volumes"])
    
    # Check for volume definition
    assert "volumes" in compose_config
    assert "db-data" in compose_config["volumes"]
    
    # Ensure there's no PostgreSQL service
    assert "postgres" not in compose_config["services"]


def test_docker_compose_with_redis(mock_opts, base_khora_config):
    """Test that docker-compose.yml includes Redis service when broker=redis."""
    # Configure for Redis
    base_khora_config.features.broker = "redis"
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_docker_compose_file(struct, mock_opts)
    
    # Check that docker-compose.yml was generated
    assert "docker-compose.yml" in result_struct
    
    # Parse the YAML content
    docker_compose_content = result_struct["docker-compose.yml"][0]
    compose_config = yaml.safe_load(docker_compose_content)
    
    # Check for Redis service
    assert "redis" in compose_config["services"]
    redis_service = compose_config["services"]["redis"]
    
    # Check Redis configuration
    assert redis_service["image"] == "redis:7"
    assert "6379:6379" in redis_service["ports"]
    assert "healthcheck" in redis_service
    
    # Check that API service depends on Redis
    api_service = compose_config["services"]["api_service"]
    assert "depends_on" in api_service
    assert "redis" in api_service["depends_on"]
    
    # Check REDIS_URL environment variable
    assert "environment" in api_service
    assert "REDIS_URL" in api_service["environment"]
    assert "redis://" in api_service["environment"]["REDIS_URL"]


def test_docker_compose_with_all_features(mock_opts, base_khora_config):
    """Test that docker-compose.yml includes all services when all features are enabled."""
    # Configure for all features
    base_khora_config.features.database = "postgres"
    base_khora_config.features.broker = "redis"
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_docker_compose_file(struct, mock_opts)
    
    # Parse the YAML content
    docker_compose_content = result_struct["docker-compose.yml"][0]
    compose_config = yaml.safe_load(docker_compose_content)
    
    # Check for all services
    assert "postgres" in compose_config["services"]
    assert "redis" in compose_config["services"]
    
    # Check API service dependencies
    api_service = compose_config["services"]["api_service"]
    assert "depends_on" in api_service
    assert "postgres" in api_service["depends_on"]
    assert "redis" in api_service["depends_on"]
    
    # Check environment variables
    assert "environment" in api_service
    assert "DATABASE_URL" in api_service["environment"]
    assert "REDIS_URL" in api_service["environment"]


def test_docker_compose_no_database_or_broker(mock_opts, base_khora_config):
    """Test that docker-compose.yml has no database or broker when features are disabled."""
    # Ensure features are disabled (default is "none")
    struct = {}
    result_struct, _ = add_docker_compose_file(struct, mock_opts)
    
    # Parse the YAML content
    docker_compose_content = result_struct["docker-compose.yml"][0]
    compose_config = yaml.safe_load(docker_compose_content)
    
    # Check that there are no database or broker services
    assert "postgres" not in compose_config["services"]
    assert "redis" not in compose_config["services"]
    
    # Check API service has no dependencies
    api_service = compose_config["services"]["api_service"]
    assert "depends_on" not in api_service
    
    # Check no database or broker environment variables
    assert "environment" not in api_service or "DATABASE_URL" not in api_service.get("environment", {})
    assert "environment" not in api_service or "REDIS_URL" not in api_service.get("environment", {})
