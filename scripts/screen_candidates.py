#!/usr/bin/env python3
"""Recommend accept/reject decisions for tracker candidate batches.

The policy is intentionally precision-oriented. It accepts candidates from
core systems venues or titles with an explicit AI infrastructure contribution.
Human batches require review. The scheduled workflow may automatically apply
only accept decisions; reject decisions remain unrecorded without human review.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


CORE_SYSTEMS_VENUES = {
    "MLSys",
    "OSDI",
    "SOSP",
    "EuroSys",
    "USENIX ATC",
    "SoCC",
    "Middleware",
    "NSDI",
    "SIGCOMM",
    "SC",
    "HPDC",
    "ASPLOS",
    "ISCA",
    "MICRO",
    "HPCA",
    "TOCS",
    "TPDS",
}

HARD_APPLICATION_PATTERN = re.compile(
    r"medical|disease|healthcare|sentiment|stock|financial|"
    r"autonomous driv|agricultur|emotion recognition|drug design|molecule|"
    r"protein|\brobot(?:ic|ics)?\b|earth system|treatment effect",
    re.IGNORECASE,
)

RECOMMENDER_PATTERN = re.compile(r"recommend(?:ation|er)", re.IGNORECASE)
RECOMMENDER_INFRA_PATTERN = re.compile(
    r"serving|inference accelerat|\bGPU\b|distributed training|stream management|"
    r"deployment|throughput|latency|resource|system architecture|microservice|"
    r"embedding communication|in-memory embedding database",
    re.IGNORECASE,
)

AMBIGUOUS_INFERENCE_PATTERN = re.compile(
    r"membership inference|dataset inference|type inference|causal inference|"
    r"inference-time (?:reasoning|alignment)|treatment effect|"
    r"inference attack|stages of inference",
    re.IGNORECASE,
)

AI_INFRA_CONTEXT_PATTERN = re.compile(
    r"\b(?:AI|ML|LLMs?|GPU|NPU|PIM|RDMA|RoCE|DNN|MoE|Kubernetes)\b|"
    r"language model|large model|foundation model|neural network|deep learning|"
    r"vision-language model|\bVLMs?\b|"
    r"machine learning|model (?:training|serving|inference|compression)|"
    r"compress\w*.{0,30}(?:model|parameter)|KV ?Cache|"
    r"mixture.of.experts|\binference\b|\btraining\b|\baccelerator\w*\b|"
    r"\bcollective\b|parallel attention|tensor program|"
    r"distributed training|parallel training|"
    r"(?:tensor|pipeline|sequence|context|expert|data|model) parallel|"
    r"quantiz|speculative decod",
    re.IGNORECASE,
)

NON_ARCHIVAL_TITLE_PATTERN = re.compile(
    r"student abstract|reproducibility report|^position:",
    re.IGNORECASE,
)

INFRA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bserv(?:e|es|ed|ing)\b",
        r"distributed.{0,40}training|training.{0,40}distributed",
        r"parallel.{0,40}training|training.{0,40}parallel",
        r"training (?:system|infrastructure|cluster)",
        r"training.{0,50}(?:GPU|accelerator|memory|communication|schedul|scalab|throughput|fault|reliab)",
        r"(?:GPU|accelerator|memory|communication|schedul|scalab|throughput|fault|reliab).{0,50}training",
        r"\binference\b.{0,50}(?:system|engine|accelerat|efficient|throughput|latency|hardware|memory|cache|schedul|parallel|distributed|cloud|GPU|CPU|NPU|PIM|quantiz|compress|offload|edge|heterogeneous|real-time|precision)",
        r"(?:system|engine|accelerat|efficient|throughput|latency|hardware|memory|cache|schedul|parallel|distributed|cloud|GPU|CPU|NPU|PIM|quantiz|compress|offload|edge|heterogeneous|real-time|precision).{0,50}\binference\b",
        r"GPU.{0,50}(?:schedul|resource|cluster|sharing|utilization|memory|training|inference|kernel|orchestrat)",
        r"(?:schedul|resource|cluster|sharing|utilization|memory|training|inference|kernel|orchestrat).{0,50}GPU",
        r"collective communication|all[- ]?reduce|all[- ]?to[- ]?all|\bRDMA\b|\bRoCE\b|Kubernetes",
        r"(?:tensor|pipeline|sequence|context|expert|data|model) parallel(?:ism)?",
        r"KV cache|speculative decod|lookahead decod|multi-token.{0,20}decod",
        r"(?:quantiz|compress).{0,60}(?:LLM|language model|transformer|VLM|vision-language|inference|serving|deployment|on-device|edge|accelerator|hardware|neural network)",
        r"(?:LLM|language model|transformer|VLM|vision-language|inference|serving|deployment|on-device|edge|accelerator|hardware|neural network).{0,60}(?:quantiz|compress)",
        r"(?:mixture.of.experts|\bMoE\b).{0,60}(?:training|inference|serving|parallel|routing|load|system|efficien|scal)",
        r"(?:training|inference|serving|parallel|routing|load|system|efficien|scal).{0,60}(?:mixture.of.experts|\bMoE\b)",
        r"long.context.{0,60}(?:training|inference|serving|attention|memory|compress|system|efficien|scal|schedul)",
        r"(?:training|inference|serving|attention|memory|compress|system|efficien|scal|schedul).{0,60}long.context",
        r"(?:accelerator|PIM|NPU|hardware.software co.design|offload|memory management).{0,60}(?:LLM|language model|model training|model inference|neural network)",
        r"(?:LLM|language model|model training|model inference|neural network).{0,60}(?:accelerator|PIM|NPU|hardware.software co.design|offload|memory management)",
        r"(?:fault|reliab|monitor|observab|diagnos).{0,60}(?:training|GPU|AI system|cluster|serving|infrastructure|RDMA)",
        r"(?:performance|energy|throughput|latency|system|hardware).{0,40}benchmark",
        r"benchmark.{0,40}(?:performance|energy|throughput|latency|system|hardware|inference serving|training system)",
        r"(?:serverless|cloud).{0,60}(?:LLM|model training|model inference|serving)",
        r"(?:schedul|resource management|load balan).{0,60}(?:LLM|language model|model training|model inference|AI workload|GPU)",
        r"communication.efficient.{0,60}(?:training|LLM|language model|DNN|neural network)",
        r"(?:memory.efficient|throughput|latency).{0,60}(?:LLM|language model|training|inference|serving)",
        r"(?:LLM|language model).{0,40}(?:routing|SLO|gateway|hot.swap|cold start)",
        r"(?:routing|SLO|gateway|hot.swap|cold start).{0,40}(?:LLM|language model)",
        r"(?:4-bit|low-bit|BFP|narrow precision).{0,40}(?:LLM|language model)",
    ]
]


def screen_candidate(candidate: dict) -> tuple[str, str]:
    title = str(candidate.get("title", "")).strip()
    venue = str(candidate.get("venue", "")).strip()
    if NON_ARCHIVAL_TITLE_PATTERN.search(title):
        return "reject", "non-archival, position, student, or reproducibility-report item"
    if venue in CORE_SYSTEMS_VENUES and AI_INFRA_CONTEXT_PATTERN.search(title):
        return "accept", "AI Infra candidate from a core systems venue"

    if HARD_APPLICATION_PATTERN.search(title):
        return "reject", "application-focused paper without a direct infrastructure contribution"
    if RECOMMENDER_PATTERN.search(title) and not RECOMMENDER_INFRA_PATTERN.search(title):
        return "reject", "recommender application without an operational infrastructure contribution"

    has_infra_signal = any(pattern.search(title) for pattern in INFRA_PATTERNS)
    if has_infra_signal and not AMBIGUOUS_INFERENCE_PATTERN.search(title):
        return "accept", "title states a direct AI infrastructure contribution"
    return "reject", "insufficient direct AI infrastructure evidence in title and venue metadata"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="YAML produced by tracker export_candidates.py")
    parser.add_argument("--output", type=Path, required=True, help="Decision YAML")
    args = parser.parse_args()

    payload = yaml.safe_load(args.input.read_text(encoding="utf-8")) or {}
    candidates = payload.get("papers", [])
    decisions = []
    for candidate in candidates:
        decision, reason = screen_candidate(candidate)
        decisions.append({**candidate, "decision": decision, "reason": reason})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump({"decisions": decisions}, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    accepted = sum(item["decision"] == "accept" for item in decisions)
    print(f"Screened {len(decisions)} candidates: {accepted} accept, {len(decisions) - accepted} reject")


if __name__ == "__main__":
    main()
