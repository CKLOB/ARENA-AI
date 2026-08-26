"""학습 + 백테스트. `python -m app.mlops.train` 으로 실행한다.

시계열이므로 랜덤 split 을 쓰지 않는다. 날짜로 정렬해 뒤쪽을 홀드아웃으로 남긴다.
랜덤으로 나누면 미래 정보가 학습에 새어 AUC 가 비현실적으로 높게 나온다.
"""

import json
import logging
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

from app.mlops.dataset import DEFAULT_HORIZON, build_dataset
from app.mlops.features import CATEGORICAL_FEATURES, FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "trading_lgbm.txt"
METRICS_PATH = MODEL_DIR / "metrics.json"

HOLDOUT_RATIO = 0.2
PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "learning_rate": 0.03,
    "num_leaves": 15,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
}
NUM_ROUNDS = 500
EARLY_STOPPING = 50


def split_by_date(dataset: pd.DataFrame, ratio: float = HOLDOUT_RATIO):
    """날짜 기준 시계열 분할. 경계 날짜는 홀드아웃에 넣어 같은 날이 양쪽에 걸치지 않게 한다."""
    dates = dataset["date"].sort_values().unique()
    cutoff = dates[int(len(dates) * (1 - ratio))]
    train = dataset[dataset["date"] < cutoff]
    holdout = dataset[dataset["date"] >= cutoff]
    return train, holdout, pd.Timestamp(cutoff)


def evaluate(booster: lgb.Booster, frame: pd.DataFrame) -> dict:
    probability = booster.predict(frame[FEATURE_NAMES])
    label = frame["label"].astype(int)
    metrics = {
        "rows": len(frame),
        "positive_rate": round(float(label.mean()), 4),
        "auc": round(float(roc_auc_score(label, probability)), 4),
        "accuracy": round(float(accuracy_score(label, probability >= 0.5)), 4),
    }
    # 임계값별 정밀도 - THRESHOLDS 튜닝의 근거가 된다.
    for threshold in (0.55, 0.6, 0.65, 0.7):
        picked = probability >= threshold
        metrics[f"precision@{threshold}"] = (
            round(float(label[picked].mean()), 4) if picked.any() else None
        )
        metrics[f"coverage@{threshold}"] = round(float(picked.mean()), 4)
    return metrics


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    dataset = build_dataset(horizon=DEFAULT_HORIZON)
    train, holdout, cutoff = split_by_date(dataset)
    logger.info(
        "\n전체 %d행 | 학습 %d행 | 홀드아웃 %d행 | 분할 기준 %s",
        len(dataset), len(train), len(holdout), cutoff.date(),
    )

    train_set = lgb.Dataset(
        train[FEATURE_NAMES], train["label"].astype(int), categorical_feature=CATEGORICAL_FEATURES
    )
    valid_set = lgb.Dataset(
        holdout[FEATURE_NAMES], holdout["label"].astype(int), reference=train_set
    )
    booster = lgb.train(
        PARAMS,
        train_set,
        num_boost_round=NUM_ROUNDS,
        valid_sets=[valid_set],
        callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
    )

    # 학습과 추론의 계약. 어긋난 모델을 저장하면 서비스가 조용히 틀린 예측을 낸다.
    assert booster.feature_name() == FEATURE_NAMES, (
        f"피처 순서 불일치: {booster.feature_name()} != {FEATURE_NAMES}"
    )

    metrics = {
        "horizon": DEFAULT_HORIZON,
        "best_iteration": booster.best_iteration,
        "cutoff": str(cutoff.date()),
        "features": FEATURE_NAMES,
        "train": evaluate(booster, train),
        "holdout": evaluate(booster, holdout),
    }

    MODEL_DIR.mkdir(exist_ok=True)
    booster.save_model(str(MODEL_PATH), num_iteration=booster.best_iteration)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")

    logger.info("\n%s", json.dumps(metrics, indent=2, ensure_ascii=False))
    logger.info("\n모델 저장: %s", MODEL_PATH)
    holdout_auc = metrics["holdout"]["auc"]
    if holdout_auc < 0.52:
        logger.warning("홀드아웃 AUC %.4f - 무작위와 다를 바 없다. 붙이지 마라.", holdout_auc)
    elif holdout_auc > 0.70:
        logger.warning("홀드아웃 AUC %.4f - 너무 높다. 데이터 누수를 의심하라.", holdout_auc)


if __name__ == "__main__":
    main()
