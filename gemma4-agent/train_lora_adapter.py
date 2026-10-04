#!/usr/bin/env python3
"""
Post-Training LoRA Adapter Script for Google Gemma 4 (31B IT).

Fine-tunes Gemma 4 to specialize in SWE task resolution using:
  1. Historical Bug Patterns & Archetypes from skills/bug-lookup/resources/seed_bugs.json
  2. Analyzed Task Categorization (Bug Fix, Feature, Refactor, Dependency, etc.)
  3. Surgical patch generation following UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE

Outputs compliant PEFT LoRA adapter:
  adapters/main_lora/
  ├── adapter_config.json
  └── adapter_model.safetensors
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent


def load_training_data(seed_bugs_path: Path, csv_path: Path = None) -> List[Dict[str, Any]]:
    """Loads bug lookup dataset and optional task analysis CSV into paired training examples."""
    examples = []
    
    if seed_bugs_path.exists():
        bugs = json.loads(seed_bugs_path.read_text(encoding="utf-8"))
        for b in bugs:
            examples.append({
                "category": b.get("category", "Bug Fix / Validation"),
                "issue": b.get("issue_pattern", ""),
                "flow": b.get("repository_pattern", ""),
                "symptoms": b.get("symptoms", []),
                "functions": b.get("relevant_functions", []),
                "fix_pattern": b.get("fix_pattern", ""),
                "patch": b.get("patch", ""),
            })

    if csv_path and csv_path.exists():
        import csv
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                examples.append({
                    "category": row.get("task_category", "Bug Fix / Validation"),
                    "issue": row.get("problem_statement", row.get("issue", "")),
                    "flow": row.get("flow", ""),
                    "symptoms": [row.get("error_message", "")] if row.get("error_message") else [],
                    "functions": [row.get("target_function", "")] if row.get("target_function") else [],
                    "fix_pattern": row.get("fix_summary", row.get("fix_pattern", "")),
                    "patch": row.get("patch", row.get("solution", "")),
                })

    return examples


def format_gemma_chat(example: Dict[str, Any], system_prompt: str) -> str:
    """Formats a single training example into Gemma 4 native chat template format."""
    symptoms_str = ", ".join(example.get("symptoms", []))
    funcs_str = ", ".join(example.get("functions", []))
    
    user_content = (
        f"{system_prompt}\n\n"
        f"Problem Statement:\n{example['issue']}\n"
    )
    if symptoms_str:
        user_content += f"Symptoms: {symptoms_str}\n"

    model_thought = (
        f"1. CATEGORY: {example['category']}\n"
        f"2. LOCALIZE: Trace execution flow: {example['flow']}. Focus on functions: {funcs_str}.\n"
        f"3. BUG LOOKUP MATCH: {example['fix_pattern']}\n"
        f"4. PLAN: Apply minimal surgical patch to implementation file without modifying test files.\n"
    )

    model_content = (
        f"```thought\n{model_thought}```\n"
        f"Identified issue in category '{example['category']}'. Applying surgical patch:\n\n"
        f"```diff\n{example['patch']}\n```"
    )

    formatted = (
        f"<start_of_turn>user\n{user_content}<end_of_turn>\n"
        f"<start_of_turn>model\n{model_content}<end_of_turn>\n"
    )
    return formatted


def train_lora(
    base_model_name: str,
    output_dir: Path,
    dataset_records: List[Dict[str, Any]],
    r: int = 16,
    lora_alpha: int = 32,
    epochs: int = 3,
    batch_size: int = 2,
    learning_rate: float = 2e-4,
):
    """Executes PEFT QLoRA training using PyTorch, Transformers, and TRL."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import Dataset
    except ImportError:
        print("[ERROR] Required training libraries missing. Please run:")
        print("  pip install torch transformers peft trl datasets bitsandbytes accelerate")
        sys.exit(1)

    print(f"[INFO] Loading tokenizer for {base_model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[INFO] Formatting {len(dataset_records)} training samples...")
    system_prompt = (ROOT / "prompts" / "system.md").read_text(encoding="utf-8")
    formatted_texts = [format_gemma_chat(rec, system_prompt) for rec in dataset_records]
    hf_dataset = Dataset.from_dict({"text": formatted_texts})

    print(f"[INFO] Loading base model {base_model_name} in 4-bit precision...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=4096, padding="max_length")

    tokenized_dataset = hf_dataset.map(tokenize_fn, batched=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        warmup_ratio=0.03,
        learning_rate=learning_rate,
        fp16=False,
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
    )

    from transformers import Trainer, DataCollatorForLanguageModeling
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print("[INFO] Starting LoRA fine-tuning...")
    trainer.train()

    print(f"[INFO] Saving PEFT LoRA adapter to {output_dir}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(output_dir))
    print("[SUCCESS] LoRA adapter post-training complete!")


def bootstrap_dummy_adapter(output_dir: Path):
    """Initializes a valid zero-weight safetensors PEFT adapter structure for local verification."""
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_cfg = {
        "alpha_pattern": {},
        "auto_mapping": None,
        "base_model_name_or_path": "google/gemma-4-31b-it",
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "init_lora_weights": True,
        "layer_replication": None,
        "layers_pattern": None,
        "layers_to_transform": None,
        "loftq_config": {},
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "megatron_config": None,
        "megatron_core": "megatron.core",
        "modules_to_save": None,
        "peft_type": "LORA",
        "r": 16,
        "rank_pattern": {},
        "revision": None,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "task_type": "CAUSAL_LM",
        "use_dora": False,
        "use_rslora": False,
    }
    (output_dir / "adapter_config.json").write_text(json.dumps(adapter_cfg, indent=2), encoding="utf-8")

    import struct
    header = json.dumps({"__metadata__": {"format": "pt"}}).encode("utf-8")
    binary_content = struct.pack("<Q", len(header)) + header
    (output_dir / "adapter_model.safetensors").write_bytes(binary_content)
    print(f"[INFO] Bootstrapped valid PEFT adapter structure at: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Post-train Gemma 4 LoRA adapter using bug lookup dataset")
    parser.add_argument("--base-model", type=str, default="google/gemma-4-31b-it", help="Hugging Face base model")
    parser.add_argument("--seed-bugs", type=str, default="skills/bug-lookup/resources/seed_bugs.json", help="Path to seed bugs JSON")
    parser.add_argument("--tasks-csv", type=str, default=None, help="Optional gemma4_tasks_analyzed.csv path")
    parser.add_argument("--output-dir", type=str, default="adapters/main_lora", help="Output directory for LoRA adapter")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--bootstrap-only", action="store_true", help="Initialize valid PEFT directory without full GPU training")
    args = parser.parse_args()

    out_path = ROOT / args.output_dir

    if args.bootstrap_only:
        bootstrap_dummy_adapter(out_path)
        return

    seed_path = ROOT / args.seed_bugs
    csv_path = Path(args.tasks_csv) if args.tasks_csv else None
    dataset_records = load_training_data(seed_path, csv_path)

    print(f"[INFO] Loaded {len(dataset_records)} training records.")
    train_lora(
        base_model_name=args.base_model,
        output_dir=out_path,
        dataset_records=dataset_records,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
