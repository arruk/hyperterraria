#!/usr/bin/env python3
"""
Hypertraduz nomes de itens vanilla usando Google Cloud Translation - Basic.

O script roda somente durante a preparação do cache. O mod não contém a chave,
não chama APIs e não traduz textos durante o jogo.
"""

from __future__ import annotations

import argparse
from collections import Counter
import html
import json
import os
from pathlib import Path
import random
import re
import sys
import time
from typing import Any, Callable
from urllib import error, parse, request


# Exatamente 50 idiomas intermediários suportados pelo Google Cloud
# Translation. Inglês (origem) e português brasileiro (destino final) ficam
# fora da lista para impedir repetição acidental.
LANGUAGE_POOL: tuple[str, ...] = (
    "af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs",
    "bg", "my", "ca", "zh-CN", "zh-TW", "hr", "cs", "da", "nl", "eo",
    "et", "fi", "fr", "gl", "ka", "de", "el", "gu", "ht", "he",
    "hi", "hu", "is", "id", "ga", "it", "ja", "kn", "kk", "km",
    "ko", "lo", "lv", "lt", "mk", "ms", "ml", "mt", "mi", "mr",
)

SOURCE_LANGUAGE = "en"
FINAL_LANGUAGE = "pt-BR"
NLLB_LANGUAGE_CODES: dict[str, str] = {
    "en": "eng_Latn",
    "pt-BR": "por_Latn",
    "af": "afr_Latn",
    "sq": "als_Latn",
    "am": "amh_Ethi",
    "ar": "arb_Arab",
    "hy": "hye_Armn",
    "az": "azj_Latn",
    "eu": "eus_Latn",
    "be": "bel_Cyrl",
    "bn": "ben_Beng",
    "bs": "bos_Latn",
    "bg": "bul_Cyrl",
    "my": "mya_Mymr",
    "ca": "cat_Latn",
    "zh-CN": "zho_Hans",
    "zh-TW": "zho_Hant",
    "hr": "hrv_Latn",
    "cs": "ces_Latn",
    "da": "dan_Latn",
    "nl": "nld_Latn",
    "eo": "epo_Latn",
    "et": "est_Latn",
    "fi": "fin_Latn",
    "fr": "fra_Latn",
    "gl": "glg_Latn",
    "ka": "kat_Geor",
    "de": "deu_Latn",
    "el": "ell_Grek",
    "gu": "guj_Gujr",
    "ht": "hat_Latn",
    "he": "heb_Hebr",
    "hi": "hin_Deva",
    "hu": "hun_Latn",
    "is": "isl_Latn",
    "id": "ind_Latn",
    "ga": "gle_Latn",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "kn": "kan_Knda",
    "kk": "kaz_Cyrl",
    "km": "khm_Khmr",
    "ko": "kor_Hang",
    "lo": "lao_Laoo",
    "lv": "lvs_Latn",
    "lt": "lit_Latn",
    "mk": "mkd_Cyrl",
    "ms": "zsm_Latn",
    "ml": "mal_Mlym",
    "mt": "mlt_Latn",
    "mi": "mri_Latn",
    "mr": "mar_Deva",
}
DEFAULT_NLLB_MODEL = "facebook/nllb-200-distilled-600M"
ITEM_PREFIX = "ItemName."
API_URL = "https://translation.googleapis.com/language/translate/v2"
DEFAULT_SOURCE = (
    Path(__file__).resolve().parent.parent
    / "Localization"
    / "Terraria.Localization.Content.en-US.Items.json"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "Assets"
    / "hyper_items_ptBR.json"
)
PROTECTED_TOKEN_PATTERN = re.compile(
    r"""
    \{\$[^{}]+\}       # referência: {$Category.Key}
    |
    \{\^[^{}]+\}       # pluralização: {^0:item;items}
    |
    \{\d+[^{}]*\}      # placeholder: {0}, {1:N0}, ...
    """,
    re.VERBOSE,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hypertraduz ItemName.* em múltiplos idiomas e termina em pt-BR."
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"JSON inglês original (padrão: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Cache final (padrão: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "-n",
        "--language-count",
        type=int,
        default=10,
        help=(
            "Quantidade total de idiomas na cadeia, incluindo pt-BR "
            "(padrão: 10; intervalo: 2 a 51)."
        ),
    )
    parser.add_argument(
        "--seed",
        default="HyperTerraria",
        help="Semente que determina a seleção e ordem dos idiomas.",
    )
    parser.add_argument(
        "--provider",
        choices=("nllb", "google"),
        default="nllb",
        help="Motor de tradução (padrão: nllb, local e sem API key).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_NLLB_MODEL,
        help=f"Modelo Hugging Face usado pelo NLLB (padrão: {DEFAULT_NLLB_MODEL}).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Quantidade de textos traduzidos por lote no NLLB (padrão: 32).",
    )
    parser.add_argument(
        "--api-key-env",
        default="GOOGLE_TRANSLATE_API_KEY",
        help="Variável com a chave, usada somente pelo provedor google.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Espera em segundos entre requisições (padrão: 0.1).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Número máximo de tentativas por requisição (padrão: 4).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Processa no máximo esta quantidade de itens; útil para testes.",
    )
    parser.add_argument(
        "--retranslate",
        action="store_true",
        help="Refaz também valores que já diferem do inglês.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cadeia e estimativa sem chamar a API ou alterar arquivos.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma chamadas potencialmente cobradas e alterações no cache.",
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


def load_source_items(path: Path) -> dict[str, str]:
    document = load_json(path)
    if not isinstance(document, dict) or not isinstance(document.get("ItemName"), dict):
        raise ValueError("o JSON de origem precisa conter ItemName na primeira camada")

    items: dict[str, str] = {}
    for internal_name, value in document["ItemName"].items():
        if (
            isinstance(internal_name, str)
            and "." not in internal_name
            and isinstance(value, str)
            and value.strip()
        ):
            items[f"{ITEM_PREFIX}{internal_name}"] = value

    if not items:
        raise ValueError("nenhum nome foi encontrado no objeto ItemName")
    return items


def load_output(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    document = load_json(path)
    if not isinstance(document, dict):
        raise ValueError("o cache de saída precisa ser um objeto JSON")
    return {
        key: value
        for key, value in document.items()
        if isinstance(key, str)
        and key.startswith(ITEM_PREFIX)
        and isinstance(value, str)
        and value.strip()
    }


def write_json_atomic(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(dict(sorted(values.items())), file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary.replace(path)


def protected_tokens(value: str) -> Counter[str]:
    return Counter(PROTECTED_TOKEN_PATTERN.findall(value))


def is_reference_only(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("{$") and PROTECTED_TOKEN_PATTERN.fullmatch(stripped) is not None


def select_language_chain(count: int, seed: str) -> list[str]:
    if count < 2 or count > len(LANGUAGE_POOL) + 1:
        raise ValueError(
            f"--language-count deve estar entre 2 e {len(LANGUAGE_POOL) + 1}"
        )
    generator = random.Random(seed)
    intermediates = generator.sample(LANGUAGE_POOL, count - 1)
    return [*intermediates, FINAL_LANGUAGE]


def translate_once(
    text: str,
    source_language: str,
    target_language: str,
    api_key: str,
    retries: int,
) -> str:
    body = json.dumps(
        {
            "q": text,
            "source": source_language,
            "target": target_language,
            "format": "text",
        }
    ).encode("utf-8")
    url = f"{API_URL}?{parse.urlencode({'key': api_key})}"

    for attempt in range(1, retries + 1):
        api_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=30) as response:
                payload = json.load(response)
            translated = payload["data"]["translations"][0]["translatedText"]
            if not isinstance(translated, str) or not translated:
                raise ValueError("a API retornou uma tradução vazia")
            return html.unescape(translated)
        except (error.HTTPError, error.URLError, TimeoutError, KeyError, ValueError) as exception:
            if attempt == retries:
                raise ValueError(
                    f"falha ao traduzir {source_language}->{target_language}: {exception}"
                ) from exception
            time.sleep(min(2 ** (attempt - 1), 8))

    raise AssertionError("fluxo de retries inválido")


class NllbTranslator:
    """Carrega uma vez o modelo NLLB e traduz localmente entre os 50 idiomas."""

    def __init__(self, model_name: str) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exception:
            raise ValueError(
                "dependências do NLLB ausentes; execute: "
                "python -m pip install torch transformers sentencepiece"
            ) from exception

        self._torch = torch
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Carregando {model_name} em {self._device}...")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            model_options: dict[str, Any] = {}
            if self._device.type == "cuda":
                model_options["torch_dtype"] = torch.float16
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                **model_options,
            )
        except Exception as exception:
            raise ValueError(
                f"não foi possível carregar o modelo NLLB '{model_name}': {exception}"
            ) from exception
        self._model.to(self._device)
        self._model.eval()

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        return self.translate_many([text], source_language, target_language)[0]

    def translate_many(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        if not texts:
            return []

        source_code = NLLB_LANGUAGE_CODES[source_language]
        target_code = NLLB_LANGUAGE_CODES[target_language]
        self._tokenizer.src_lang = source_code

        try:
            inputs = self._tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256,
            ).to(self._device)
            target_token_id = self._tokenizer.convert_tokens_to_ids(target_code)
            with self._torch.inference_mode():
                generated = self._model.generate(
                    **inputs,
                    forced_bos_token_id=target_token_id,
                    max_new_tokens=128,
                )
            translated = [
                value.strip()
                for value in self._tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                )
            ]
        except Exception as exception:
            raise ValueError(
                f"NLLB falhou em {source_language}->{target_language}: {exception}"
            ) from exception

        if len(translated) != len(texts):
            raise ValueError(
                f"NLLB retornou {len(translated)} texto(s) para {len(texts)} entrada(s)"
            )
        if any(not value for value in translated):
            raise ValueError(
                f"NLLB retornou texto vazio em {source_language}->{target_language}"
            )
        return translated


def translate_text_segments(
    text: str,
    source_language: str,
    target_language: str,
    translate_function: Callable[[str, str, str], str],
) -> str:
    """
    Traduz somente trechos fora dos tokens.

    Os tokens nunca são enviados ao tradutor, portanto não dependemos de o
    modelo respeitar marcadores artificiais.
    """
    parts: list[str] = []
    position = 0
    for match in PROTECTED_TOKEN_PATTERN.finditer(text):
        segment = text[position : match.start()]
        parts.append(
            translate_function(segment, source_language, target_language)
            if segment.strip()
            else segment
        )
        parts.append(match.group(0))
        position = match.end()

    tail = text[position:]
    parts.append(
        translate_function(tail, source_language, target_language)
        if tail.strip()
        else tail
    )
    return "".join(parts)


def split_translatable_segments(text: str) -> tuple[list[str | None], list[str]]:
    parts: list[str | None] = []
    segments: list[str] = []
    position = 0

    for match in PROTECTED_TOKEN_PATTERN.finditer(text):
        segment = text[position : match.start()]
        if segment.strip():
            parts.append(None)
            segments.append(segment)
        else:
            parts.append(segment)
        parts.append(match.group(0))
        position = match.end()

    tail = text[position:]
    if tail.strip():
        parts.append(None)
        segments.append(tail)
    else:
        parts.append(tail)

    return parts, segments


def translate_text_segments_many(
    texts: list[str],
    source_language: str,
    target_language: str,
    translate_function: Callable[[list[str], str, str], list[str]],
) -> list[str]:
    templates: list[list[str | None]] = []
    all_segments: list[str] = []

    for text in texts:
        parts, segments = split_translatable_segments(text)
        templates.append(parts)
        all_segments.extend(segments)

    translated_segments = translate_function(
        all_segments,
        source_language,
        target_language,
    )
    translated_iter = iter(translated_segments)
    results: list[str] = []

    for parts in templates:
        rebuilt: list[str] = []
        for part in parts:
            rebuilt.append(next(translated_iter) if part is None else part)
        results.append("".join(rebuilt))

    return results


def hypertranslate(
    english_value: str,
    chain: list[str],
    translate_function: Callable[[str, str, str], str],
    delay: float,
) -> str:
    expected_tokens = protected_tokens(english_value)
    current_text = english_value
    current_language = SOURCE_LANGUAGE

    for target_language in chain:
        current_text = translate_text_segments(
            current_text,
            current_language,
            target_language,
            translate_function,
        )
        if protected_tokens(current_text) != expected_tokens:
            raise ValueError(
                f"tokens protegidos divergiram em "
                f"{current_language}->{target_language}"
            )
        current_language = target_language
        if delay > 0:
            time.sleep(delay)

    return current_text


def hypertranslate_many(
    english_values: list[str],
    chain: list[str],
    translate_function: Callable[[list[str], str, str], list[str]],
    delay: float,
) -> list[str]:
    expected_tokens = [protected_tokens(value) for value in english_values]
    current_texts = english_values
    current_language = SOURCE_LANGUAGE

    for target_language in chain:
        current_texts = translate_text_segments_many(
            current_texts,
            current_language,
            target_language,
            translate_function,
        )
        for current_text, expected in zip(current_texts, expected_tokens):
            if protected_tokens(current_text) != expected:
                raise ValueError(
                    f"tokens protegidos divergiram em "
                    f"{current_language}->{target_language}"
                )
        current_language = target_language
        if delay > 0:
            time.sleep(delay)

    return current_texts


def batched(values: list[tuple[str, str]], batch_size: int) -> list[list[tuple[str, str]]]:
    return [
        values[index : index + batch_size]
        for index in range(0, len(values), batch_size)
    ]


def main() -> int:
    arguments = parse_arguments()
    try:
        if arguments.delay < 0:
            raise ValueError("--delay não pode ser negativo")
        if arguments.retries < 1:
            raise ValueError("--retries deve ser pelo menos 1")
        if arguments.limit is not None and arguments.limit < 1:
            raise ValueError("--limit deve ser pelo menos 1")
        if arguments.batch_size < 1:
            raise ValueError("--batch-size deve ser pelo menos 1")

        chain = select_language_chain(arguments.language_count, arguments.seed)
        source_items = load_source_items(arguments.source)
        output = load_output(arguments.output)

        candidates = [
            (key, english_value)
            for key, english_value in sorted(source_items.items())
            if not is_reference_only(english_value)
            and (
                arguments.retranslate
                or key not in output
                or output[key] == english_value
            )
        ]
        if arguments.limit is not None:
            candidates = candidates[: arguments.limit]

        estimated_requests = (
            len(candidates) * len(chain) if arguments.provider == "google" else 0
        )
        estimated_characters = (
            sum(len(value) for _, value in candidates) * len(chain)
        )
        print(f"Cadeia: {SOURCE_LANGUAGE} -> {' -> '.join(chain)}")
        print(f"Itens candidatos: {len(candidates)}")
        print(f"Provedor: {arguments.provider}")
        if arguments.provider == "google":
            print(f"Requisições estimadas: {estimated_requests}")
        print(f"Caracteres estimados (aproximação): {estimated_characters}")

        if arguments.dry_run:
            return 0
        if arguments.provider == "google" and not arguments.yes:
            raise ValueError(
                "use --dry-run para inspecionar ou --yes para confirmar chamadas cobradas"
            )

        if arguments.provider == "nllb":
            nllb = NllbTranslator(arguments.model)
            translate_function = nllb.translate
        else:
            api_key = os.environ.get(arguments.api_key_env, "").strip()
            if not api_key:
                raise ValueError(
                    f"defina a variável de ambiente {arguments.api_key_env} "
                    "com a chave da API"
                )

            def translate_function(
                text: str,
                source_language: str,
                target_language: str,
            ) -> str:
                return translate_once(
                    text,
                    source_language,
                    target_language,
                    api_key,
                    arguments.retries,
                )

        # Garante que referências e itens ainda ausentes também façam parte do cache.
        for key, english_value in source_items.items():
            output.setdefault(key, english_value)
            if is_reference_only(english_value):
                output[key] = english_value

        failures = 0
        if arguments.provider == "nllb" and arguments.batch_size > 1:
            for batch_index, batch in enumerate(
                batched(candidates, arguments.batch_size),
                start=1,
            ):
                first_index = (batch_index - 1) * arguments.batch_size + 1
                keys = [key for key, _ in batch]
                english_values = [english_value for _, english_value in batch]
                try:
                    translated_values = hypertranslate_many(
                        english_values,
                        chain,
                        nllb.translate_many,
                        arguments.delay,
                    )
                    for offset, (key, translated) in enumerate(
                        zip(keys, translated_values),
                        start=0,
                    ):
                        index = first_index + offset
                        output[key] = translated
                        print(f"[{index}/{len(candidates)}] {key}: {translated}")
                    write_json_atomic(arguments.output, output)
                except ValueError as batch_exception:
                    print(
                        f"Lote {batch_index} falhou; tentando item por item: "
                        f"{batch_exception}",
                        file=sys.stderr,
                    )
                    for offset, (key, english_value) in enumerate(batch, start=0):
                        index = first_index + offset
                        try:
                            translated = hypertranslate(
                                english_value,
                                chain,
                                nllb.translate,
                                arguments.delay,
                            )
                            output[key] = translated
                            write_json_atomic(arguments.output, output)
                            print(f"[{index}/{len(candidates)}] {key}: {translated}")
                        except ValueError as exception:
                            failures += 1
                            print(
                                f"[{index}/{len(candidates)}] ERRO {key}: {exception}",
                                file=sys.stderr,
                            )
        else:
            for index, (key, english_value) in enumerate(candidates, start=1):
                try:
                    translated = hypertranslate(
                        english_value,
                        chain,
                        translate_function,
                        arguments.delay,
                    )
                    output[key] = translated
                    write_json_atomic(arguments.output, output)
                    print(f"[{index}/{len(candidates)}] {key}: {translated}")
                except ValueError as exception:
                    failures += 1
                    print(f"[{index}/{len(candidates)}] ERRO {key}: {exception}", file=sys.stderr)

        print(f"Cache gravado em: {arguments.output}")
        print(f"Falhas: {failures}")
        return 2 if failures else 0
    except ValueError as exception:
        print(f"Erro: {exception}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido; traduções concluídas já foram salvas.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
