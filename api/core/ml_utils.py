from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from .config import (
	CASHOUT_THRESHOLD,
	HIGH_RISK_THRESHOLD,
	HORIZON_HOURS,
	INCASSATION_PLANNED_PCT,
	INCASSATION_URGENT_PCT,
	LOW_BALANCE_METRIC_PCT,
	LOW_CASH_PCT,
	MIN_HISTORY_STEPS,
	WARNING_CASH_PCT,
)


def risk_label(prob: float, medium_threshold: float | None = None) -> str:
	med = CASHOUT_THRESHOLD if medium_threshold is None else medium_threshold
	if prob >= HIGH_RISK_THRESHOLD:
		return "HIGH"
	if prob >= med:
		return "MEDIUM"
	return "LOW"


def prediction_confidence(history_len: int, min_steps: int = MIN_HISTORY_STEPS) -> str:
	"""HIGH / MEDIUM / LOW — насколько надёжен прогноз по длине истории."""
	if history_len >= min_steps:
		return "HIGH"
	if history_len >= max(min_steps // 2, 6):
		return "MEDIUM"
	return "LOW"


def incassation_recommendation(
	pred_balance_pct: float,
	current_balance_pct: float,
	cashout_prob: float,
	risk_label_value: str,
	hours_to_empty: Optional[float] = None,
) -> Dict[str, Any]:
	"""
	Рекомендация по инкассации (правило поверх ML, без отдельной модели).
	"""
	reasons = []
	is_urgent = False
	is_planned = False

	# 1. Сбор причин категории URGENT
	if pred_balance_pct < INCASSATION_URGENT_PCT * 100:
		reasons.append("прогноз < порога срочности")
		is_urgent = True
	if current_balance_pct < LOW_CASH_PCT * 100:
		reasons.append("текущий остаток критичный")
		is_urgent = True
	if risk_label_value == "HIGH" or cashout_prob >= HIGH_RISK_THRESHOLD:
		reasons.append("высокий ML-риск")
		is_urgent = True

	# 2. Сбор причин категории PLANNED (включая оценку времени до опустошения)
	if hours_to_empty is not None and hours_to_empty <= HORIZON_HOURS:
		reasons.append(f"до опустошения ~{hours_to_empty:.0f}ч")
		is_planned = True

	# Добавляем плановые причины, только если они имеют смысл (избегаем дублирования логики в тексте)
	if pred_balance_pct < INCASSATION_PLANNED_PCT * 100 and not is_urgent:
		reasons.append("прогноз ниже планового порога")
		is_planned = True
	if current_balance_pct < WARNING_CASH_PCT * 100 and not is_urgent:
		reasons.append("остаток в зоне предупреждения")
		is_planned = True
	if (risk_label_value == "MEDIUM" or cashout_prob >= CASHOUT_THRESHOLD) and not is_urgent:
		reasons.append("средний ML-риск")
		is_planned = True

	# 3. Принятие решения на основе наивысшего приоритета
	if is_urgent:
		return {
			"action": "URGENT",
			"priority": 1,
			"reason": "; ".join(reasons) or "критический уровень",
			"within_hours": 6,
		}

	if is_planned:
		return {
			"action": "PLANNED",
			"priority": 2,
			"reason": "; ".join(reasons) or "плановое пополнение",
			"within_hours": 24,
		}

	return {
		"action": "OK",
		"priority": 3,
		"reason": "пополнение не требуется в ближайшие 24ч",
		"within_hours": None,
	}


def regression_metrics(
	y_true,
	y_pred,
	capacity,
	low_pct_threshold: float = LOW_BALANCE_METRIC_PCT,
) -> Dict[str, float]:
	y_true = np.asarray(y_true, dtype=float)
	y_pred = np.asarray(y_pred, dtype=float)
	cap = np.asarray(capacity, dtype=float)

	n_samples = len(y_true)
    
	# Защита от пустых батчей, предотвращающая падения и NaN-предупреждения
	if n_samples == 0:
		return {k: float("nan") for k in (
			"mae", "rmse", "mape_capacity_pct", "mape_actual_pct",
			"within_10pct", "within_20pct", "within_30pct", "low_balance_mape_pct"
		)} | {"low_balance_n": 0, "n": 0}

	cap_safe = np.where(cap <= 0, 1.0, cap)
	pct_true = y_true / cap_safe

	# Оптимизация: вычисляем дельты один раз
	errors = y_true - y_pred
	abs_errors = np.abs(errors)
	pct_err = (abs_errors / cap_safe) * 100

	mae = float(np.mean(abs_errors))
	rmse = float(np.sqrt(np.mean(errors ** 2)))
    
	mape_cap = float(np.mean(pct_err))
	mape_actual = float(np.mean(abs_errors / np.maximum(y_true, 1.0)) * 100)

	within_10 = float(np.mean(pct_err <= 10) * 100)
	within_20 = float(np.mean(pct_err <= 20) * 100)
	within_30 = float(np.mean(pct_err <= 30) * 100)

	low_mask = pct_true < low_pct_threshold
	low_mape = (
		float(np.mean(pct_err[low_mask]))
		if low_mask.any()
		else float("nan")
	)

	return {
		"mae": mae,
		"rmse": rmse,
		"mape_capacity_pct": mape_cap,
		"mape_actual_pct": mape_actual,
		"within_10pct": within_10,
		"within_20pct": within_20,
		"within_30pct": within_30,
		"low_balance_mape_pct": low_mape,
		"low_balance_n": int(low_mask.sum()),
		"n": n_samples,
	}


def apply_calibrator(raw_prob: float, calibrator) -> float:
	# Ограничиваем вероятность диапазоном [0, 1] для защиты от выбросов калибратора
	if calibrator is None:
		return float(np.clip(raw_prob, 0.0, 1.0))
	try:
		calibrated_prob = float(calibrator.predict(np.asarray([raw_prob], dtype=float))[0])
		return float(np.clip(calibrated_prob, 0.0, 1.0))
	except Exception:
		return float(np.clip(raw_prob, 0.0, 1.0))
