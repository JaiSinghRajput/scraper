import json

# ==========================
# CONFIGURATION
# ==========================

SINGLE_FILE_MODE = True      # True = process only FILE1
                              # False = process FILE1 + FILE2

FILE1 = "wedding_vanues_rajasthan.json"
FILE2 = "final_data_raw/wedding-venues/punjab/scraped_wedding_venues_punjab.json"

OUTPUT_FILE1 = "wedding_vanues_rajasthan_excluded.json"
OUTPUT_FILE2 = "scraped_wedding_vanues_punjab.json"

PRIMARY_KEY = "url"

RULES = [
    {
        "path": "address.area",
        "operator": "equals",
        "value": "jaipur"
    },
    {
        "path": "address.area",
        "operator": "equals",
        "value": "jodhpur"
    },
    {
        "path": "address.area",
        "operator": "equals",
        "value": "udaipur"
    },
]

# ==========================
# HELPERS
# ==========================

def get_nested_value(obj, path):
    current = obj

    for part in path.split("."):
        if not isinstance(current, dict):
            return None

        if part not in current:
            return None

        current = current[part]

    return current


def evaluate_rule(value, operator, expected):

    if operator == "equals":
        if isinstance(value, str) and isinstance(expected, str):
            return value.lower() == expected.lower()
        return value == expected

    elif operator == "not_equals":
        if isinstance(value, str) and isinstance(expected, str):
            return value.lower() != expected.lower()
        return value != expected

    elif operator == "contains":
        if value is None:
            return False

        if isinstance(value, list):
            return any(str(expected).lower() == str(v).lower() for v in value)

        return str(expected).lower() in str(value).lower()

    elif operator == "starts_with":
        return isinstance(value, str) and value.lower().startswith(str(expected).lower())

    elif operator == "ends_with":
        return isinstance(value, str) and value.lower().endswith(str(expected).lower())

    elif operator == "greater_than":
        return float(value) > float(expected)

    elif operator == "less_than":
        return float(value) < float(expected)

    elif operator == "exists":
        return value is not None

    elif operator == "is_null":
        return value is None

    raise ValueError(f"Unsupported operator: {operator}")


def matches_rules(obj):
    """Returns True if ANY rule matches."""
    for rule in RULES:
        value = get_nested_value(obj, rule["path"])

        if evaluate_rule(value, rule["operator"], rule.get("value")):
            return True

    return False


# ==========================
# LOAD FILES
# ==========================

with open(FILE1, "r", encoding="utf-8") as f:
    data1 = json.load(f)

original_file1 = len(data1)

if not SINGLE_FILE_MODE:
    with open(FILE2, "r", encoding="utf-8") as f:
        data2 = json.load(f)
    original_file2 = len(data2)

# ==========================
# FIND URLS TO REMOVE
# ==========================

urls_to_remove = {
    obj[PRIMARY_KEY]
    for obj in data1
    if PRIMARY_KEY in obj and matches_rules(obj)
}

# ==========================
# FILTER FILE1
# ==========================

filtered1 = [
    obj for obj in data1
    if obj.get(PRIMARY_KEY) not in urls_to_remove
]

with open(OUTPUT_FILE1, "w", encoding="utf-8") as f:
    json.dump(filtered1, f, indent=4, ensure_ascii=False)

# ==========================
# FILTER FILE2 (OPTIONAL)
# ==========================

if not SINGLE_FILE_MODE:

    filtered2 = [
        obj for obj in data2
        if obj.get(PRIMARY_KEY) not in urls_to_remove
    ]

    with open(OUTPUT_FILE2, "w", encoding="utf-8") as f:
        json.dump(filtered2, f, indent=4, ensure_ascii=False)

# ==========================
# SUMMARY
# ==========================

print("\n========== SUMMARY ==========")
print(f"Original File 1 Objects : {original_file1}")
print(f"URLs Matched            : {len(urls_to_remove)}")
print(f"Removed From File 1     : {original_file1 - len(filtered1)}")
print(f"Remaining File 1        : {len(filtered1)}")

if not SINGLE_FILE_MODE:
    print(f"Original File 2 Objects : {original_file2}")
    print(f"Removed From File 2     : {original_file2 - len(filtered2)}")
    print(f"Remaining File 2        : {len(filtered2)}")

print("=============================")