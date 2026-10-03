"""Embed works the way OpenAlex does for the SDG head: Qwen3-Embedding-0.6B over title, abstract and venue.

  pip install torch "sentence-transformers>=3"
  python -m classifier.fetch_works --ids ids.txt --out works.jsonl
  python -m classifier.embed --input works.jsonl --out vectors.npz
  python -m classifier.head --vectors vectors.npz --out scores.jsonl

OpenAlex embeds every work with a title, in production, through Databricks' hosted copy of Qwen3-Embedding-0.6B
(https://huggingface.co/Qwen/Qwen3-Embedding-0.6B, Apache 2.0), as 1024-d unit vectors. The text is exactly
work_text() below, cut at 2,000 characters, embedded bare (the model's instruction prefix is for queries only). This
script runs the open weights locally with the same text.

We have not measured how closely local vectors match the hosted ones (TODO: compare on the 2,598 committee works,
whose served vectors ship in benchmarks/data/committee/vectors.npz). For an exact replication of the benchmarks, score
the shipped vectors; use this script for new works.
"""
import argparse
import json

import numpy as np

MODEL = "Qwen/Qwen3-Embedding-0.6B"
MAX_CHARS = 2000


def work_text(w):
    """The production embedding text: 'Title: ...' + '\\n\\nAbstract: ...' + '\\n\\nVenue: ...', first 2,000 characters."""
    t = "Title: " + (w.get("title") or "")
    if w.get("abstract"):
        t += "\n\nAbstract: " + w["abstract"]
    if w.get("venue"):
        t += "\n\nVenue: " + w["venue"]
    return t[:MAX_CHARS]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True, help="JSONL from classifier.fetch_works")
    ap.add_argument("--out", required=True, help=".npz with ids (int64) and X (n x 1024 float32)")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--device", default=None, help="cuda, mps or cpu (default: whatever torch finds)")
    a = ap.parse_args()
    from sentence_transformers import SentenceTransformer

    works = [w for w in (json.loads(l) for l in open(a.input) if l.strip()) if "error" not in w and w.get("title")]
    model = SentenceTransformer(MODEL, device=a.device)
    X = model.encode([work_text(w) for w in works], batch_size=a.batch, normalize_embeddings=True,
                     show_progress_bar=True, convert_to_numpy=True).astype(np.float32)
    ids = np.asarray([int(w["work_id"].lstrip("W")) for w in works], np.int64)
    np.savez_compressed(a.out, ids=ids, X=X)
    print(f"wrote {a.out}: {len(ids):,} vectors of {X.shape[1]} dimensions")


if __name__ == "__main__":
    main()
