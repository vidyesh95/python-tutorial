# Numbers and Math
"""
Python has three built-in number types: int (unlimited size), float (64-bit decimal approximation)
and complex. Beyond the operators, the built-ins abs/round/pow/divmod/min/max/sum and the math,
decimal and fractions modules cover almost everything you need.
"""

import math
from decimal import Decimal
from fractions import Fraction

# Integers are unlimited
# Example
big = 2**100
print(big)
print(1_000_000 + 1)  # underscores make big literals readable

# Conversion between types
# Example
print(int("42") + 1, int(3.99), float("2.5"), int("ff", 16), int("1010", 2))
print(str(3.0), bool(0), bool(7), bool(""), bool("x"))

# Division flavours
# Example
print(7 / 2)  # 3.5   true division, always float
print(7 // 2)  # 3     floor division
print(-7 // 2)  # -4    floors towards negative infinity!
print(7 % 2, -7 % 3)  # 1 2   the sign of % follows the divisor
print(divmod(17, 5))  # (3, 2)

# Rounding
"""
round() uses "banker's rounding": halves go to the nearest EVEN number.
"""
# Example
print(round(3.14159, 2))  # 3.14
print(round(2.5), round(3.5))  # 2 4
print(math.floor(-2.5), math.ceil(-2.5), math.trunc(-2.5))  # -3 -2 -2

# Float precision
"""
Floats are binary approximations, so 0.1 + 0.2 is not exactly 0.3.
Compare floats with math.isclose(); use Decimal for money.
"""
# Example
print(0.1 + 0.2)  # 0.30000000000000004
print(0.1 + 0.2 == 0.3)  # False
print(math.isclose(0.1 + 0.2, 0.3))  # True
print(Decimal("0.1") + Decimal("0.2"))  # 0.3
print(Fraction(1, 3) + Fraction(1, 6))  # 1/2

# Useful built-ins
# Example
nums = [4, -2, 9, 0]
print(abs(-7.5), pow(2, 10), min(nums), max(nums), sum(nums))
print(sum(nums) / len(nums))  # average

# The math module
# Example
print(math.pi, math.e)
print(math.sqrt(16), math.isqrt(17))  # isqrt: integer square root
print(math.pow(2, 0.5), 2**0.5)
print(math.factorial(5), math.gcd(12, 18), math.lcm(4, 6))
print(math.log(math.e), math.log10(1000), math.log2(8))
print(math.sin(math.pi / 2), math.degrees(math.pi))
print(math.inf > 10**100, math.isnan(math.nan))
print(math.hypot(3, 4))  # 5.0

# Number formatting
# Example
print(f"{1234567.891:,.2f}")  # 1,234,567.89
print(f"{0.256:.1%}")  # 25.6%
print(f"{255:b} {255:x} {255:08b}")  # binary / hex / zero padded

# Common mistakes
"""
1. Using == to compare floats; use math.isclose().
2. Expecting round(2.5) to be 3 - Python rounds half to even (2).
3. Using floats for money; use Decimal("19.99") (always pass a string, Decimal(19.99) keeps the error).
4. Thinking // truncates: -7 // 2 is -4, not -3. Use math.trunc() or int() to truncate.
5. Forgetting that / always returns a float, even 4 / 2 == 2.0.
"""
