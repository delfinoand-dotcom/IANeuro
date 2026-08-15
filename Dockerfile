# Usa una imagen oficial y ligera de Python
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /env

# Copia e instala las dependencias de tu proyecto
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de tu proyecto al contenedor
COPY . .
#ADD . /env

# Expone el puerto en el que tu aplicación web está escuchando (por ejemplo, 5000 o 8000)
EXPOSE 8000

#Define enviroment variable
ENV NAME World

# Comando para ejecutar tu página/aplicación (cambiar 'main.py' por tu archivo principal)
CMD ["python", "main.py"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
