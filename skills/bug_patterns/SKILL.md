---
name: bug_patterns
description: Offline catalog of common bug archetypes (coupons/pricing, boundary conditions, mutable defaults, ignored returns).
---

# Common Bug Patterns & Diagnostic Clues (Offline Knowledge)

*Note: Historical patterns are clues and hypotheses, never ground truth. Always verify against repository code.*

## Archetype 1: Ignored Return Value in Call Chain
- **Symptom**: Helper function calculates an adjustment or transformation, but caller does not assign or use the returned value.
- **Pattern**:
  ```python
  # Buggy:
  apply_discount(subtotal, coupon)
  return subtotal

  # Fix:
  discount = apply_discount(subtotal, coupon)
  return max(0.0, subtotal - discount)
  ```

## Archetype 2: Off-By-One / Boundary Slicing
- **Symptom**: Last element skipped on boundary pages or pagination dividing evenly.
- **Fix**: Check `start + page_size` vs `start + page_size - 1` in slice upper bounds.

## Archetype 3: Mutable Default Arguments
- **Symptom**: Shared state or item leaking between independent calls.
- **Fix**: Replace `def func(items=[])` with `def func(items=None): items = [] if items is None else list(items)`.

## Archetype 4: Missing None/Empty Check
- **Symptom**: `AttributeError` or `TypeError` on optional inputs.
- **Fix**: Guard with `if value is None:` or default fallback before accessing attributes.
