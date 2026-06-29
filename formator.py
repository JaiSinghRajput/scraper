import json
import argparse
import re
from datetime import datetime
from rapidfuzz import fuzz

def is_invalid_faq_answer(answer):
    if not answer:
        return True

    answer = str(answer).strip().lower()

    invalid_patterns = [
        "no",
        "not available",
        "n/a",
        "na",
        "none",
    ]

    return any(
        answer.startswith(pattern)
        for pattern in invalid_patterns
    )
def is_invalid_value(value):
    if not value:
        return True

    value = str(value).strip()

    # remove trailing spaces
    value_lower = value.lower()

    # exact junk values
    if value_lower in {
        "n/a",
        "na",
        "not available",
        "none",
        "-",
        ".",
        "..",
        "...",
        "…",
        "--"
    }:
        return True

    # values like:
    # Awards Received : …
    # Products Used : ...
    # Services : .
    parts = value.split(":", 1)

    if len(parts) == 2:

        rhs = parts[1].strip(
            " .,…-"
        )

        if not rhs:
            return True

        if rhs.lower() in {
            "n/a",
            "na",
            "not available",
            "none",
        }:
            return True

    return False
def normalize_phone(phone):
    if not phone:
        return None

    phone = re.sub(
        r"\D",
        "",
        str(phone)
    )

    if not phone:
        return None

    # +910XXXXXXXXXX
    if phone.startswith("910"):
        phone = phone[3:]

    # 91XXXXXXXXXX
    elif (
        phone.startswith("91")
        and len(phone[2:]) == 10
    ):
        phone = phone[2:]

    # 0XXXXXXXXXX
    elif phone.startswith("0"):
        phone = phone[1:]

    return phone
def is_indian_mobile(phone):
    return (
        phone
        and len(phone) == 10
        and phone[0] in "6789"
    )
def is_duplicate_feature(
    feature_text,
    faq_answers,
    threshold=90
):
    feature_text = str(feature_text).lower()

    for answer in faq_answers:
        answer = str(answer).lower()

        if (
            feature_text in answer
            or answer in feature_text
        ):
            return True

        if (
            fuzz.token_set_ratio(
                feature_text,
                answer
            ) >= threshold
        ):
            return True

    return False
def normalize_display_value(text):
    return re.sub(
        r"\s+",
        " ",
        str(text).lower().strip()
    )
def normalize_faq(question, answer):
    if not question or not answer:
        return question, answer

    question = str(question).strip()
    answer = str(answer).strip()

    # ----------------------------------
    # Experience conversion
    # ----------------------------------
    year_match = re.search(
    r"\b\d{4}\b",
    answer
    )

    if (
        question
        and question.strip().lower() == "experience"
    ):

        if not year_match:
            return None, None

        year = int(
            year_match.group()
        )

        if not (1900 <= year <= 2026):
            return None, None

        exp = 2026 - year

        answer = f"{exp}+ years"

        return question, answer

    # ----------------------------------
    # Generic question removal
    # ----------------------------------

    q_norm = re.sub(
        r"[^a-z0-9]+",
        "",
        question.lower()
    )

    if ":" in answer:

        prefix, remainder = answer.split(
            ":",
            1
        )

        prefix_norm = re.sub(
            r"[^a-z0-9]+",
            "",
            prefix.lower()
        )

        if (
            prefix_norm == q_norm
            or q_norm in prefix_norm
            or prefix_norm in q_norm
        ):
            answer = remainder.strip()
            
    # ----------------------------------
    # Question == Answer
    # Convert to Yes
    # ----------------------------------

    a_norm = re.sub(
        r"[^a-z0-9]+",
        "",
        answer.lower()
    )

    if (
        q_norm == a_norm
        or fuzz.ratio(
            q_norm,
            a_norm
        ) >= 95
    ):
        answer = "Yes"
        
    # ----------------------------------
    # FAQ Price Cleanup
    # ----------------------------------

    if re.search(r"\d", answer):

        # 75, 000 -> 75,000
        answer = re.sub(
            r",\s+",
            ",",
            answer
        )

        # find Indian-style prices
        def fix_price(match):

            num = re.sub(
                r"\D",
                "",
                match.group(0)
            )

            if not num:
                return match.group(0)

            return format_indian_number(
                int(num)
            )

        answer = re.sub(
            r"\d[\d,\s]*",
            fix_price,
            answer
        )
        
        # add missing space between price and text
        answer = re.sub(
            r"(\d)([A-Za-z])",
            r"\1 \2",
            answer
        )

    # ----------------------------------
    # Generic cleanup
    # ----------------------------------

    answer = answer.replace(
        "\\n",
        ", "
    )

    answer = answer.replace(
        "\n",
        ", "
    )

    answer = re.sub(
        r"\s+",
        " ",
        answer
    )

    answer = re.sub(
        r"(,\s*){2,}",
        ", ",
        answer
    )

    answer = answer.strip(" ,")

    return question, answer
def clean_style_usp(answer):

    if not answer:
        return None

    answer = str(answer).strip()

    # remove phone numbers
    answer = re.sub(
        r"(?:\+?91[\s\-]?)?[6-9]\d{9}",
        "",
        answer
    )

    # remove urls
    if re.search(
        r"https?://|www\.",
        answer,
        re.I
    ):
        return None

    # remove emojis
    answer = re.sub(
        r"[\U00010000-\U0010ffff]",
        "",
        answer
    )

    answer = re.sub(
        r"\s+",
        " ",
        answer
    ).strip()

    junk = {
        "good",
        "nice",
        "best",
        "ok",
        "super",
        "all",
        "pk",
        "yes",
        "-",
        "."
    }

    if answer.lower() in junk:
        return None

    if len(answer) < 5:
        return None

    return answer
def clean_strings(obj):
    if isinstance(obj, dict):
        return {
            k: clean_strings(v)
            for k, v in obj.items()
            if v is not None
        }

    if isinstance(obj, list):
        return [
            clean_strings(v)
            for v in obj
        ]

    if isinstance(obj, str):

        # preserve Indian currency values
        if re.fullmatch(
            r"[\d,\s]+(?:\.\d+)?",
            obj.strip()
        ):
            return re.sub(
                r",\s+",
                ",",
                obj.strip()
            )

        # preserve Indian price ranges
        if re.fullmatch(
    r"[\d,\s]+(?:\.\d+)?-[\d,\s]+(?:\.\d+)?",
    obj.strip()
):
            return re.sub(r",\s+", ",", obj.strip())
        # preserve any string that contains a valid Indian formatted price
        if re.search(
            r"\d+\s*,\s*\d+",
            obj
        ):
            return re.sub(
                r",\s+",
                ",",
                obj.strip()
            )
        # normalize spaces
        obj = re.sub(
            r"\s+",
            " ",
            obj
        )

        # remove unicode ellipsis
        obj = obj.replace(
            "…",
            ""
        )

        # convert dot-separated junk into commas
        # Example:
        # MAC.. Lakme.. Revlon
        # -> MAC, Lakme, Revlon
        obj = re.sub(
            r"\s*\.\.+\s*",
            ", ",
            obj
        )

        # remove remaining repeated dots
        obj = re.sub(
            r"\.{2,}",
            ".",
            obj
        )

        # remove spaces before dots
        obj = re.sub(
            r"\s+\.",
            ".",
            obj
        )

        # remove trailing dots
        obj = re.sub(
            r"\.+$",
            "",
            obj
        )

        # remove trailing commas
        obj = re.sub(
            r",+$",
            "",
            obj
        )

        # split and clean comma separated values
        parts = []

        for part in obj.split(","):

            part = part.strip(
                " .,…"
            )

            if not part:
                continue

            if part in {
                ".",
                "..",
                "...",
                "…"
            }:
                continue

            parts.append(part)

        # dedupe values
        seen = set()
        cleaned_parts = []

        for part in parts:

            norm = (
                part.lower()
                .replace("’", "'")
                .strip()
            )

            if norm in seen:
                continue

            seen.add(norm)
            cleaned_parts.append(part)

        obj = ", ".join(
            cleaned_parts
        )

        return obj.strip(
            " .,…"
        )

    return obj
def format_indian_number(num):
    num = str(int(num))

    if len(num) <= 3:
        return num

    last3 = num[-3:]
    rest = num[:-3]

    parts = []

    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]

    if rest:
        parts.insert(0, rest)

    return ",".join(parts + [last3])
def remove_phone_numbers(obj):

    if isinstance(obj, dict):

        cleaned = {}

        for k, v in obj.items():

            if k == "phone":
                cleaned[k] = v
                continue

            cleaned[k] = remove_phone_numbers(v)

        return cleaned

    if isinstance(obj, list):
        return [
            remove_phone_numbers(v)
            for v in obj
        ]

    if isinstance(obj, str):

        obj = re.sub(
        r"(?:\+?91[\s\-]?)?[6-9]\d{9}",
        "",
        obj
    )

        obj = re.sub(
            r"(?:\+?91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}",
            "",
            obj
        )

        obj = re.sub(
            r"\s+",
            " ",
            obj
        )

        return obj.strip(
            " ,.-"
        )

    return obj
def normalize_price_range(question, price):
    if not question or not price:
        return price

    if question.strip().lower() != "starting price":
        return price

    price = str(price).strip()

    if price.lower() == "price on request":
        return price

    if price == "-1--1":
        return None

    parts = price.split("-")

    if len(parts) != 2:
        return price

    try:
        low = int(re.sub(r"\D", "", str(parts[0])) or "0")

        high = int(re.sub(r"\D", "", str(parts[1])) or "0")

        if low == 0:
            low = 10000

        if high == 0:
            high = 10000

        if low > high:
            low, high = high, low

        return (
    f"{format_indian_number(low)}-"
    f"{format_indian_number(high)}"
)

    except Exception:
        return price
def remove_emojis(obj):

    if isinstance(obj, dict):
        return {
            k: remove_emojis(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [
            remove_emojis(v)
            for v in obj
        ]

    if isinstance(obj, str):

        return re.sub(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F900-\U0001FAFF"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "]+",
            "",
            obj
        )

    return obj
def transform_vendor(raw_json):
    # Handle list input automatically
    if isinstance(raw_json, list):
        return [transform_vendor(item) for item in raw_json]

    vendor = raw_json.get("vendorProfile", {})
    profile = vendor.get("profile", {})

    # ----------------------------------
    # Pricing Dedup
    # ----------------------------------

    pricing_map = {}

    def add_price(question, price, unit=None):

        price = normalize_price_range(
            question,
            price
        )

        if not question or not price:
            return

        key = (
            f"{str(question).strip().lower()}|"
            f"{str(price).strip()}"
        )

        if key not in pricing_map:
            pricing_map[key] = {
                "question": question,
                "price": price,
                "unit": unit,
            }
        
    # pricing[]
    for item in vendor.get("pricing", []):
        add_price(
            item.get("question"),
            item.get("price"),
            item.get("unit"),
        )

    # new_pricing.price[]
    new_pricing = vendor.get("new_pricing", {})

    # vendor.price_faq
    for item in vendor.get("price_faq", []):
        add_price(
            item.get("question"),
            item.get("answer"),
            item.get("unit"),
        )

    # new_pricing.price_faq
    for item in vendor.get("price_faq", []):
        add_price(
            item.get("question"),
            item.get("answer"),
            item.get("unit"),
        )

    # FAQ pricing fallback
    for item in vendor.get("faq", []):
        question = item.get("question", "")
        answer = item.get("answer")

        if (
            answer
            and any(
                word in question.lower()
                for word in [
                    "price",
                    "pricing",
                    "package",
                    "cost",
                    "rate",
                    "charges",
                ]
            )
            and re.search(r"\d", str(answer))
        ):
            add_price(question, answer)
    # ----------------------------------
    # Documents / Brochure PDF
    # ----------------------------------

    documents = {}

    menu_brochure = vendor.get(
        "menu_brochure_pdf", {}
    )

    if menu_brochure.get("pdf_url"):
        documents["Brochure"] = (
            menu_brochure["pdf_url"]
        )

# ----------------------------------
# Videos
# ----------------------------------

    videos = []

    for video in (
        vendor.get("videos") or {}
    ).get("video_array", []):

        video_link = video.get("video_link")
        video_title = video.get(
            "video_title", ""
        )

        if not video_link:
            continue

        if "wedmegood" in video_title.lower():
            continue

        # Only keep YouTube videos
        if not any(
            domain in video_link.lower()
            for domain in [
                "youtube.com",
                "youtu.be",
            ]
        ):
            continue

        videos.append({
            "video_link": video_link,
            "video_title": video_title,
        })
    
    # ----------------------------------
    # FAQ Cleaning
    # ----------------------------------

    faq_items = []
    faq_seen = set()

    cancellation_self = []
    cancellation_user = []

    for item in vendor.get("faq", []):
        question = item.get("question")
        answer = item.get("answer")

        question, answer = normalize_faq(
            question,
            answer
        )
        if not question or not answer:
            continue
        q = re.sub(
    r"[^a-z0-9]",
    "",
    str(question).lower()
)

        if ("cancellation" in q and "policy" in q):

            answer = str(answer).strip()

            answer_lower = answer.lower()

            # ----------------------------------
            # Detect from answer first
            # ----------------------------------

            if answer_lower.startswith("for self"):

                answer = re.sub(
                    r"^for\s*self\s*[-:]\s*",
                    "",
                    answer,
                    flags=re.I
                )

                if answer not in cancellation_self:
                    cancellation_self.append(answer)

                continue

            if answer_lower.startswith("for user"):

                answer = re.sub(
                    r"^for\s*user\s*[-:]\s*",
                    "",
                    answer,
                    flags=re.I
                )

                if answer not in cancellation_user:
                    cancellation_user.append(answer)

                continue

            # ----------------------------------
            # Detect from question
            # ----------------------------------

            if "self" in q:

                if answer not in cancellation_self:
                    cancellation_self.append(answer)

                continue

            if (
                "user" in q
                or "term" in q
            ):

                if answer not in cancellation_user:
                    cancellation_user.append(answer)

                continue

            # Generic Cancellation Policy

            generic_answer = answer.strip()

            # If same answer already exists in self bucket, skip generic
            if generic_answer in cancellation_self:
                continue

            # If same answer already exists in user bucket, skip generic
            if generic_answer in cancellation_user:
                continue
                    
        if "styleusp" in q:
            answer = clean_style_usp(
                answer
            )

            if not answer:
                continue
        if (question and question.strip().lower() == "lead time"):
            continue
        
        if question.strip().lower() == "advance amount (%)":
            question = "Advance Amount"
            
        if question == "Advance Amount":

            percent_match = re.search(
                r"(\d+)\s*%",
                answer
            )

            if percent_match:

                percent = int(
                    percent_match.group(1)
                )

                percent = min(
                    percent,
                    100
                )

                answer = re.sub(
                    r"\d+\s*%",
                    f"{percent}%",
                    answer,
                    count=1
                )
                
        # ----------------------------------
        # Cancellation Policy
        # ----------------------------------

        if question.strip().lower() == "cancellation policy":

            percent_match = re.search(
                r"(\d+)\s*%",
                answer
            )

            if percent_match:

                percent = int(
                    percent_match.group(1)
                )

                percent = min(
                    percent,
                    100
                )

                answer = (
                    f"{percent}% of advance booking"
                )
        if not answer:
            continue

        if is_invalid_faq_answer(answer):
            continue

        if "wedmegood" in (
            f"{question or ''} {answer or ''}"
        ).lower():
            continue

        faq_key = (
            str(question).strip().lower(),
            str(answer).strip().lower()
        )

        if faq_key in faq_seen:
            continue

        faq_seen.add(faq_key)

        faq_items.append({
            "question": question,
            "answer": answer,
        })
    parts = []

    self_text = ", ".join(
        dict.fromkeys(cancellation_self)
    )

    user_text = ", ".join(
        dict.fromkeys(cancellation_user)
    )

    if self_text and self_text == user_text:

        parts.append(self_text)

    else:

        if self_text:
            parts.append(
                f"For Self - {self_text}"
            )

        if user_text:
            parts.append(
                f"For User - {user_text}"
            )

    merged_answer = ", ".join(parts)

    if merged_answer:

        existing_generic = False

        for faq in faq_items:

            if (
                str(faq.get("question", "")).strip().lower()
                == "cancellation policy"
            ):

                existing_answer = str(
                    faq.get("answer", "")
                ).strip().lower()

                normalized_existing = re.sub(
                    r"^for\s*(self|user)\s*[-:]\s*",
                    "",
                    existing_answer,
                    flags=re.I
                )

                normalized_new = re.sub(
                    r"^for\s*(self|user)\s*[-:]\s*",
                    "",
                    merged_answer.lower(),
                    flags=re.I
                )

                if normalized_existing == normalized_new:
                    existing_generic = True
                    break

        if not existing_generic:

            faq_items.append({
                "question": "Cancellation Policy",
                "answer": merged_answer
            })
    faq_answers = [
        str(item["answer"]).lower()
        for item in faq_items
    ]
    seen_display_values = set()

    # ----------------------------------
    # Feature Cleaning
    # ----------------------------------

    features = []

    for feature in (
        vendor.get("about", {})
        .get("feature", [])
    ):
        value = feature.get("displayValue")
        if is_invalid_value(value):
            continue

        if (
            ": n/a" in str(value).lower()
            or ": na" in str(value).lower()
            or ": not available" in str(value).lower()
        ):
            continue

        if not value:
            continue

        if "wedmegood" in str(value).lower():
            continue

        if is_duplicate_feature(
            value,
            faq_answers
        ):
            continue

        norm = normalize_display_value(
            value
        )

        if norm in seen_display_values:
            continue

        seen_display_values.add(norm)

        features.append({
            "displayValue": value
        })
    # ----------------------------------
    # Policy Cleaning
    # ----------------------------------

    policies = []

    for policy in (
        vendor.get("about", {})
        .get("policy", [])
    ):
        value = policy.get("displayValue")
        if is_invalid_value(value):
            continue

        if (
            ": n/a" in str(value).lower()
            or ": na" in str(value).lower()
            or ": not available" in str(value).lower()
        ):
            continue

        if not value:
            continue

        if not policy.get("is_available"):
            continue

        if "wedmegood" in str(value).lower():
            continue

        if is_duplicate_feature(
            value,
            faq_answers
        ):
            continue

        norm = normalize_display_value(
            value
        )

        if norm in seen_display_values:
            continue

        seen_display_values.add(norm)

        policies.append({
            "displayValue": value
        })
    
    # ----------------------------------
    # Clean Output
    # ----------------------------------
    
    raw_phones = (
    profile.get("phone")
        or []
    )

    phones = []

    for phone in raw_phones:

        phone = normalize_phone(phone)

        if not phone or len(phone) < 6:
            continue

        if phone not in phones:
            phones.append(phone)

    indian_mobile = None

    for phone in phones:

        if is_indian_mobile(phone):
            indian_mobile = phone
            break

    if indian_mobile:
        phones.remove(indian_mobile)
        phones.insert(0, indian_mobile)

    result = {
        "VendorProfile": {
            "vendorSlug": vendor.get(
                "vendorSlug"
            ),
            "profile": {
                "name": profile.get(
                    "name"
                ),
                "city": profile.get(
                    "city"
                ),
                "other_cities": (
                    profile.get(
                        "other_cities"
                    )
                    or profile.get(
                        "otherCities"
                    )
                    or []
                ),
                "login_email": profile.get(
                    "login_email"
                ),
                "locality_name": profile.get(
                    "locality_name"
                ),
                "phone": phones,
                "addresses": [
                    {
                        "display_address": address.get(
                            "display_address"
                        ),
                        "long": (
                            address.get(
                                "longitude"
                            )
                            or address.get(
                                "long"
                            )
                        ),
                        "lat": (
                            address.get(
                                "latitude"
                            )
                            or address.get(
                                "lat"
                            )
                        ),
                    }
                    for address in profile.get(
                        "address",
                        [],
                    )
                ]
            },
            "videos": {
                "video_array": videos
            }
            if videos
            else None,
            "faq": faq_items,
            "pricing": list(
                pricing_map.values()
            ),
            "new_pricing": {
                "heading": new_pricing.get(
                    "heading"
                ),
                "price": [
                    {
                        "question": item.get(
                            "question"
                        ),
                        "price": item.get(
                            "price"
                        ),
                    }
                    for item in new_pricing.get(
                        "price",
                        [],
                    )
                ],
                "price_faq": [
                    {
                        "question": item.get(
                            "question"
                        ),
                        "answer": item.get(
                            "answer"
                        ),
                        "unit": item.get(
                            "unit"
                        ),
                    }
                    for item in new_pricing.get(
                        "price_faq",
                        [],
                    )
                ],
            }
            if new_pricing
            else None,
            "about": {
                "policy": policies
            },
            "documents": documents
            if documents
            else None,
        }
    }

    result = clean_strings(result)

    result = remove_phone_numbers(
        result
    )

    result = remove_emojis(
        result
    )

    return result

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file",
    )

    args = parser.parse_args()

    with open(
        args.input,
        "r",
        encoding="utf-8",
    ) as f:
        raw = json.load(f)

    clean = transform_vendor(raw)

    with open(
        args.output,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            clean,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Saved cleaned data to {args.output}"
    )


if __name__ == "__main__":
    main()