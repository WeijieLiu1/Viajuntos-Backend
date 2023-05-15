FROM python:3.8-slim

# Copiar nuestro fichero de dependencias
COPY ./requirements.txt /tmp/requirements.txt

# Actualizar pip y instalar dependencias
RUN pip install -U pip wheel setuptools
RUN pip install -r /tmp/requirements.txt

# Configurar variables de entorno
ENV AIRSERVICE_JOBS_SECRET_KEY="mykey"  
ENV API_DEBUG="True"
ENV API_DOMAIN_NAME="http://localhost"  
ENV API_PORT=5000  
ENV API_SECRET_KEY="myapisecretkey"
ENV DATABASE_URL="http://localhost"   
ENV JWT_SECRET_KEY="myjwtkey" 
ENV MAIL_PASSWORD="kdbbzkbkpemzfsrd"   
ENV MAIL_USERNAME="zjqtlwj@gmail.com"
ENV POSTGRES_DB="mydatabase"  
ENV POSTGRES_PASSWORD="mypassword"
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER="postgre" 
#ENV SQLALCHEMY_DATABASE_URI = 
# Copiar el código de nuestra app para que se pueda ejecutar
COPY ./wsgi.py /wsgi.py
COPY ./config.py /config.py
COPY ./app /app
COPY ./migrations /migrations
COPY ./testEnvWin.ps1 /testEnvWin.ps1
COPY ./testEnv.sh /testEnv.sh
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
COPY ./manage.py  /manage.py 
RUN ./docker-entrypoint.sh
WORKDIR /
CMD ["python3", "wsgi.py"]