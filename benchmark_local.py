"""
Local Model Benchmark Script (`benchmark_local.py`)

Measures actual latency, token throughput (tokens/sec), and AST validation pass-rate
for `qwen2.5-coder:3b` running on Person A's NVIDIA RTX 2050 GPU (4GB VRAM).
"""

import asyncio
import json
import os
import sys
import time
import logging
from typing import List, Dict, Any

from backend.ai.providers.local_provider import LocalOllamaProvider
from backend.core.validator import ASTSafetyValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Benchmark")

BENCHMARK_PROMPTS = [
    "Write a Python evaluate(tx) function to flag transactions over $1000 from accounts younger than 14 days.",
    "Write a Python evaluate(tx) function to flag international transactions over $2500 in merchant_category 'crypto'.",
    "Write a Python evaluate(tx) function to flag transactions from location 'MUM-JMT' where account_age_days < 7.",
    "Write a Python evaluate(tx) function to flag transactions over $5000 on category 'electronics'.",
    "Write a Python evaluate(tx) function to flag transactions where is_international is True and amount > 500.",
    "Write a Python evaluate(tx) function to flag transactions where account_age_days < 3 and amount > 100.",
    "Write a Python evaluate(tx) function to flag transactions with merchant_category 'wire_transfer' over $3000.",
    "Write a Python evaluate(tx) function to flag transactions from 'DEL-NUH' with amount > 1500.",
    "Write a Python evaluate(tx) function to flag transactions with device_id matching dev_9999 and amount > 1000.",
    "Write a Python evaluate(tx) function to flag international transactions in 'luxury_goods' over $4000."
]

SYSTEM_PROMPT = """
You are an expert fraud detection rule generator.
Write ONLY valid Python code containing a single function:
def evaluate(tx):
    # logic returning bool
DO NOT include any markdown block quotes, imports, or explanations outside the function.
Access properties as attributes on `tx` using dot notation (e.g., `tx.amount > 1000 and tx.account_age_days < 14`), NOT dictionary keys (do NOT use `tx['amount']`).
Allowed tx fields: id, account_id, amount, location, timestamp, account_age_days, merchant_category, device_id, is_international.
"""


async def run_benchmark():
    logger.info("Initializing Local LLM Benchmark for qwen2.5-coder:3b...")
    provider = LocalOllamaProvider()
    validator = ASTSafetyValidator()

    # 1. Health check
    is_healthy = await provider.check_health()
    if not is_healthy:
        logger.error(
            "Ollama server is NOT running at http://localhost:11434. "
            "Please start Ollama (`ollama serve`) and pull the model (`ollama pull qwen2.5-coder:3b`) to run the benchmark."
        )
        sys.exit(1)

    logger.info("Ollama service verified. Starting 10-prompt benchmark run...")

    results: List[Dict[str, Any]] = []
    total_tokens = 0
    total_eval_time = 0.0
    passed_ast_count = 0

    for i, prompt in enumerate(BENCHMARK_PROMPTS, 1):
        logger.info(f"[{i}/10] Generating rule for prompt: '{prompt[:60]}...'")
        try:
            metrics = await provider.generate_with_metrics(prompt=prompt, system_prompt=SYSTEM_PROMPT)
            raw_code = metrics["response"]

            # Clean markdown formatting if model output wraps in triple backticks
            clean_code = raw_code.replace("```python", "").replace("```", "").strip()

            # Run AST Safety Validator on generated code
            val_res = validator.validate(clean_code)

            if val_res.valid:
                passed_ast_count += 1

            sample_result = {
                "prompt_index": i,
                "prompt": prompt,
                "latency_sec": metrics["total_duration_sec"],
                "eval_duration_sec": metrics["eval_duration_sec"],
                "eval_tokens": metrics["eval_count"],
                "tokens_per_sec": metrics["tokens_per_second"],
                "ast_valid": val_res.valid,
                "ast_error": val_res.error,
                "generated_code": clean_code
            }
            results.append(sample_result)

            total_tokens += metrics["eval_count"]
            total_eval_time += metrics["eval_duration_sec"]

            logger.info(
                f"    -> Latency: {metrics['total_duration_sec']}s | "
                f"TPS: {metrics['tokens_per_second']} tokens/sec | "
                f"AST Valid: {val_res.valid}"
            )

        except Exception as e:
            logger.error(f"    -> Prompt {i} failed: {e}")
            results.append({
                "prompt_index": i,
                "prompt": prompt,
                "error": str(e),
                "ast_valid": False
            })

    avg_tps = round(total_tokens / total_eval_time, 2) if total_eval_time > 0 else 0.0
    ast_pass_rate = round((passed_ast_count / len(BENCHMARK_PROMPTS)) * 100, 1)

    summary = {
        "model": provider.model_name,
        "device_target": "NVIDIA RTX 2050 (4GB VRAM)",
        "total_prompts": len(BENCHMARK_PROMPTS),
        "avg_tokens_per_sec": avg_tps,
        "ast_pass_rate_pct": ast_pass_rate,
        "total_tokens_generated": total_tokens,
        "samples": results
    }

    # Save to docs
    os.makedirs("docs", exist_ok=True)
    report_path = "docs/benchmark_results.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)
    logger.info(f"BENCHMARK COMPLETE")
    logger.info(f"Model: {provider.model_name}")
    logger.info(f"Average Throughput: {avg_tps} tokens/sec")
    logger.info(f"AST Validator Pass Rate: {ast_pass_rate}% ({passed_ast_count}/{len(BENCHMARK_PROMPTS)})")
    logger.info(f"Full benchmark details saved to {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
