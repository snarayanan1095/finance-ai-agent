FROM python:3.9-slim
ARG BUILD_ID=1        # <— increment every rebuild
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "health_check.py"]