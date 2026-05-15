from __future__ import annotations

import ast
import math

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, is_math_expression


_CONSTANTS = {"pi": math.pi, "e": math.e}


def _deg_sin(value: float) -> float:
    return math.sin(math.radians(value))


def _deg_cos(value: float) -> float:
    return math.cos(math.radians(value))


def _deg_tan(value: float) -> float:
    return math.tan(math.radians(value))


_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": _deg_sin,
    "cos": _deg_cos,
    "tan": _deg_tan,
}


def _evaluate_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError("unsupported binary operator")
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("unsupported unary operator")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        if len(node.args) != 1:
            raise ValueError("unsupported function arity")
        return float(_FUNCTIONS[node.func.id](_evaluate_node(node.args[0])))
    raise ValueError("unsupported expression")


def _evaluate(query: str) -> str:
    tree = ast.parse(query.replace("^", "**"), mode="eval")
    value = _evaluate_node(tree)
    if abs(value - round(value)) < 1e-10:
        return str(int(round(value)))
    return f"{value:.10g}"


def search(context: SearchContext, query: str) -> list[Result]:
    if not is_math_expression(query):
        return []

    try:
        result = _evaluate(query)
    except Exception:
        return []

    return [
        Result(
            id=f"calc:{query}",
            title=result,
            subtitle=f"Calculator | {query}",
            category="Calculator",
            score=CATEGORY_WEIGHTS["Calculator"],
            action={"type": "copy", "value": result},
            copy_value=result,
            terms=[query, result],
        )
    ]
