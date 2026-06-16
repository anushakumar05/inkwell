output "instance_public_ip" {
  description = "Stable Elastic IP attached to the EC2"
  value       = aws_eip.this.public_ip
}

output "ssh_command" {
  description = "Copy-pasteable command to SSH into the instance"
  value       = "ssh -i ~/.ssh/inkwell-tf-key ec2-user@${aws_eip.this.public_ip}"
}

output "app_url" {
  description = "Where your app's backend is reachable"
  value       = "http://${aws_eip.this.public_ip}:8000"
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}