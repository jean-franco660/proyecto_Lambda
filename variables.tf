variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "input_bucket_name" {
  description = "Nombre del bucket de entrada para CSV"
  type        = string
}

variable "output_bucket_name" {
  description = "Nombre del bucket de salida para reportes"
  type        = string
}


variable "db_cluster_identifier" {
  default     = "reportes-db-cluster"
  description = "Identificador del clúster Aurora"
}

variable "db_name" {
  default     = "reportes_db"
}

variable "db_username" {
  default     = "admin"
}

variable "db_password" {
  default     = "root"
  sensitive   = true
}

variable "db_instance_class" {
  default     = "db.t3.medium"
}

variable "env" {
  description = "Nombre del entorno (por ejemplo: dev, prod, test)"
  type        = string
  default     = "dev"
}
