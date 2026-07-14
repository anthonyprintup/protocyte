from __future__ import annotations

import struct
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)

_DECIMAL_PRECISION = 160
_DECIMAL_EXPONENT_LIMIT = Decimal(10_000)
_NEGATIVE_DECIMAL_EXPONENT_LIMIT = Decimal(-10_000)
_DECIMAL_CONTEXT = Context(
    prec=_DECIMAL_PRECISION,
    rounding=ROUND_HALF_EVEN,
    Emin=-999_999,
    Emax=999_999,
    capitals=1,
    clamp=0,
    flags=[],
    traps=[InvalidOperation, DivisionByZero, Overflow],
)
_BINARY_FORMATS = {
    32: (24, -126, 127, 127, 8, 23),
    64: (53, -1022, 1023, 1023, 11, 52),
}


class DeterministicMathDomainError(ValueError):
    pass


class DeterministicMathNonFiniteError(OverflowError):
    pass


def _decimal_value(value: int | float) -> Decimal:
    return Decimal(value) if isinstance(value, int) else Decimal.from_float(value)


def _round_scaled_ratio(numerator: int, denominator: int, shift: int) -> int:
    if shift >= 0:
        numerator <<= shift
    else:
        denominator <<= -shift
    quotient, remainder = divmod(numerator, denominator)
    doubled_remainder = remainder << 1
    if doubled_remainder > denominator or (
        doubled_remainder == denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _decimal_to_binary_bits(value: Decimal, width: int) -> int:
    precision, min_exponent, max_exponent, bias, exponent_bits, fraction_bits = (
        _BINARY_FORMATS[width]
    )
    sign = int(value.is_signed())
    sign_bits = sign << (width - 1)
    if value.is_infinite():
        return sign_bits | (((1 << exponent_bits) - 1) << fraction_bits)
    if not value.is_finite():
        raise DeterministicMathDomainError

    numerator, denominator = value.copy_abs().as_integer_ratio()
    if numerator == 0:
        return sign_bits

    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < denominator << exponent:
            exponent -= 1
    elif numerator << -exponent < denominator:
        exponent -= 1

    if exponent < min_exponent:
        significand = _round_scaled_ratio(
            numerator,
            denominator,
            (precision - 1) - min_exponent,
        )
        if significand == 0:
            return sign_bits
        if significand < 1 << (precision - 1):
            exponent_field = 0
            fraction = significand
        else:
            exponent_field = 1
            fraction = 0
    else:
        significand = _round_scaled_ratio(
            numerator,
            denominator,
            (precision - 1) - exponent,
        )
        if significand == 1 << precision:
            significand >>= 1
            exponent += 1
        if exponent > max_exponent:
            return sign_bits | (((1 << exponent_bits) - 1) << fraction_bits)
        exponent_field = exponent + bias
        fraction = significand - (1 << (precision - 1))

    return sign_bits | (exponent_field << fraction_bits) | fraction


def _binary_float_from_bits(bits: int, width: int) -> float:
    if width == 32:
        return struct.unpack("<f", bits.to_bytes(4, "little"))[0]
    return struct.unpack("<d", bits.to_bytes(8, "little"))[0]


def _round_decimal(value: Decimal, width: int) -> float:
    bits = _decimal_to_binary_bits(value, width)
    _, _, _, _, exponent_bits, fraction_bits = _BINARY_FORMATS[width]
    exponent_mask = ((1 << exponent_bits) - 1) << fraction_bits
    if bits & exponent_mask == exponent_mask:
        raise DeterministicMathNonFiniteError
    return _binary_float_from_bits(bits, width)


def evaluate_unary(name: str, value: int | float, width: int) -> float:
    operand = _decimal_value(value)
    if name == "sqrt" and operand < 0:
        raise DeterministicMathDomainError
    if name in {"log", "log2", "log10"} and operand <= 0:
        raise DeterministicMathDomainError
    if name == "exp" and operand > _DECIMAL_EXPONENT_LIMIT:
        raise DeterministicMathNonFiniteError
    if name == "exp" and operand < _NEGATIVE_DECIMAL_EXPONENT_LIMIT:
        return 0.0

    try:
        with localcontext(_DECIMAL_CONTEXT):
            result = {
                "sqrt": lambda: operand.sqrt(),
                "exp": lambda: operand.exp(),
                "log": lambda: operand.ln(),
                "log2": lambda: operand.ln() / Decimal(2).ln(),
                "log10": lambda: operand.log10(),
            }[name]()
    except (DecimalException, OverflowError, ValueError) as exc:
        raise DeterministicMathNonFiniteError from exc
    return _round_decimal(result, width)


def evaluate_pow(base: float, exponent: float) -> float:
    decimal_base = Decimal.from_float(base)
    decimal_exponent = Decimal.from_float(exponent)
    if decimal_exponent.is_zero():
        return 1.0

    _, exponent_denominator = decimal_exponent.as_integer_ratio()
    exponent_is_integral = exponent_denominator == 1
    if decimal_base.is_zero():
        if decimal_exponent < 0:
            raise DeterministicMathDomainError
        negative_zero = (
            decimal_base.is_signed()
            and exponent_is_integral
            and int(decimal_exponent) & 1
        )
        return -0.0 if negative_zero else 0.0

    negative_result = False
    if decimal_base < 0:
        if not exponent_is_integral:
            raise DeterministicMathDomainError
        negative_result = bool(int(decimal_exponent) & 1)
        decimal_base = decimal_base.copy_abs()

    if decimal_base == 1:
        return -1.0 if negative_result else 1.0

    try:
        with localcontext(_DECIMAL_CONTEXT):
            transformed = decimal_exponent * decimal_base.ln()
            if transformed > _DECIMAL_EXPONENT_LIMIT:
                raise DeterministicMathNonFiniteError
            if transformed < _NEGATIVE_DECIMAL_EXPONENT_LIMIT:
                return -0.0 if negative_result else 0.0
            result = transformed.exp()
            if negative_result:
                result = -result
    except DeterministicMathNonFiniteError:
        raise
    except (DecimalException, OverflowError, ValueError) as exc:
        raise DeterministicMathNonFiniteError from exc
    return _round_decimal(result, 64)
