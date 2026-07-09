
from __future__ import annotations
from datetime import datetime
from typing import List,Optional
from pydantic import BaseModel, Field

class ATMMeta(BaseModel):
    atm_id:str
    name:str
    bank:str
    address:str
    profile:str
    lat:float
    lon:float
    capacity:int

class ATMState(BaseModel):
    atm_id:str
    name:str
    bank:str
    lat:float
    lon:float
    capacity:int
    balance:int
    balance_pct:float=Field(description="Остаток в % от ёмкости")
    is_incassation:bool
    last_incassation:Optional[datetime]=None
    timestamp:datetime


class MLPrediction(BaseModel):
    atm_id:str
    pred_balance_24h:float
    pred_balance_pct:float
    cashout_prob:float=Field(description="Вероятность cash-out в следующие 24ч [0..1]")
    cashout_risk:bool
    risk_label:str=Field(description="LOW | MEDIUM | HIGH")

class ATMFull(BaseModel):
    state:ATMState
    predictions:Optional[MLPrediction]=None

class RouteStop(BaseModel):
    order:int
    atm_id:str
    name:str
    bank:str
    lat:float
    lon:float
    balance:int
    balance_pct:float
    status:str
    cashout_prob:Optional[float]=None
    dist_from_prev_km:float=0.0

class CashRouter(BaseModel):
    car_id: int
    label:str
    color:str
    stops:List[RouteStop]
    total_dist_km:float
    est_time_min:int

class RouteResponse(BaseModel):
    cars:List[CashRouter]
    total_stops:int
    total_dist_km:float
    est_time_min:int
    depot:dict[str, float] # masalan {lat : 45.3434 , lon:34.1343}

class SimStatus(BaseModel):
    current_timestamp:str
    step_index:int
    total_steps:int
    speed_x:float    #real vaqtda qanchalik tez

class AlertItem(BaseModel):
    atm_id:str
    name:str
    balance_pct:float
    cashout_prob:float
    risk_label:str
    hours_to_empty:Optional[float]=None







