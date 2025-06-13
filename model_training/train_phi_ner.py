# model_training/train_phi_ner.py

from transformers import AutoTokenizer, AutoModelForTokenClassification, TrainingArguments, Trainer, DataCollatorForTokenClassification
from datasets import load_dataset
import evaluate
import numpy as np
from utils import tokenize_and_align_labels, label_list, label2id, id2label

# Step 1: Load the CONLL-2003 dataset, which contains named entity labels for people, organizations, etc.
# This is a standard dataset for NER tasks and provides labeled tokens we can use to train on PII-like patterns.
raw_datasets = load_dataset("conll2003", trust_remote_code=True)

# Step 2: Load the tokenizer for the base model (BERT in this case).
# The tokenizer splits input text into tokens that match the model's expectations.
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

# Step 3: Tokenize the dataset and align labels for each token.
# This transforms raw text and entity annotations into token-level inputs the model can train on.
tokenized_datasets = raw_datasets.map(
    lambda x: tokenize_and_align_labels(x, tokenizer),
    batched=True
)

# Step 4: Load a pretrained BERT model and attach a classification head for token level prediction.
# We specify how many entity classes there are and how to map between class IDs and names.
model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-cased",
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id
)

# Step 5: Define training hyperparameters and behavior.
# This includes evaluation strategy, batch size, learning rate, and where to save model outputs.
args = TrainingArguments(
    output_dir="./phi-bert-model",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=10,
    report_to="none"
)

# Step 6: Create a data collator that batches tokenized examples for training.
# This ensures padding and label alignment is handled correctly in training batches.
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

# Step 7: Load evaluation metric for NER tasks.
# We use seqeval to calculate precision, recall, and F1 scores for entity recognition.
metric = evaluate.load("seqeval")

# Step 8: Define a metric function to compute evaluation metrics after each epoch.
def compute_metrics(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)
    true_labels = [[label_list[l] for l in label if l != -100] for label in labels]
    true_preds = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    return metric.compute(predictions=true_preds, references=true_labels)

# Step 9: Create and configure the Hugging Face Trainer.
# This wraps our model, data, tokenizer, and training args into a training loop.
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics
)

# Step 10: Train the model using the provided dataset and settings.
trainer.train()

# Step 11: Save the final trained model and tokenizer to disk for reuse or deployment.
trainer.save_model("phi-bert-model")
tokenizer.save_pretrained("phi-bert-model")