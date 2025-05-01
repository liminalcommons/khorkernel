#!/usr/bin/env python3
# Khora Kernel - Terraform Plugin v1.0.2
# Adds Terraform infrastructure scaffolding to the project

import pathlib
import os
import sys

def render(project_root, manifest, jinja_env):
    """
    Main entry point for the Terraform plugin.
    
    Args:
        project_root (pathlib.Path): Path to the project root
        manifest (dict): The parsed KERNEL_MANIFEST.yaml contents
        jinja_env (jinja2.Environment): Configured Jinja environment
    """
    print("Running Terraform plugin...")
    
    # Get the project name from the manifest
    project_name = manifest.get('project', 'khora-app')
    
    # Create the Terraform directory structure
    tf_dir = project_root / "infra" / "terraform"
    tf_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    modules_dir = tf_dir / "modules"
    modules_dir.mkdir(exist_ok=True)
    
    environments_dir = tf_dir / "environments"
    environments_dir.mkdir(exist_ok=True)
    
    # Create environment subdirectories
    for env in ["dev", "staging", "prod"]:
        (environments_dir / env).mkdir(exist_ok=True)
    
    # Get plugin directory for static files
    plugin_dir = pathlib.Path(__file__).parent
    kernel_dir = project_root / ".khorkernel"
    
    # Create basic Terraform files
    
    # 1. Root module files
    # main.tf
    main_tf_content = """# Khora Kernel Terraform - Main Configuration

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  
  # Uncomment to use Terraform Cloud
  # cloud {
  #   organization = "your-org"
  #   workspaces {
  #     name = "your-workspace"
  #   }
  # }
  
  # Uncomment to use S3 backend
  # backend "s3" {
  #   bucket = "terraform-state-${project}"
  #   key    = "terraform.tfstate"
  #   region = "us-west-2"
  #   dynamodb_table = "terraform-locks"
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "${project}"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Database resources
module "database" {
  source = "./modules/database"
  
  environment        = var.environment
  project_name       = var.project_name
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  
  # Database config
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
  db_instance_class = var.db_instance_class
}

# Network resources
module "network" {
  source = "./modules/network"
  
  environment  = var.environment
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
}

# Container service resources
module "ecs" {
  source = "./modules/ecs"
  
  environment        = var.environment
  project_name       = var.project_name
  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  private_subnet_ids = module.network.private_subnet_ids
  
  # Application config
  container_image    = var.container_image
  container_port     = var.container_port
  desired_count      = var.desired_count
  cpu                = var.cpu
  memory             = var.memory
  
  # Database connection
  db_host = module.database.db_host
  db_name = var.db_name
  db_user = var.db_username
}
""".replace("${project}", project_name)
    
    (tf_dir / "main.tf").write_text(main_tf_content)
    
    # variables.tf
    variables_tf_content = """# Khora Kernel Terraform - Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "${project}"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

# Network variables
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Database variables
variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "${project}_db"
}

variable "db_username" {
  description = "Username for database access"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Password for database access"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "Instance class for the RDS instance"
  type        = string
  default     = "db.t3.micro"
}

# Application variables
variable "container_image" {
  description = "Docker image for the application container"
  type        = string
}

variable "container_port" {
  description = "Port the container exposes"
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Desired number of container instances"
  type        = number
  default     = 1
}

variable "cpu" {
  description = "CPU units for the container (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for the container in MB"
  type        = number
  default     = 512
}
""".replace("${project}", project_name)
    
    (tf_dir / "variables.tf").write_text(variables_tf_content)
    
    # outputs.tf
    outputs_tf_content = """# Khora Kernel Terraform - Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.network.private_subnet_ids
}

output "db_host" {
  description = "Database host endpoint"
  value       = module.database.db_host
}

output "api_url" {
  description = "URL of the API service"
  value       = module.ecs.api_url
}
"""
    
    (tf_dir / "outputs.tf").write_text(outputs_tf_content)
    
    # 2. Create module stubs
    for module in ["network", "database", "ecs"]:
        module_dir = modules_dir / module
        module_dir.mkdir(exist_ok=True)
        
        # Create stub files
        (module_dir / "main.tf").write_text(f"# Khora Kernel Terraform - {module.capitalize()} Module\n")
        (module_dir / "variables.tf").write_text(f"# Khora Kernel Terraform - {module.capitalize()} Variables\n")
        (module_dir / "outputs.tf").write_text(f"# Khora Kernel Terraform - {module.capitalize()} Outputs\n")
    
    # 3. Create environment files
    for env in ["dev", "staging", "prod"]:
        env_dir = environments_dir / env
        
        terraform_tfvars_content = f"""# Khora Kernel Terraform - {env.capitalize()} Environment Configuration

environment        = "{env}"
aws_region         = "us-west-2"
project_name       = "{project_name}"

# Network
vpc_cidr           = "10.0.0.0/16"

# Database - IMPORTANT: Replace these with secure values and manage them with a secret store
db_name            = "{project_name}_{env}"
db_username        = "{project_name}_user"
db_password        = "REPLACE_WITH_SECURE_PASSWORD" # DO NOT COMMIT THIS FILE WITH REAL CREDENTIALS
db_instance_class  = "db.t3.{'small' if env == 'prod' else 'micro'}"

# Application
container_image    = "{project_name}:latest"
container_port     = 8000
desired_count      = {3 if env == 'prod' else 1}
cpu                = {512 if env == 'prod' else 256}
memory             = {1024 if env == 'prod' else 512}
"""
        
        (env_dir / "terraform.tfvars").write_text(terraform_tfvars_content)
        
        # main.tf for environment
        env_main_tf_content = """# Khora Kernel Terraform - Environment Configuration

terraform {
  required_version = ">= 1.0.0"
  
  # Uncomment to use S3 backend
  # backend "s3" {
  #   bucket = "terraform-state-${project}-${env}"
  #   key    = "${env}/terraform.tfstate"
  #   region = "us-west-2"
  #   dynamodb_table = "terraform-locks"
  #   encrypt = true
  # }
}

module "infrastructure" {
  source = "../../"
  
  environment     = var.environment
  project_name    = var.project_name
  aws_region      = var.aws_region
  
  # Network
  vpc_cidr        = var.vpc_cidr
  
  # Database
  db_name         = var.db_name
  db_username     = var.db_username
  db_password     = var.db_password
  db_instance_class = var.db_instance_class
  
  # Application
  container_image = var.container_image
  container_port  = var.container_port
  desired_count   = var.desired_count
  cpu             = var.cpu
  memory          = var.memory
}
""".replace("${project}", project_name).replace("${env}", env)
        
        (env_dir / "main.tf").write_text(env_main_tf_content)
        
        # variables.tf for environment
        (env_dir / "variables.tf").write_text("# Variables are defined in the root module\n")
        
        # outputs.tf for environment
        env_outputs_tf_content = """# Khora Kernel Terraform - Environment Outputs

output "api_url" {
  description = "URL of the API service"
  value       = module.infrastructure.api_url
}
"""
        (env_dir / "outputs.tf").write_text(env_outputs_tf_content)
    
    # 4. Create a basic README.md for the Terraform setup
    readme_content = f"""# {project_name} Infrastructure

This directory contains Terraform configurations to manage the infrastructure for {project_name}.

## Structure

```
infra/terraform/
├── main.tf                # Root module configuration
├── variables.tf           # Variable definitions
├── outputs.tf             # Output definitions
├── modules/               # Reusable modules
│   ├── database/          # Database resources (RDS)
│   ├── ecs/               # Container service resources
│   └── network/           # Network resources (VPC, subnets)
└── environments/          # Environment-specific configurations
    ├── dev/
    ├── staging/
    └── prod/
```

## Usage

### Prerequisites

- Terraform v1.0.0 or later
- AWS CLI configured with appropriate credentials
- An AWS account with necessary permissions

### Deployment

To deploy to an environment:

```bash
# Navigate to the environment directory
cd environments/dev

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the changes
terraform apply tfplan
```

### Important Security Notes

- **DO NOT** commit the `terraform.tfvars` file with real credentials
- Use a secure secret management system in production
- Consider using Terraform Cloud or an S3 backend for state management

## CI/CD Integration

This repository includes GitHub Actions workflows for Terraform operations:

- **terraform-validate**: Runs on PR to validate configurations
- **terraform-plan**: Runs on PR to generate and comment with a plan
- **terraform-apply**: Runs on merge to main to apply changes (with approvals)

See `.github/workflows/` for details.
"""
    
    (tf_dir / "README.md").write_text(readme_content)
    
    # 5. Create a .gitignore for Terraform
    gitignore_content = """# Terraform .gitignore
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
*.tfvars
.terraformrc
terraform.rc
crash.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
# Include tfvars files that are safe template examples
!example.tfvars
"""
    
    (tf_dir / ".gitignore").write_text(gitignore_content)
    
    print(f"✅ Terraform scaffolding created in {tf_dir.relative_to(project_root)}")
    print("  Note: This is a minimal setup. You'll need to complete the module implementations.")
    
    # Create or update GitHub workflow for Terraform
    workflow_dir = project_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    terraform_workflow_content = """name: Terraform

on:
  push:
    branches: [ main ]
    paths:
      - 'infra/terraform/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'infra/terraform/**'

jobs:
  terraform-validate:
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.0.0
      
      - name: Terraform Init
        run: |
          cd infra/terraform
          terraform init -backend=false
      
      - name: Terraform Validate
        run: |
          cd infra/terraform
          terraform validate
  
  terraform-plan:
    name: Plan
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    needs: terraform-validate
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.0.0
      
      - name: Terraform Init
        run: |
          cd infra/terraform/environments/dev
          terraform init -backend=false
      
      - name: Terraform Plan
        id: plan
        run: |
          cd infra/terraform/environments/dev
          terraform plan -no-color -input=false
        continue-on-error: true
      
      - name: Comment on PR
        uses: actions/github-script@v6
        if: github.event_name == 'pull_request'
        env:
          PLAN: "${{ steps.plan.outputs.stdout }}"
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const output = `#### Terraform Plan 📝\`${{ steps.plan.outcome }}\`
            
            <details><summary>Show Plan</summary>
            
            \`\`\`terraform
            ${process.env.PLAN}
            \`\`\`
            
            </details>`;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            })
"""
    
    (workflow_dir / "terraform.yml").write_text(terraform_workflow_content)
    
    print(f"✅ GitHub workflow for Terraform created in {workflow_dir.relative_to(project_root)}/terraform.yml")
    
    return True