import json
import math
import re
import statistics
from pathlib import Path
from tools._base import tool

_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool,
    "dict": dict, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset,
    "int": int, "isinstance": isinstance, "len": len,
    "list": list, "map": map, "max": max, "min": min,
    "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip,
    "True": True, "False": False, "None": None,
}

_SAFE_MODULES = {
    "math": math,
    "statistics": statistics,
    "json": json,
    "re": re,
}

CALC_TIMEOUT_SECONDS = 30


@tool(
    name="run_local_calculation",
    description="Exécute du code Python dans un bac à sable sécurisé pour faire des calculs. Modules disponibles : math, statistics, json, csv, re. PAS d'accès fichiers, réseau ou système. Le résultat est la dernière valeur imprimée via print().",
    category="compute",
    parameters={
        "type": "object",
        "properties": {
            "python_code": {
                "type": "string",
                "description": "Le code Python à exécuter. Utilise print() pour renvoyer le résultat.",
            },
        },
        "required": ["python_code"],
    },
)
def run_local_calculation(args: dict, project_id: str, project_dir: Path) -> str:
    code = args.get("python_code", "").strip()
    if not code:
        return "Erreur : Aucun code Python fourni."

    if len(code) > 10_000:
        return "Erreur : Le code est trop long (max 10 000 caractères)."

    try:
        from RestrictedPython import compile_restricted, safe_globals, PrintCollector
        from RestrictedPython.Eval import default_guarded_getiter
        from RestrictedPython.Guards import (
            guarded_unpack_sequence,
            safer_getattr,
        )

        compiled = compile_restricted(code, "<sandbox>", "exec")
        if compiled is None:
            return "Erreur : Le code contient des instructions non autorisées."

        restricted_globals = safe_globals.copy()
        restricted_globals["__builtins__"] = _SAFE_BUILTINS.copy()
        restricted_globals["_print_"] = PrintCollector
        restricted_globals["_getiter_"] = default_guarded_getiter
        restricted_globals["_getattr_"] = safer_getattr
        restricted_globals["_unpack_sequence_"] = guarded_unpack_sequence
        restricted_globals["_iter_unpack_sequence_"] = guarded_unpack_sequence
        restricted_globals["_write_"] = lambda obj: obj
        restricted_globals["_inplacevar_"] = lambda op, x, y: op(x, y)

        for mod_name, mod in _SAFE_MODULES.items():
            restricted_globals[mod_name] = mod

        restricted_locals: dict = {}

        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Le calcul a dépassé le timeout de 30 secondes.")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(CALC_TIMEOUT_SECONDS)

        try:
            exec(compiled, restricted_globals, restricted_locals)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        printed = restricted_locals.get("_print")
        result = printed() if printed else ""
        result = result.strip() if isinstance(result, str) else str(result).strip()
        if not result:
            return "Le code s'est exécuté sans erreur mais n'a rien affiché. Utilise print() pour renvoyer un résultat."
        return result

    except TimeoutError as e:
        return f"Erreur : {str(e)}"
    except SyntaxError as e:
        return f"Erreur de syntaxe dans le code : {str(e)}"
    except Exception as e:
        error_type = type(e).__name__
        return f"Erreur d'exécution ({error_type}) : {str(e)}"
