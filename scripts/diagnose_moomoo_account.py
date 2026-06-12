from __future__ import annotations

import moomoo as ft


def main() -> None:
    firms = [
        "FUTUINC",
        "FUTUSG",
        "FUTUSECURITIES",
        "FUTUMY",
        "FUTUJP",
        "FUTUAU",
        "FUTUCA",
    ]
    for name in firms:
        ctx = None
        print(f"--- {name} ---")
        try:
            ctx = ft.OpenSecTradeContext(
                filter_trdmarket=ft.TrdMarket.US,
                host="127.0.0.1",
                port=11111,
                security_firm=getattr(ft.SecurityFirm, name),
            )
            try:
                print("login_user_id", ctx.get_login_user_id())
            except Exception as exc:
                print("login_user_id error", repr(exc))
            ret, data = ctx.get_acc_list()
            print("get_acc_list ret", ret)
            print(data)
        except Exception as exc:
            print("context/query error", repr(exc))
        finally:
            if ctx is not None:
                ctx.close()


if __name__ == "__main__":
    main()
