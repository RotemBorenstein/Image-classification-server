import threading

import torch
from PIL import Image
from torchvision import models
from torchvision.models import ResNet18_Weights

state_lock = threading.RLock()
load_started = False
load_finished = threading.Event()
load_thread = None
load_error = None
loaded_model = None
preprocess = None
labels = None


def _load_model():
    global labels, load_error, loaded_model, preprocess

    try:
        weights = ResNet18_Weights.DEFAULT
        model_instance = models.resnet18(weights=weights)
        model_instance.eval()

        preprocess_instance = weights.transforms()
        label_list = weights.meta["categories"]

        with state_lock:
            loaded_model = model_instance
            preprocess = preprocess_instance
            labels = label_list
            load_error = None
    except Exception as exc:
        with state_lock:
            loaded_model = None
            preprocess = None
            labels = None
            load_error = exc
    finally:
        load_finished.set()


def _start_background_load():
    global load_started, load_thread

    with state_lock:
        if load_started:
            return
        load_started = True
        load_thread = threading.Thread(target=_load_model, daemon=True)
        load_thread.start()


def ensure_model_loaded(blocking=True):
    _start_background_load()

    if blocking:
        load_finished.wait()

    with state_lock:
        return loaded_model is not None


def can_classify():
    with state_lock:
        return loaded_model is not None


def classify_image(file):
    """
    Returns list of {name, score} where:
    - scores are probabilities (softmax)
    - sum(scores) <= 1 (top-k normalization)
    """

    image = Image.open(file).convert("RGB")

    if not ensure_model_loaded(blocking=True):
        raise RuntimeError("Classifier unavailable")

    with state_lock:
        model_instance = loaded_model
        preprocess_instance = preprocess
        label_list = labels
        error = load_error

    if model_instance is None or preprocess_instance is None or label_list is None:
        raise RuntimeError("Classifier unavailable") from error

    x = preprocess_instance(image).unsqueeze(0)

    with torch.no_grad():
        logits = model_instance(x)
        probs = torch.softmax(logits, dim=1)[0]

    topk = 5
    values, indices = torch.topk(probs, topk)

    results = []
    total = 0.0

    for i in range(topk):
        score = float(values[i])
        total += score
        results.append(
            {
                "name": label_list[int(indices[i])],
                "score": score,
            }
        )

    if total > 1:
        for result in results:
            result["score"] /= total

    return results


_start_background_load()
