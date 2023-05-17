$env:AIRSERVICE_JOBS_SECRET_KEY = "mykey"
$env:API_DEBUG = "True"
$env:API_DOMAIN_NAME = "http://localhost" 
$env:API_PORT = 5000
$env:API_SECRET_KEY = "myapisecretkey"
#$env:DATABASE_URL = "http://localhost" 
$env:DATABASE_URL = "mysql://postgre:mypassword@localhost/mydatabase"
$env:JWT_SECRET_KEY = "myjwtkey"   
$env:MAIL_PASSWORD = "kdbbzkbkpemzfsrd" 
$env:MAIL_USERNAME = "zjqtlwj@gmail.com"
$env:POSTGRES_DB = "mydatabase"
$env:POSTGRES_PASSWORD = "mypassword" 
$env:POSTGRES_PORT = 5432
$env:POSTGRES_USER = "postgre"
#$env:DATABASE_URL=mysql://username:password@hostname/databasename
$env:SQLALCHEMY_DATABASE_URI = "mysql://postgre:mypassword@localhost/mydatabase"
#echo $env:POSTGRES_PASSWORD