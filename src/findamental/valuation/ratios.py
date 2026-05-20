def pe_ratio(price: float, eps: float) -> float:
    _require_nonzero(eps, "eps")
    return price / eps


def pb_ratio(price: float, book_value_per_share: float) -> float:
    _require_nonzero(book_value_per_share, "book_value_per_share")
    return price / book_value_per_share


def roe(net_income: float, total_equity: float) -> float:
    _require_nonzero(total_equity, "total_equity")
    return net_income / total_equity


def revenue_growth(current: float, prior: float) -> float:
    _require_nonzero(prior, "prior")
    return (current - prior) / abs(prior)


def _require_nonzero(value: float, name: str) -> None:
    if value == 0:
        raise ValueError(f"{name} must be non-zero")
