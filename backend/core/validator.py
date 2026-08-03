"""
AST Safety Validator (`core/validator.py`)

Layered static analysis pipeline and sandboxed dry-run executor.
Ensures no malicious, infinite-looping, or invalid field-accessing code reaches the rules engine.
"""

import ast
import logging
from typing import Set, Dict, Any, List, Optional
from backend.core.schemas import Transaction, ValidationResult

logger = logging.getLogger(__name__)

# Valid fields allowed on a Transaction object
ALLOWED_TRANSACTION_FIELDS: Set[str] = set(Transaction.model_fields.keys())

# Safe builtins allowed during sandboxed dry-run execution
SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "len": len,
    "True": True,
    "False": False,
    "None": None,
}

# Names explicitly forbidden in function calls
DISALLOWED_CALL_NAMES: Set[str] = {
    "eval", "exec", "open", "compile", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "input", "breakpoint", "memoryview",
    "super", "type", "isinstance", "issubclass", "hasattr", "slice"
}

# Module names explicitly forbidden in attributes
DISALLOWED_MODULE_PREFIXES: Set[str] = {
    "os", "sys", "subprocess", "shutil", "importlib", "socket", "http",
    "requests", "urllib", "pathlib", "asyncio", "threading", "multiprocessing",
    "ctypes", "builtins", "__builtins__"
}


class ASTSafetyValidator:
    """
    Layered validator for proposed fraud rule Python source code.
    """

    def validate(self, code_str: str) -> ValidationResult:
        """
        Main validation entry point:
        1. Syntax check (ast.parse)
        2. AST walk for disallowed nodes (Import, loops, try/except, dangerous calls)
        3. Schema field validation (tx.<field>)
        4. Size & AST node complexity cap
        5. Restricted namespace sandboxed dry-run
        """
        if not code_str or not code_str.strip():
            return ValidationResult(valid=False, error="Rule code cannot be empty")

        # 1. Parse AST
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                error=f"Syntax error on line {e.lineno}: {e.msg}",
                line_number=e.lineno
            )

        # 2. Walk AST for disallowed statements & expressions
        for node in ast.walk(tree):
            lineno = getattr(node, "lineno", None)

            # Disallow imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = getattr(node, "module", "") or ""
                if isinstance(node, ast.Import):
                    module_name = ", ".join(alias.name for alias in node.names)
                return ValidationResult(
                    valid=False,
                    error=f"Disallowed import statement '{module_name}' on line {lineno}",
                    line_number=lineno
                )

            # Disallow loops (no infinite loops or iteration permitted)
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                loop_type = node.__class__.__name__
                return ValidationResult(
                    valid=False,
                    error=f"Disallowed loop structure '{loop_type}' on line {lineno}",
                    line_number=lineno
                )

            # Disallow try/except blocks (rules must not hide errors)
            if isinstance(node, (ast.Try, ast.ExceptHandler)):
                return ValidationResult(
                    valid=False,
                    error=f"Disallowed try/except block on line {lineno}",
                    line_number=lineno
                )

            # Disallow class definitions
            if isinstance(node, ast.ClassDef):
                return ValidationResult(
                    valid=False,
                    error=f"Disallowed class definition '{node.name}' on line {lineno}",
                    line_number=lineno
                )

            # Check function calls
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if isinstance(node.func.value, ast.Name):
                        mod_val = node.func.value.id
                        if mod_val in DISALLOWED_MODULE_PREFIXES:
                            return ValidationResult(
                                valid=False,
                                error=f"Disallowed module call '{mod_val}.{func_name}' on line {lineno}",
                                line_number=lineno
                            )

                if func_name in DISALLOWED_CALL_NAMES:
                    return ValidationResult(
                        valid=False,
                        error=f"Disallowed function call '{func_name}' on line {lineno}",
                        line_number=lineno
                    )

            # 3. Validate transaction field access (tx.<attr> or transaction.<attr>)
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id in ["tx", "transaction"]:
                    field_name = node.attr
                    if field_name != "get" and field_name not in ALLOWED_TRANSACTION_FIELDS:
                        return ValidationResult(
                            valid=False,
                            error=f"Unknown field '{field_name}' accessed on Transaction schema on line {lineno}",
                            line_number=lineno
                        )


        # 4. Check AST complexity cap
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > 150:
            return ValidationResult(
                valid=False,
                error=f"Rule complexity cap exceeded ({node_count} AST nodes > 150 limit)"
            )

        # 5. Sandboxed Dry-Run Execution
        dry_run_res = self._perform_dry_run(code_str)
        if not dry_run_res.valid:
            return dry_run_res

        return ValidationResult(valid=True)

    def _perform_dry_run(self, code_str: str) -> ValidationResult:
        """
        Executes code in restricted namespace against synthetic sample transactions
        to catch logic runtime exceptions (e.g. comparing str to int).
        """
        # Restricted global namespace
        restricted_globals = {"__builtins__": SAFE_BUILTINS}
        local_scope: Dict[str, Any] = {}

        try:
            compiled_code = compile(code_str, filename="<rule>", mode="exec")
            exec(compiled_code, restricted_globals, local_scope)
        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Compilation error during dry-run: {type(e).__name__}: {str(e)}"
            )

        # Find evaluate or detect function
        eval_func = local_scope.get("evaluate") or local_scope.get("detect")
        if not eval_func or not callable(eval_func):
            return ValidationResult(
                valid=False,
                error="Rule code must define an entry function named 'evaluate(tx)' or 'detect(transaction: dict)'"
            )



        # Create test sample transactions
        samples: List[Transaction] = [
            Transaction(
                id="tx_dry_1", account_id="acc_1", amount=100.0, location="US-NY",
                timestamp="2026-07-27T12:00:00Z", account_age_days=30,
                merchant_category="groceries", device_id="dev_1", is_international=False
            ),
            Transaction(
                id="tx_dry_2", account_id="acc_2", amount=5000.0, location="RU-MOS",
                timestamp="2026-07-27T12:00:00Z", account_age_days=2,
                merchant_category="crypto", device_id="dev_2", is_international=True
            ),
            Transaction(
                id="tx_dry_3", account_id="acc_3", amount=0.0, location="JP-TYO",
                timestamp="2026-07-27T12:00:00Z", account_age_days=500,
                merchant_category="electronics", device_id="dev_3", is_international=True
            ),
        ]

        # Execute against dry-run samples
        for i, sample in enumerate(samples, 1):
            try:
                try:
                    res = eval_func(sample)
                except AttributeError:
                    res = eval_func(sample.model_dump())

                if not isinstance(res, (bool, int)):
                    return ValidationResult(
                        valid=False,
                        error=f"Dry-run evaluation returned non-boolean result type '{type(res).__name__}'"
                    )
            except Exception as e:
                return ValidationResult(
                    valid=False,
                    error=f"Dry-run runtime error on sample {i}: {type(e).__name__}: {str(e)}"
                )


        return ValidationResult(valid=True)
