import json

# =========================================================
# CONFIG
# =========================================================

INPUT_FILE = "wedding_planners_detailed.json"

# Fields to ignore completely
IGNORE_FIELDS = {
    "url",
}

# =========================================================
# LOAD JSON
# =========================================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# =========================================================
# HELPERS
# =========================================================

def is_empty(value):
    """
    Check if value is considered empty
    """

    if value is None:
        return True

    if isinstance(value, str) and value.strip() == "":
        return True

    if isinstance(value, list) and len(value) == 0:
        return True

    if isinstance(value, dict) and len(value) == 0:
        return True

    return False


def is_invalid(value, ignored_fields=None, current_key=""):
    """
    Recursive checker for nested objects
    """

    if ignored_fields is None:
        ignored_fields = set()

    # =====================================================
    # IGNORE FIELD
    # =====================================================

    if current_key in ignored_fields:
        return True

    # =====================================================
    # PRIMITIVE VALUES
    # =====================================================

    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    # =====================================================
    # LIST
    # =====================================================

    if isinstance(value, list):

        # empty list
        if len(value) == 0:
            return True

        # all list items invalid
        return all(
            is_invalid(item, ignored_fields)
            for item in value
        )

    # =====================================================
    # DICT
    # =====================================================

    if isinstance(value, dict):

        # empty dict
        if len(value) == 0:
            return True

        valid_found = False

        for key, val in value.items():

            # skip ignored fields
            if key in ignored_fields:
                continue

            if not is_invalid(val, ignored_fields, key):
                valid_found = True
                break

        return not valid_found

    # =====================================================
    # OTHER TYPES
    # =====================================================

    return False


# =========================================================
# PROCESS
# =========================================================

invalid_objects = []
valid_objects = []

for item in data:

    if is_invalid(item, IGNORE_FIELDS):
        invalid_objects.append(item)

    else:
        valid_objects.append(item)

# =========================================================
# SAVE RESULTS
# =========================================================

with open("invalid_objects.json", "w", encoding="utf-8") as f:
    json.dump(invalid_objects, f, indent=4, ensure_ascii=False)

with open("valid_objects.json", "w", encoding="utf-8") as f:
    json.dump(valid_objects, f, indent=4, ensure_ascii=False)

# =========================================================
# DONE
# =========================================================

print("Done!")

print(f"\nInvalid Objects : {len(invalid_objects)}")
print(f"Valid Objects   : {len(valid_objects)}")

print("\nIgnored Fields:")
for field in IGNORE_FIELDS:
    print("-", field)

print("\nGenerated Files:")
print("1. invalid_objects.json")
print("2. valid_objects.json")