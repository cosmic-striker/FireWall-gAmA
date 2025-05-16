from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

model_name = "gates04/DistilBERT-Network-Intrusion-Detection"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

input_data = ["Sample network log entry"]

inputs = tokenizer(input_data, padding=True, truncation=True, return_tensors="pt")

with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=-1)

print(predictions)
