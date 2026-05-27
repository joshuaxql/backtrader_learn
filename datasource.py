import os
from datetime import datetime

import pandas as pd
import tushare as ts


VALID_ADJUSTMENTS = {"none", "qfq", "hfq"}


def get_tushare_client(token: str | None = None) -> ts.pro.client.DataApi:
    if token:
        return ts.pro_api(token)

    env_token = os.getenv("TUSHARE_TOKEN")
    if not env_token:
        raise RuntimeError(
            "Missing TUSHARE_TOKEN environment variable. "
            "Set it before requesting market data from Tushare."
        )
    return ts.pro_api(env_token)


def validate_request(ts_code: str, start_date: str, end_date: str, adjust: str) -> None:
    if not ts_code:
        raise ValueError("ts_code must not be empty.")
    if adjust not in VALID_ADJUSTMENTS:
        raise ValueError("adjust must be one of: none, qfq, hfq")

    for value, label in ((start_date, "start_date"), (end_date, "end_date")):
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError as exc:
            raise ValueError(f"{label} must follow YYYYMMDD, got {value!r}.") from exc

    if start_date > end_date:
        raise ValueError("start_date must be earlier than or equal to end_date.")


def apply_adjustment(data: pd.DataFrame, adjust: str) -> pd.DataFrame:
    if adjust == "none":
        return data

    price_cols = ["open", "high", "low", "close"]
    factor_col = data["adj_factor"]
    base_factor = factor_col.iloc[-1] if adjust == "qfq" else factor_col.iloc[0]
    ratio = factor_col / base_factor

    adjusted = data.copy()
    adjusted.loc[:, price_cols] = adjusted.loc[:, price_cols].mul(ratio, axis=0)
    return adjusted


def normalize_to_backtrader(data: pd.DataFrame) -> pd.DataFrame:
    bt_df = data.rename(columns={"vol": "volume"}).copy()
    bt_df["volume"] = bt_df["volume"] * 100
    bt_df["openinterest"] = 0
    bt_df = bt_df.set_index("trade_date")
    bt_df.index.name = "datetime"
    return bt_df[["open", "high", "low", "close", "volume", "openinterest"]]


def fetch_bt_dataframe(
    ts_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "hfq",
    token: str | None = None,
) -> pd.DataFrame:
    validate_request(ts_code, start_date, end_date, adjust)

    pro = get_tushare_client(token)
    daily = pro.daily(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        fields="ts_code,trade_date,open,high,low,close,vol",
    )

    if daily.empty:
        raise RuntimeError(
            f"No daily data returned for {ts_code} between {start_date} and {end_date}."
        )

    data = daily
    if adjust != "none":
        adj_factor = pro.adj_factor(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,adj_factor",
        )
        if adj_factor.empty:
            raise RuntimeError(
                "No adj_factor data returned for "
                f"{ts_code} between {start_date} and {end_date}."
            )
        data = daily.merge(adj_factor, on=["ts_code", "trade_date"], how="left")

    data["trade_date"] = pd.to_datetime(data["trade_date"], format="%Y%m%d")
    data = data.sort_values("trade_date").reset_index(drop=True)

    numeric_cols = ["open", "high", "low", "close", "vol"]
    if "adj_factor" in data.columns:
        numeric_cols.append("adj_factor")

    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    required_cols = ["open", "high", "low", "close", "vol"]
    if adjust != "none":
        required_cols.append("adj_factor")

    data = data.dropna(subset=required_cols)
    data = apply_adjustment(data, adjust)
    return normalize_to_backtrader(data)


if __name__ == "__main__":
    print(fetch_bt_dataframe("000001.SZ", "20200101", "20250101").tail())
