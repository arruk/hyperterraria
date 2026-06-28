#!/usr/bin/env python3
"""
Gera Assets/hyper_items_ptBR.json a partir de arquivos JSON em inglês.

O script não chama APIs e não traduz textos. Ele:
1. lê somente o objeto ItemName na primeira camada dos arquivos de entrada;
2. preserva hypertraduções existentes no arquivo de saída;
3. protege referências e placeholders usados pelo sistema de localização;
4. usa o nome inglês somente para chaves ainda não traduzidas.

Formato de entrada:

    {"ItemName": {"CopperShortsword": "Copper Shortsword"}}
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path
from typing import Any


ITEM_PREFIX = "ItemName."
PROTECTED_TOKEN_PATTERN = re.compile(
    r"""
    \{\$[^{}]+\}       # referência para outra chave: {$Category.Key}
    |
    \{\^[^{}]+\}       # expressão de pluralização: {^0:item;items}
    |
    \{\d+[^{}]*\}      # placeholder/formatador: {0}, {1:N0}, ...
    """,
    re.VERBOSE,
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "Assets"
    / "hyper_items_ptBR.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Cria ou atualiza o cache de nomes de itens usando arquivos JSON "
            "de localização inglesa."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Um ou mais arquivos JSON contendo as localizações inglesas.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Arquivo de saída (padrão: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help=(
            "Substitui traduções existentes pelos textos ingleses. "
            "Sem esta opção, traduções existentes são preservadas."
        ),
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError as exception:
        raise ValueError(f"arquivo não encontrado: {path}") from exception
    except json.JSONDecodeError as exception:
        raise ValueError(
            f"JSON inválido em {path}, linha {exception.lineno}, "
            f"coluna {exception.colno}: {exception.msg}"
        ) from exception
    except OSError as exception:
        raise ValueError(f"não foi possível ler {path}: {exception}") from exception


def load_english_item_names(paths: list[Path]) -> dict[str, str]:
    items: dict[str, str] = {}

    for path in paths:
        document = load_json(path)
        if not isinstance(document, dict):
            raise ValueError(f"a raiz do JSON precisa ser um objeto: {path}")

        item_section = document.get("ItemName")
        if not isinstance(item_section, dict):
            raise ValueError(
                f"o arquivo não contém um objeto ItemName na primeira camada: {path}"
            )

        found_in_file = 0
        for internal_name, value in item_section.items():
            if (
                not isinstance(internal_name, str)
                or "." in internal_name
                or not isinstance(value, str)
                or not value.strip()
            ):
                continue

            items[f"{ITEM_PREFIX}{internal_name}"] = value
            found_in_file += 1

        print(f"{path}: {found_in_file} chave(s) ItemName.* encontrada(s)")

    return items


def load_existing_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    document = load_json(path)
    if not isinstance(document, dict):
        raise ValueError(f"o cache existente precisa ser um objeto JSON: {path}")

    return {
        key: value
        for key, value in document.items()
        if isinstance(key, str)
        and key.startswith(ITEM_PREFIX)
        and isinstance(value, str)
        and value.strip()
    }


def protected_tokens(value: str) -> Counter[str]:
    """Retorna os tokens que uma tradução não pode remover nem modificar."""
    return Counter(PROTECTED_TOKEN_PATTERN.findall(value))


def is_reference_only(value: str) -> bool:
    """Indica que todo o valor é uma referência, sem texto traduzível."""
    stripped = value.strip()
    match = PROTECTED_TOKEN_PATTERN.fullmatch(stripped)
    return match is not None and stripped.startswith("{$")


def select_value(
    key: str,
    english_value: str,
    existing_value: str | None,
    overwrite_existing: bool,
) -> tuple[str, str | None]:
    """
    Escolhe o valor final e informa um eventual motivo para rejeitar o existente.

    Referências puras nunca devem ser traduzidas. Textos mistos podem ser
    traduzidos, desde que preservem exatamente todos os tokens do original.
    """
    if is_reference_only(english_value):
        return english_value, None

    if overwrite_existing or existing_value is None:
        return english_value, None

    expected_tokens = protected_tokens(english_value)
    actual_tokens = protected_tokens(existing_value)
    if actual_tokens != expected_tokens:
        return (
            english_value,
            f"{key}: tradução existente ignorada porque alterou tokens protegidos "
            f"(esperado={list(expected_tokens.elements())}, "
            f"encontrado={list(actual_tokens.elements())})",
        )

    return existing_value, None


def write_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(
            dict(sorted(cache.items())),
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def main() -> int:
    arguments = parse_arguments()

    try:
        english_items = load_english_item_names(arguments.inputs)
        if not english_items:
            raise ValueError(
                "nenhuma chave ItemName.* foi encontrada nos arquivos informados"
            )

        existing = load_existing_cache(arguments.output)
        result: dict[str, str] = {}
        warnings: list[str] = []
        preserved = 0
        protected_references = 0

        for key, english_value in english_items.items():
            selected, warning = select_value(
                key,
                english_value,
                existing.get(key),
                arguments.overwrite_existing,
            )
            result[key] = selected

            if is_reference_only(english_value):
                protected_references += 1
            elif (
                not arguments.overwrite_existing
                and key in existing
                and selected == existing[key]
            ):
                preserved += 1

            if warning is not None:
                warnings.append(warning)

        write_cache(arguments.output, result)

        untranslated = sum(
            value == english_items[key] for key, value in result.items()
        )
        print(f"Cache gravado em: {arguments.output}")
        print(f"Total de itens: {len(result)}")
        print(f"Valores existentes preservados: {preserved}")
        print(f"Referências puras protegidas: {protected_references}")
        print(f"Valores ainda iguais ao inglês: {untranslated}")
        for warning in warnings:
            print(f"Aviso: {warning}", file=sys.stderr)
        return 0
    except ValueError as exception:
        print(f"Erro: {exception}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
