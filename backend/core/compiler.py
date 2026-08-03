"""
Rule Compiler (`core/compiler.py`)

Compiles validated Python rule source code into callable executable function objects
and registers/hot-reloads them directly into the live Rules Engine.
"""

import logging
from typing import Callable, Dict, Any, Tuple
from backend.core.schemas import Rule, Transaction
from backend.core.validator import SAFE_BUILTINS
from backend.core.rules_engine import RulesEngine

logger = logging.getLogger(__name__)


class RuleCompiler:
    """
    Compiles validated AST Python rule code into callable functions.
    """

    def compile_rule_code(self, code_str: str) -> Callable[[Transaction], bool]:
        """
        Compiles string containing 'def evaluate(tx): ...' into a callable function object.
        Executes inside a restricted global namespace.
        """
        restricted_globals = {"__builtins__": SAFE_BUILTINS}
        local_scope: Dict[str, Any] = {}

        try:
            code_obj = compile(code_str, filename="<rule_compiled>", mode="exec")
            exec(code_obj, restricted_globals, local_scope)
        except Exception as e:
            raise ValueError(f"Failed to compile rule code: {type(e).__name__}: {str(e)}")

        eval_func = local_scope.get("evaluate") or local_scope.get("detect")
        if not eval_func or not callable(eval_func):
            raise ValueError("Compiled code must contain a callable 'evaluate(tx)' function (or 'detect(transaction)')")


        def wrapped_eval(tx: Transaction) -> bool:
            try:
                return bool(eval_func(tx))
            except Exception:
                if hasattr(tx, "model_dump"):
                    return bool(eval_func(tx.model_dump()))
                elif isinstance(tx, dict):
                    return bool(eval_func(tx))
                return False

        return wrapped_eval


    def compile_and_register(self, rule: Rule, rules_engine: RulesEngine) -> Callable[[Transaction], bool]:
        """
        Compiles validated rule code and registers it immediately into active rules engine (hot-reload).
        """
        compiled_func = self.compile_rule_code(rule.code)
        rules_engine.register_rule(rule, compiled_func)
        logger.info(f"Successfully compiled and hot-reloaded rule '{rule.id}' into live rules engine.")
        return compiled_func
