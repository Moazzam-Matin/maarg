"""Seed realistic sample experiments into SQLite using @track."""

from __future__ import annotations

import math
import time
from pathlib import Path

from ui.data import ensure_maarg_importable

ensure_maarg_importable()

from maarg import SQLiteStorage, track  # noqa: E402
from maarg.storage._sqlite import DEFAULT_DB_PATH  # noqa: E402


def _make_training_figure(
    epochs: int,
    learning_rate: float,
    final_acc: float,
    final_loss: float,
):
    """Create a Matplotlib learning curve figure if matplotlib is available."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    xs = list(range(1, epochs + 1))
    losses = [
        final_loss + (1.2 - final_loss) * math.exp(-0.35 * (x - 1) * (learning_rate / 0.01))
        for x in xs
    ]
    accs = [
        final_acc - (final_acc - 0.35) * math.exp(-0.32 * (x - 1) * (learning_rate / 0.01))
        for x in xs
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3.0), dpi=110)
    ax1.plot(xs, losses, marker="o", color="#EF4444", linewidth=2)
    ax1.set_title("Validation Loss")
    ax1.set_xlabel("Epoch")
    ax1.grid(alpha=0.25)

    ax2.plot(xs, accs, marker="o", color="#0194E2", linewidth=2)
    ax2.set_title("Validation Accuracy")
    ax2.set_xlabel("Epoch")
    ax2.set_ylim(0.2, 1.0)
    ax2.grid(alpha=0.25)

    fig.suptitle(f"lr={learning_rate} | acc={final_acc:.3f}", fontsize=10)
    fig.tight_layout()
    return fig


def seed_demo_runs(
    db_path: str | Path = DEFAULT_DB_PATH,
    artifacts_dir: str | Path = Path(".maarg") / "artifacts",
) -> int:
    """
    Populate ``db_path`` with sample ML, RecSys, and RAG experiments via ``@track``.

    Returns the number of runs recorded during seeding.
    """
    storage = SQLiteStorage(db_path=db_path)
    recorded = 0

    @track(experiment="mnist-cnn-sweep", storage=storage, artifacts_dir=artifacts_dir)
    def train_cnn(
        learning_rate: float = 0.01,
        batch_size: int = 64,
        dropout: float = 0.2,
        optimizer: str = "adamw",
        epochs: int = 10,
        simulate_oom: bool = False,
    ):
        if simulate_oom:
            raise RuntimeError(
                f"CUDA out of memory while allocating batch_size={batch_size} tensor"
            )
        lr_penalty = abs(math.log10(learning_rate) + 2.3) * 0.035
        opt_bonus = 0.018 if optimizer == "adamw" else 0.0
        drop_penalty = abs(dropout - 0.25) * 0.08
        accuracy = round(min(0.992, max(0.72, 0.962 + opt_bonus - lr_penalty - drop_penalty)), 4)
        loss = round(max(0.03, 1.0 - accuracy + 0.04), 4)
        f1_score = round(accuracy - 0.008, 4)

        result: dict[str, object] = {
            "accuracy": accuracy,
            "loss": loss,
            "f1_score": f1_score,
        }
        fig = _make_training_figure(epochs, learning_rate, accuracy, loss)
        if fig is not None:
            result["training_curve"] = fig
        return result

    @track(experiment="recsys-eval", storage=storage, artifacts_dir=artifacts_dir)
    def evaluate_ranker(
        embedding_dim: int = 64,
        top_k: int = 10,
        regularization: float = 0.001,
    ):
        base = 0.048 + (embedding_dim / 256) * 0.02 - regularization * 2.0
        return {
            "ndcg": round(base * 2.4, 4),
            "precision_at_k": {
                "5": round(base * 1.15, 4),
                "10": round(base, 4),
            },
            "recall_at_k": {
                "5": round(base * 0.55, 4),
                "10": round(base * 0.92, 4),
            },
        }

    @track(experiment="rag-prompt-bench", storage=storage, artifacts_dir=artifacts_dir)
    def benchmark_rag(
        chunk_size: int = 512,
        top_k: int = 5,
        reranker: bool = True,
        model: str = "gemini-flash",
    ):
        rerank_boost = 0.07 if reranker else 0.0
        faithfulness = round(min(0.98, 0.81 + rerank_boost + (top_k * 0.012)), 4)
        relevancy = round(min(0.97, 0.79 + rerank_boost + (512 / max(chunk_size, 256)) * 0.03), 4)
        latency_ms = round(180 + top_k * 22 + (140 if reranker else 0), 1)
        return {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "latency_ms": latency_ms,
        }

    cnn_configs = [
        {"learning_rate": 0.001, "batch_size": 32, "dropout": 0.2, "optimizer": "sgd", "epochs": 8},
        {"learning_rate": 0.003, "batch_size": 64, "dropout": 0.25, "optimizer": "adamw", "epochs": 10},
        {"learning_rate": 0.005, "batch_size": 64, "dropout": 0.25, "optimizer": "adamw", "epochs": 12},
        {"learning_rate": 0.01, "batch_size": 128, "dropout": 0.3, "optimizer": "adamw", "epochs": 10},
        {"learning_rate": 0.02, "batch_size": 128, "dropout": 0.4, "optimizer": "sgd", "epochs": 8},
        {"learning_rate": 0.005, "batch_size": 256, "dropout": 0.2, "optimizer": "adamw", "epochs": 12},
    ]

    for cfg in cnn_configs:
        res = train_cnn(**cfg)
        _close_fig_if_present(res)
        recorded += 1
        time.sleep(0.005)

    try:
        train_cnn(learning_rate=0.01, batch_size=2048, dropout=0.2, optimizer="adamw", simulate_oom=True)
    except RuntimeError:
        recorded += 1
    time.sleep(0.005)

    recsys_configs = [
        {"embedding_dim": 32, "top_k": 10, "regularization": 0.002},
        {"embedding_dim": 64, "top_k": 10, "regularization": 0.001},
        {"embedding_dim": 128, "top_k": 10, "regularization": 0.0005},
        {"embedding_dim": 256, "top_k": 10, "regularization": 0.001},
    ]
    for cfg in recsys_configs:
        evaluate_ranker(**cfg)
        recorded += 1
        time.sleep(0.005)

    rag_configs = [
        {"chunk_size": 256, "top_k": 3, "reranker": False, "model": "gemini-flash"},
        {"chunk_size": 512, "top_k": 5, "reranker": True, "model": "gemini-flash"},
        {"chunk_size": 512, "top_k": 8, "reranker": True, "model": "gemini-pro"},
        {"chunk_size": 1024, "top_k": 5, "reranker": False, "model": "gemini-pro"},
    ]
    for cfg in rag_configs:
        benchmark_rag(**cfg)
        recorded += 1
        time.sleep(0.005)

    return recorded


def _close_fig_if_present(result: object) -> None:
    if isinstance(result, dict) and "training_curve" in result:
        try:
            import matplotlib.pyplot as plt

            plt.close(result["training_curve"])
        except Exception:  # noqa: BLE001
            pass
