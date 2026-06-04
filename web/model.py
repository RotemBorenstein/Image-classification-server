import torch
from torchvision import models
from torchvision.models import ResNet18_Weights
from PIL import Image

# load pretrained model once at startup
weights = ResNet18_Weights.DEFAULT
model = models.resnet18(weights=weights)
model.eval()

preprocess = weights.transforms()
labels = weights.meta["categories"]


def classify_image(file):
    """
    Returns list of {name, score} where:
    - scores are probabilities (softmax)
    - sum(scores) <= 1 (top-k normalization)
    """

    image = Image.open(file).convert("RGB")
    x = preprocess(image).unsqueeze(0)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]

    topk = 5
    values, indices = torch.topk(probs, topk)

    results = []
    total = 0.0

    for i in range(topk):
        score = float(values[i])
        total += score

        results.append({
            "name": labels[int(indices[i])],
            "score": score
        })

    # optional safety: ensure <= 1 due to spec
    if total > 1:
        for r in results:
            r["score"] /= total

    return results