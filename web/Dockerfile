FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python -c "from torchvision import models; from torchvision.models import ResNet18_Weights; models.resnet18(weights=ResNet18_Weights.DEFAULT)"

EXPOSE 5000

CMD ["python", "app.py"]
