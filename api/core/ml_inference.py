from __future__ import annotations

from typing import Optional

import numpy as np

from .config import LOW_BALANCE_TRAIN_PCT


def predict_balance(
	row,
	reg_main,
	reg_low: Optional[object],
	capacity: float,
	current_balance_pct: float,
) -> float:
	"""Если остаток низкий — специализированная модель, иначе основная."""
    
	# 1. Безопасная обработка нулевой вместимости (capacity = 0 не должно превращаться в 1)
	cap = capacity if capacity is not None else 1.0
    
	# Опциональная защита: вместимость не может быть отрицательной
	cap = max(cap, 0.0)

	# 2. Выбор активной модели без дублирования вызова метода predict()
	use_low_model = (reg_low is not None) and (current_balance_pct < (LOW_BALANCE_TRAIN_PCT * 100))
	model = reg_low if use_low_model else reg_main

	# 3. Единый вызов предсказания
	pred = model.predict(row)[0]

	# 4. Ограничение результата в заданных рамках и приведение к float
	return float(np.clip(pred, 0.0, cap))
