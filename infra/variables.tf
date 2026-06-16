# Input variables — what changes between deploys
# Values come from terraform.tfvars (not committed) or the command line.

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (t3.micro = free tier)"
  type        = string
  default     = "t3.micro"
}

variable "project_name" {
  description = "Project name used as a prefix for AWS resource names"
  type        = string
  default     = "inkwell"
}

variable "environment" {
  description = "Environment name: 'staging' or 'prod'"
  type        = string
  default     = "prod"
}

variable "ssh_public_key" {
  description = "Public SSH key content to install on the EC2 for ec2-user"
  type        = string
}

variable "your_ip_cidr" {
  description = "Your home/laptop IP in CIDR form, used to restrict SSH access (e.g. '70.123.45.6/32')"
  type        = string
}