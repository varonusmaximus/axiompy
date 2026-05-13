"""
Concrete implementations of secret clients for various backends.

Each implementation module provides a specific backend integration:
- cerberus.py: Acme's Cerberus secret management
- aws_secrets_manager.py: AWS Secrets Manager
- aws_kms.py: AWS Key Management Service
- local.py: Local .env file backend
"""
