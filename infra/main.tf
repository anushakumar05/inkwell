# Terraform-managed Inkwell production infrastructure.
# Single EC2 instance running Docker, with security group + key pair.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# Look up the latest Amazon Linux 2023 AMI dynamically.
# Hardcoding AMI IDs is a smell — they change region-to-region and over time.
# ---------------------------------------------------------------------------
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ---------------------------------------------------------------------------
# SSH key pair — uploaded to AWS so the EC2 trusts our local private key.
# ---------------------------------------------------------------------------
resource "aws_key_pair" "this" {
  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = var.ssh_public_key
}

# ---------------------------------------------------------------------------
# Security group — the EC2's firewall.
# Inbound: SSH (port 22) from YOUR IP only, HTTP (80) and FastAPI (8000) from anywhere.
# Outbound: all traffic allowed (so the container can reach OpenAI/Anthropic/Atlas).
# ---------------------------------------------------------------------------
resource "aws_security_group" "this" {
  name        = "${var.project_name}-${var.environment}-sg"
  description = "Inkwell ${var.environment} EC2 firewall"

  ingress {
    description = "SSH from my laptop only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_ip_cidr]
  }

  ingress {
    description = "FastAPI direct on 8000"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (for future HTTPS proxy)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------------------------------------------------------
# The EC2 instance itself.
# user_data runs once on first boot — installs Docker so the host is ready
# to run our app container when we ship it in Task 8.
# ---------------------------------------------------------------------------
resource "aws_instance" "this" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.this.key_name

  vpc_security_group_ids = [aws_security_group.this.id]

  iam_instance_profile = aws_iam_instance_profile.ec2.name

  user_data = <<-EOF
    #!/bin/bash
    set -e
    dnf update -y
    dnf install -y docker
    systemctl enable --now docker
    usermod -aG docker ec2-user
  EOF

  # Replace the instance if user_data changes — needed because user_data only
  # runs on first boot, so editing it later doesn't do anything unless we
  # explicitly recreate.
  user_data_replace_on_change = true

  tags = {
    Name = "${var.project_name}-${var.environment}"
  }
}

# ---------------------------------------------------------------------------
# ECR repo to hold our backend Docker image.
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Allow our EC2 to pull from ECR by attaching an IAM role to it.
resource "aws_iam_role" "ec2" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_ecr_read" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# ---------------------------------------------------------------------------
# Elastic IP — static public IP that survives stop/start cycles.
# Free while attached to a running instance.
# ---------------------------------------------------------------------------
resource "aws_eip" "this" {
  domain   = "vpc"
  instance = aws_instance.this.id

  tags = {
    Name = "${var.project_name}-${var.environment}-eip"
  }
}