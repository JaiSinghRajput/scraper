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
    year_match = re.search(r"(19|20)\d{2}",answer)

    if ("since" in question.lower() and year_match):
        if year_match:

            year = int(
                year_match.group()
            )

            current_year = (
                datetime.now().year
            )

            exp = max(
                current_year - year,
                0
            )

            question = "Experience"
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
    for item in vendor.get("price_faq", []):
        add_price(
            item.get("question"),
            item.get("answer"),
            item.get("unit"),
        )

    # new_pricing.price[]
    new_pricing = vendor.get("new_pricing", {})

    for item in new_pricing.get("price", []):
        add_price(
            item.get("question"),
            item.get("price"),
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

    for item in vendor.get("faq", []):
        question = item.get("question")
        answer = item.get("answer")

        question, answer = normalize_faq(
            question,
            answer
        )
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

    return clean_strings(result)

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