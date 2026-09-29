#!/usr/bin/env python3
"""报销单自动审批：按金额、发票附件、违规记录三项判一个去处。"""
import sys

PASS = "自动通过"
MANUAL = "转人工审批"
REJECT = "拒绝并记违规"


def decide(amount, has_invoice, has_violation):
    if amount <= 500:
        if not has_invoice:
            return MANUAL
        return MANUAL if has_violation else PASS
    if not has_invoice:
        return REJECT
    return REJECT if has_violation else MANUAL


def main(argv):
    if len(argv) != 4 or argv[2] not in ("y", "n") or argv[3] not in ("y", "n"):
        print("用法：approve.py <金额> <有发票附件 y/n> <有违规记录 y/n>", file=sys.stderr)
        return 2
    try:
        amount = float(argv[1])
    except ValueError:
        print("金额不合法：%s" % argv[1], file=sys.stderr)
        return 2
    print(decide(amount, argv[2] == "y", argv[3] == "y"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
