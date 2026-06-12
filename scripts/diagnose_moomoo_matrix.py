from __future__ import annotations

import pandas as pd
import moomoo as ft


def main() -> None:
    pd.set_option("display.max_columns", None)
    firms = ["FUTUINC", "FUTUSG", "FUTUSECURITIES", "FUTUMY", "FUTUJP", "FUTUAU", "FUTUCA"]
    markets = ["NONE", "US", "SG", "HK", "MY", "JP", "AU", "CA"]
    seen = set()
    for market_name in markets:
        for firm_name in firms:
            ctx = None
            label = f"{market_name}/{firm_name}"
            try:
                ctx = ft.OpenSecTradeContext(
                    filter_trdmarket=getattr(ft.TrdMarket, market_name),
                    host="127.0.0.1",
                    port=11111,
                    security_firm=getattr(ft.SecurityFirm, firm_name),
                )
                ret, data = ctx.get_acc_list()
                if ret != ft.RET_OK:
                    print(label, "ERROR", data)
                    continue
                key = data.to_csv(index=False)
                if key in seen:
                    continue
                seen.add(key)
                print(f"\n--- {label} ---")
                print(data.to_string(index=False))
            except Exception as exc:
                print(label, "EXCEPTION", repr(exc))
            finally:
                if ctx is not None:
                    ctx.close()


if __name__ == "__main__":
    main()
