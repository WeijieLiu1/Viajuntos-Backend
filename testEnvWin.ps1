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