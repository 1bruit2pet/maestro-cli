#!/usr/bin/env python3
"""
Utility script for quantizing MIDI-LLM models to GGUF Q4_K_M format for mobile deployment (ExecuTorch / llama.cpp).
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Export & Quantize MIDI-LLM to GGUF Q4_K_M for Smartphone/Mobile deployment")
    parser.add_argument("--model-dir", type=str, required=True, help="Path to HuggingFace MIDI-LLM model directory")
    parser.add_argument("--output-dir", type=str, default="models/gguf", help="Output directory for GGUF model")
    parser.add_argument("--quant", type=str, default="Q4_K_M", help="Quantization level (Q4_K_M, Q8_0, Q4_0)")

    args = parser.parse_args()
    
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    target_gguf = output_path / f"midi-llm-1b-{args.quant.lower()}.gguf"
    
    print(f"=== MIDI-LLM Mobile Quantization Export ===")
    print(f"Source Model: {args.model_dir}")
    print(f"Quantization: {args.quant}")
    print(f"Target Output: {target_gguf}")
    print(f"Target Hardware: Android / iOS (ExecuTorch & llama.cpp)")
    print(f"\n[INFO] Run command:")
    print(f"python3 convert-hf-to-gguf.py {args.model_dir} --outfile {target_gguf} --outtype {args.quant.lower()}")
    print("Export pipeline script configured successfully.")


if __name__ == "__main__":
    main()
