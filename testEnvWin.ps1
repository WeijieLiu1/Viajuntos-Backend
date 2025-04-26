# $env:AIRSERVICE_JOBS_SECRET_KEY = "mykey"
# $env:API_DEBUG = "True"
# $env:API_DOMAIN_NAME = "http://localhost" 
# $env:API_PORT = 5000
# $env:API_SECRET_KEY = "myapisecretkey"
# # 修改数据库 URL，使用 Google Cloud SQL 的公共 IP 地址
# $env:DATABASE_URL = "postgresql://viajuntos:password123@localhost:5432/viajuntosdb"
# $env:JWT_SECRET_KEY = "myjwtkey"   
# $env:MAIL_PASSWORD = "kdbbzkbkpemzfsrd" 
# $env:MAIL_USERNAME = "zjqtlwj@gmail.com"
# $env:POSTGRES_DB = "viajuntosdb"
# $env:POSTGRES_PASSWORD = "password123" 
# $env:POSTGRES_PORT = 5432
# $env:POSTGRES_USER = "viajuntos"
# # 修改 SQLAlchemy 的数据库 URI，使用 Google Cloud SQL 的公共 IP 地址
# $env:SQLALCHEMY_DATABASE_URI = "postgresql://viajuntos:password123@localhost:5432/viajuntosdb"

#echo $env:POSTGRES_PASSWORD

$env:AIRSERVICE_JOBS_SECRET_KEY = "mykey"
$env:API_DEBUG = "True"
$env:API_DOMAIN_NAME = "http://localhost" 
$env:API_PORT = 5000
$env:API_SECRET_KEY = "myapisecretkey"
#$env:DATABASE_URL = "http://localhost" 
$env:DATABASE_URL = "postgresql://viajuntos:password123@localhost:5432/viajuntosdb"
$env:JWT_SECRET_KEY = "myjwtkey"   
$env:MAIL_PASSWORD = "kdbbzkbkpemzfsrd" 
$env:MAIL_USERNAME = "zjqtlwj@gmail.com"
$env:POSTGRES_DB = "viajuntosdb"
$env:POSTGRES_PASSWORD = "password123" 
$env:POSTGRES_PORT = 5432
$env:POSTGRES_USER = "viajuntos"
$env:SQLALCHEMY_DATABASE_URI = "postgresql://viajuntos:password123@localhost:5432/viajuntosdb"
#echo $env:POSTGRES_PASSWORD


# You're working on project viajuntos
# Number: 784363842682  ID: viajuntos-457514 

# > docker images 

# REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
# postgres     9.4       ed5a45034282   5 years ago   251MB

# > docker tag postgres:9.4 gcr.io/viajuntos-457514/postgres:9.4
# > gcloud auth login
# > gcloud config set project viajuntos-457514
# > gcloud auth configure-docker
# > docker push gcr.io/viajuntos-457514/postgres:9.4 
# > gcloud run deploy postgres --image gcr.io/viajuntos-457514/postgres:9.4 --platform managed --region us-central1 --allow-unauthenticated

# > gcloud compute instances create-with-container postgres-vm --container-image=gcr.io/viajuntos-457514/postgres:9.4 --zone=us-central1-a --container-privileged

# Created [https://www.googleapis.com/compute/v1/projects/viajuntos-457514/zones/us-central1-a/instances/postgres-vm].
# NAME         ZONE           MACHINE_TYPE   PREEMPTIBLE  INTERNAL_IP  EXTERNAL_IP   STATUS
# postgres-vm  us-central1-a  n1-standard-1               10.128.0.2   34.30.60.143  RUNNING

# > gcloud compute firewall-rules create allow-postgres --allow tcp:5432 --target-tags=postgres-vm --description="Allow external access to Postgres" --direction=INGRESS --priority=1000 --network=default
# > gcloud compute instances add-tags postgres-vm --tags=postgres-vm --zone=us-central1-a
# > gcloud compute ssh postgres-vm --zone=us-central1-a

# gcloud compute firewall-rules create allow-ssh --allow tcp:22 --target-tags=postgres-vm --description="Allow SSH access"

# > ssh-keygen -t rsa -f C:\Users\92196\.ssh\google_compute_engine_cmd
# > gcloud compute instances add-metadata postgres-vm  --metadata-from-file ssh-keys=C:\Users\92196\.ssh\google_compute_engine_cmd.pub --zone=us-central1-a




# ================ gcloud =======================
# wei286600@cloudshell:~ (viajuntos-457514)$ gcloud compute ssh postgres-vm --zone=us-central1-a

# > gcloud compute ssh postgres-vm --zone=us-central1-a
# WARNING: The private SSH key file for gcloud does not exist.
# WARNING: The public SSH key file for gcloud does not exist.
# WARNING: You do not have an SSH key for gcloud.
# WARNING: SSH keygen will be executed to generate a key.
# This tool needs to create the directory [/home/wei286600/.ssh] before being able to generate SSH keys.

# Do you want to continue (Y/n)?  y

# Generating public/private rsa key pair.
# Enter passphrase (empty for no passphrase): 
# Enter same passphrase again: 
# Your identification has been saved in /home/wei286600/.ssh/google_compute_engine
# Your public key has been saved in /home/wei286600/.ssh/google_compute_engine.pub
# The key fingerprint is:
# SHA256:WfjUPaCJXXCChFRfAsuCEl6ckkYtrtgQ9OWEixlJuR4 wei286600@cs-893679535768-default
# The key's randomart image is:
# +---[RSA 3072]----+
# |o+=+o=.++o+.=    |
# |.=*+B....* X o   |
# | +B+o.. = B . o  |
# |.E.o   . =     . |
# |o+.     S .      |
# |o..              |
# |                 |
# |                 |
# |                 |
# +----[SHA256]-----+

# Updating project ssh metadata...working...Updated [https://www.googleapis.com/compute/v1/projects/viajuntos-457514].                                                                                                                                                                                                              
# Updating project ssh metadata...done.                                                                                                                                                                                                                                                                                             
# Waiting for SSH key to propagate.
# Warning: Permanently added 'compute.2452852793563402883' (ED25519) to the list of known hosts.
#   ########################[ Welcome ]########################
#   #  You have logged in to the guest OS.                    #
#   #  To access your containers use 'docker attach' command  #
#   ###########################################################

# > docker run --name klt-postgres-vm-irhg -e POSTGRES_PASSWORD=password123 -p 5432:5432 -d gcr.io/viajuntos-457514/postgres:9.4
# > docker logs klt-postgres-vm-irhg
# > docker ps



# export from local database
# > pg_dump -U viajuntos -h localhost -p 5432 -d viajuntosdb -f viajuntosdb_20250422.sql
# upload and copy to vm
# > docker cp /home/wei286600/viajuntosdb_20250422.sql klt-postgres-vm-irhg:/tmp/viajuntosdb_20250422.sql

# > docker exec -it klt-postgres-vm-irhg bash
# > psql -U viajuntos -d viajuntosdb -f /tmp/viajuntosdb_20250422.sql