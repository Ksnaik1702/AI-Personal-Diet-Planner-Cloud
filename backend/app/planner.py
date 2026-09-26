"""AI-assisted meal selection over a locally checked ingredient catalog."""

from datetime import datetime, timezone
import json
import logging
import os
import random
import re
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from google import genai


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logger = logging.getLogger(__name__)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

AI_PLAN_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "breakfast": {"type": "string"},
                    "lunch": {"type": "string"},
                    "dinner": {"type": "string"},
                },
                "required": ["day", "breakfast", "lunch", "dinner"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["days"],
    "additionalProperties": False,
}

MEAL_INGREDIENTS = {
    "Vegetable poha with apple (no peanut garnish)": ("poha", "flattened rice", "potato", "peas", "onion", "apple", "lemon", "sunflower oil", "turmeric"),
    "Vegetable poha with peanut garnish": ("poha", "flattened rice", "potato", "peas", "onion", "apple", "peanut", "lemon", "sunflower oil", "turmeric"),
    "Idli with sambar": ("idli", "rice", "urad dal", "lentil", "toor dal", "vegetables", "tomato", "tamarind", "spices"),
    "Besan chilla with mint chutney": ("besan", "chickpea flour", "onion", "tomato", "coriander", "mint", "lemon", "spices"),
    "Besan chilla with tomato chutney": ("besan", "chickpea flour", "onion", "tomato", "coriander", "mint", "lemon", "spices"),
    "Oats porridge made with water and apple": ("oats", "water", "apple", "cinnamon"),
    "Banana oats porridge made with water": ("oats", "water", "banana", "cinnamon"),
    "Vegetable upma with cashews": ("upma", "semolina", "wheat", "vegetables", "onion", "peas", "cashew", "cashews", "sunflower oil", "spices"),
    "Sesame vegetable uttapam": ("uttapam", "rice", "urad dal", "lentil", "sesame", "vegetables", "onion", "tomato"),
    "Dal, rice, and mixed vegetable sabzi": ("dal", "lentils", "rice", "vegetables", "carrot", "peas", "cauliflower", "onion", "tomato", "spices"),
    "Rajma with rice and cucumber salad": ("rajma", "kidney beans", "rice", "cucumber", "tomato", "onion", "lemon"),
    "Paneer bhurji with roti and vegetables": ("paneer", "milk", "wheat", "roti", "onion", "tomato", "bell pepper", "vegetables", "spices"),
    "Chole with roti and salad": ("chole", "chickpeas", "wheat", "roti", "cucumber", "tomato", "onion", "lettuce", "salad", "spices"),
    "Peanut and vegetable curry with rice": ("peanut", "groundnut", "vegetables", "tomato", "onion", "rice", "spices"),
    "Vegetable pulao with cashews": ("rice", "vegetables", "carrot", "peas", "cashew", "cashews", "spices"),
    "Vegetable khichdi with curd": ("khichdi", "rice", "lentils", "vegetables", "curd", "yogurt", "milk", "spices"),
    "Vegetable khichdi": ("khichdi", "rice", "lentils", "vegetables", "spices"),
    "Palak paneer with roti": ("spinach", "palak", "paneer", "milk", "wheat", "roti", "onion", "tomato", "spices"),
    "Mixed vegetable pulao with raita": ("rice", "vegetables", "carrot", "peas", "raita", "yogurt", "curd", "milk"),
    "Dal and roti with seasonal vegetables": ("dal", "lentils", "wheat", "roti", "seasonal vegetables", "carrot", "peas", "onion", "tomato"),
    "Sesame tofu with rice": ("sesame", "tofu", "soy", "soybean", "rice", "vegetables"),
    "Chana masala with rice": ("chana", "chickpeas", "tomato", "onion", "rice", "spices"),
    "Tofu and vegetable rice bowl": ("tofu", "soy", "soybean", "vegetables", "rice"),
    "Chickpea and vegetable curry with roti": ("chickpeas", "vegetables", "tomato", "onion", "wheat", "roti", "spices"),
    "Mixed vegetable pulao with a side salad": ("rice", "vegetables", "carrot", "peas", "cucumber", "tomato", "lettuce", "salad"),
    "Lentil soup with roti and vegetables": ("lentils", "soup", "vegetables", "carrot", "onion", "tomato", "wheat", "roti"),
    "Vegetable omelette with toast": ("egg", "eggs", "vegetables", "onion", "tomato", "bread", "wheat", "toast"),
    "Grilled fish with rice and vegetables": ("fish", "rice", "vegetables", "carrot", "peas", "lemon"),
    "Fish curry with rice": ("fish", "curry", "tomato", "onion", "spices", "rice"),
    "Chickpea salad with roti": ("chickpeas", "cucumber", "tomato", "lettuce", "salad", "wheat", "roti"),
    "Shrimp curry with rice": ("shrimp", "prawn", "shellfish", "tomato", "onion", "spices", "rice"),
    "Baked fish with vegetables and rice": ("fish", "vegetables", "carrot", "peas", "rice", "lemon"),
    "Paneer and vegetable roti rolls": ("paneer", "milk", "vegetables", "wheat", "roti", "onion", "tomato"),
    "Shrimp and vegetable rice bowl": ("shrimp", "prawn", "shellfish", "vegetables", "rice"),
    "Egg bhurji with toast": ("egg", "eggs", "bread", "wheat", "toast", "onion", "tomato"),
    "Chicken curry with rice and vegetables": ("chicken", "tomato", "onion", "spices", "rice", "vegetables"),
    "Grilled chicken with roti and salad": ("chicken", "wheat", "roti", "cucumber", "tomato", "lettuce", "salad"),
    "Chicken and vegetable rice bowl": ("chicken", "vegetables", "rice"),
}

GENERIC_INGREDIENTS = {
    "vegetables": ("carrot", "potato", "peas", "beans", "cauliflower", "onion", "tomato", "bell pepper", "spinach", "zucchini", "eggplant"),
    "seasonal vegetables": ("carrot", "potato", "peas", "beans", "cauliflower", "onion", "tomato", "spinach"),
    "spices": ("cumin", "coriander", "turmeric", "black pepper", "chili", "ginger", "garlic", "mustard", "salt"),
    "salad": ("cucumber", "tomato", "lettuce"),
}


def expanded_ingredients(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({ingredient for value in values for ingredient in GENERIC_INGREDIENTS.get(value, (value,))}))


def ingredient_tokens(values: tuple[str, ...]) -> frozenset[str]:
    terms: set[str] = set()
    for phrase in expanded_ingredients(values):
        for token in re.findall(r"[a-z0-9]+", phrase.casefold()):
            terms.add(token[:-1] if token.endswith("s") and len(token) > 3 and not token.endswith("ss") else token)
    return frozenset(terms)


def normalize_term(term: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "", term.casefold())
    return token[:-1] if token.endswith("s") and len(token) > 3 and not token.endswith("ss") else token


def meal(name: str, *allergens: str) -> dict[str, object]:
    return {
        "name": name,
        "allergens": frozenset(allergens),
        "ingredients": expanded_ingredients(MEAL_INGREDIENTS[name]),
        "ingredientTerms": ingredient_tokens(MEAL_INGREDIENTS[name]),
    }


# These are fixed demo recipe variants. Their tags describe listed ingredients,
# not brand ingredients, substitutions, kitchen handling, or cross-contact.
MEAL_IDEAS = {
    "vegetarian": {
        "breakfast": [
            meal("Vegetable poha with apple (no peanut garnish)"),
            meal("Vegetable poha with peanut garnish", "peanut"),
            meal("Idli with sambar"),
            meal("Besan chilla with mint chutney"),
            meal("Oats porridge made with water and apple", "gluten"),
            meal("Banana oats porridge made with water", "gluten"),
            meal("Vegetable upma with cashews", "gluten", "tree_nuts"),
            meal("Sesame vegetable uttapam", "sesame"),
        ],
        "lunch": [
            meal("Dal, rice, and mixed vegetable sabzi"),
            meal("Rajma with rice and cucumber salad"),
            meal("Paneer bhurji with roti and vegetables", "milk", "gluten"),
            meal("Chole with roti and salad", "gluten"),
            meal("Peanut and vegetable curry with rice", "peanut"),
            meal("Vegetable pulao with cashews", "tree_nuts"),
        ],
        "dinner": [
            meal("Vegetable khichdi with curd", "milk"),
            meal("Palak paneer with roti", "milk", "gluten"),
            meal("Mixed vegetable pulao with raita", "milk"),
            meal("Dal and roti with seasonal vegetables", "gluten"),
            meal("Sesame tofu with rice", "sesame", "soy"),
        ],
    },
    "vegan": {
        "breakfast": [
            meal("Vegetable poha with apple (no peanut garnish)"),
            meal("Vegetable poha with peanut garnish", "peanut"),
            meal("Besan chilla with tomato chutney"),
            meal("Oats porridge made with water and apple", "gluten"),
            meal("Banana oats porridge made with water", "gluten"),
            meal("Vegetable upma with cashews", "gluten", "tree_nuts"),
            meal("Sesame vegetable uttapam", "sesame"),
        ],
        "lunch": [
            meal("Chana masala with rice"),
            meal("Dal, rice, and mixed vegetable sabzi"),
            meal("Rajma with rice and cucumber salad"),
            meal("Tofu and vegetable rice bowl", "soy"),
            meal("Peanut and vegetable curry with rice", "peanut"),
            meal("Vegetable pulao with cashews", "tree_nuts"),
        ],
        "dinner": [
            meal("Vegetable khichdi"),
            meal("Chickpea and vegetable curry with roti", "gluten"),
            meal("Mixed vegetable pulao with a side salad"),
            meal("Lentil soup with roti and vegetables", "gluten"),
            meal("Sesame tofu with rice", "sesame", "soy"),
        ],
    },
    "pescatarian": {
        "breakfast": [
            meal("Vegetable poha with apple (no peanut garnish)"),
            meal("Vegetable poha with peanut garnish", "peanut"),
            meal("Idli with sambar"),
            meal("Oats porridge made with water and apple", "gluten"),
            meal("Banana oats porridge made with water", "gluten"),
            meal("Vegetable omelette with toast", "egg", "gluten"),
            meal("Vegetable upma with cashews", "gluten", "tree_nuts"),
            meal("Sesame vegetable uttapam", "sesame"),
        ],
        "lunch": [
            meal("Grilled fish with rice and vegetables", "fish"),
            meal("Dal, rice, and mixed vegetable sabzi"),
            meal("Fish curry with rice", "fish"),
            meal("Chickpea salad with roti", "gluten"),
            meal("Shrimp curry with rice", "shellfish"),
            meal("Vegetable pulao with cashews", "tree_nuts"),
        ],
        "dinner": [
            meal("Vegetable khichdi"),
            meal("Baked fish with vegetables and rice", "fish"),
            meal("Paneer and vegetable roti rolls", "milk", "gluten"),
            meal("Dal and roti with seasonal vegetables", "gluten"),
            meal("Sesame tofu with rice", "sesame", "soy"),
            meal("Shrimp and vegetable rice bowl", "shellfish"),
        ],
    },
    "omnivore": {
        "breakfast": [
            meal("Vegetable poha with apple (no peanut garnish)"),
            meal("Vegetable poha with peanut garnish", "peanut"),
            meal("Egg bhurji with toast", "egg", "gluten"),
            meal("Oats porridge made with water and apple", "gluten"),
            meal("Banana oats porridge made with water", "gluten"),
            meal("Idli with sambar"),
            meal("Vegetable upma with cashews", "gluten", "tree_nuts"),
            meal("Sesame vegetable uttapam", "sesame"),
        ],
        "lunch": [
            meal("Chicken curry with rice and vegetables"),
            meal("Dal, rice, and mixed vegetable sabzi"),
            meal("Grilled chicken with roti and salad", "gluten"),
            meal("Rajma with rice and cucumber salad"),
            meal("Shrimp curry with rice", "shellfish"),
            meal("Vegetable pulao with cashews", "tree_nuts"),
        ],
        "dinner": [
            meal("Vegetable khichdi"),
            meal("Fish curry with rice", "fish"),
            meal("Dal and roti with seasonal vegetables", "gluten"),
            meal("Chicken and vegetable rice bowl"),
            meal("Sesame tofu with rice", "sesame", "soy"),
            meal("Shrimp and vegetable rice bowl", "shellfish"),
        ],
    },
}

PLAN_LENGTHS = {"week": 7, "two-weeks": 14, "month": 30}
NO_ALLERGY_ENTRIES = {"", "none", "no", "no allergies", "nil", "n/a", "na"}

# Explicit aliases accepted in the free-text profile field. Unrecognized words
# are rejected by the generator instead of silently being ignored.
ALLERGEN_ALIASES = {
    "milk": ("milk", "dairy", "casein", "whey", "curd", "paneer", "cheese", "butter", "ghee", "lactose"),
    "egg": ("egg", "eggs", "albumin"),
    "fish": ("fish",),
    "shellfish": ("shellfish", "crustacean", "crustaceans", "shrimp", "prawn", "prawns", "crab", "lobster"),
    "tree_nuts": ("tree nuts", "almond", "almonds", "cashew", "cashews", "pistachio", "pistachios", "walnut", "walnuts", "pecan", "pecans", "hazelnut", "hazelnuts", "macadamia"),
    "peanut": ("peanut", "peanuts", "groundnut", "groundnuts", "peanut oil", "groundnut oil"),
    "gluten": ("wheat", "gluten", "barley", "rye", "semolina", "durum", "spelt", "atta"),
    "soy": ("soy", "soya", "soybean", "soybeans", "tofu", "tempeh", "miso"),
    "sesame": ("sesame", "sesame oil", "tahini", "til"),
}
IGNORED_ALLERGY_WORDS = {"allergy", "allergies", "allergic", "intolerance", "intolerant", "to", "and", "or", "food", "foods", "avoid", "avoiding", "i", "am", "have", "with", "a", "the", "free", "none", "no", "nil", "na"}


def parse_allergens(entry: str) -> tuple[set[str], set[str]]:
    """Map known aliases to tags and leave other food words for direct matching."""
    normalized = entry.casefold().replace("-", " ")
    if normalized.strip() in NO_ALLERGY_ENTRIES:
        return set(), set()

    remaining = normalized
    detected: set[str] = set()
    aliases = sorted(
        ((alias, allergen) for allergen, words in ALLERGEN_ALIASES.items() for alias in words),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, allergen in aliases:
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, remaining):
            detected.add(allergen)
            remaining = re.sub(pattern, " ", remaining)

    for alias, categories in (("seafood", {"fish", "shellfish"}), ("nuts", {"peanut", "tree_nuts"}), ("nut", {"peanut", "tree_nuts"})):
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, remaining):
            detected.update(categories)
            remaining = re.sub(pattern, " ", remaining)

    food_terms = {
        normalize_term(token)
        for token in re.findall(r"[a-z0-9]+", remaining)
        if token not in IGNORED_ALLERGY_WORDS
    }
    return detected, food_terms


def generate_sample_plan(profile: dict[str, object]) -> dict[str, object]:
    """Return educational meal ideas after excluding tagged allergens."""
    allergens, avoid_terms = parse_allergens(str(profile.get("allergies", "")))

    diet = str(profile.get("diet", ""))
    if diet not in MEAL_IDEAS:
        return {
            "blocked": True,
            "message": "Choose vegetarian, vegan, pescatarian, or no specific preference to generate a meal plan.",
        }

    ideas = MEAL_IDEAS[diet]
    all_catalog_terms = set().union(*(idea["ingredientTerms"] for meals in ideas.values() for idea in meals))
    matched_avoid_terms = avoid_terms & all_catalog_terms
    review_items = avoid_terms - all_catalog_terms
    filtered_ideas = {
        slot: [
            idea for idea in meals
            if not (idea["allergens"] & allergens)
            and not (idea["ingredientTerms"] & avoid_terms)
        ]
        for slot, meals in ideas.items()
    }
    empty_slots = [slot for slot, meals in filtered_ideas.items() if not meals]

    days = PLAN_LENGTHS.get(str(profile.get("timeline", "week")), 7)
    plan_id = str(uuid4())
    rotation = random.Random(plan_id)
    for meals in filtered_ideas.values():
        rotation.shuffle(meals)

    daily_meals = []
    for day_index in range(days):
        selected = {
            slot: meals[day_index % len(meals)] if meals else None
            for slot, meals in filtered_ideas.items()
        }

        def recipe_name(slot: str) -> str:
            recipe = selected[slot]
            return recipe["name"] if recipe else "No matching meal in the current list; add a verified alternative"

        def recipe_ingredients(slot: str) -> list[str]:
            recipe = selected[slot]
            return list(recipe["ingredients"]) if recipe else []

        daily_meals.append({
            "day": day_index + 1,
            "breakfast": recipe_name("breakfast"),
            "breakfastIngredients": recipe_ingredients("breakfast"),
            "lunch": recipe_name("lunch"),
            "lunchIngredients": recipe_ingredients("lunch"),
            "dinner": recipe_name("dinner"),
            "dinnerIngredients": recipe_ingredients("dinner"),
        })

    notes = [
        "These are illustrative meal ideas, not a clinically designed diet plan.",
        "Meals matching your listed food exclusions were removed using their ingredient list and allergen tags.",
        "Recipe variations, packaged products, ingredient omissions, and kitchen cross-contact are not checked. Verify every ingredient and food label; this planner cannot guarantee allergen safety.",
        "This meal planner does not calculate portions, calories, nutrition, or budget.",
    ]
    if empty_slots:
        notes.append("No matching meals remain for: " + ", ".join(empty_slots) + ". Add verified alternatives for those meal slots.")

    return {
        "blocked": False,
        "planId": plan_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "title": f"{days}-day meal idea plan",
        "engine": "Ingredient-filtered meal ideas" if allergens or avoid_terms else "Personalized meal ideas",
        "dietStyle": diet,
        "excludedAllergens": sorted(allergens),
        "excludedIngredients": sorted(matched_avoid_terms),
        "reviewItems": sorted(review_items),
        "days": daily_meals,
        "notes": notes,
    }


def generate_personalized_plan(profile: dict[str, object]) -> dict[str, object]:
    """Use Gemini to arrange verified menu choices, with a local fallback."""
    fallback = generate_sample_plan(profile)
    if fallback["blocked"]:
        return fallback

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        fallback["engine"] = "Rule-based fallback (AI key not configured)"
        fallback["notes"].append("AI generation is not configured; this plan was assembled using local meal-selection rules.")
        return fallback

    diet = str(profile.get("diet", ""))
    allergens, avoid_terms = parse_allergens(str(profile.get("allergies", "")))
    available: dict[str, dict[str, dict[str, object]]] = {}
    for slot, meals in MEAL_IDEAS[diet].items():
        available[slot] = {
            item["name"]: item for item in meals
            if not (item["allergens"] & allergens)
            and not (item["ingredientTerms"] & avoid_terms)
        }

    if any(not meals for meals in available.values()):
        fallback["engine"] = "Rule-based fallback (no meals available for every slot)"
        fallback["notes"].append("The local meal selector was used because the current menu has no matching option for every meal slot.")
        return fallback

    allowed_names = {slot: list(meals) for slot, meals in available.items()}
    days = len(fallback["days"])
    # Only send non-sensitive preferences and already-filtered recipe names.
    # Raw allergy entries and body measurements stay on this server.
    prompt_data = {
        "diet_style": diet,
        "goal": str(profile.get("goal", "balanced")),
        "cuisine_preference": str(profile.get("cuisine", ""))[:200],
        "number_of_days": days,
        "available_meals_by_slot": allowed_names,
    }
    prompt = (
        "Create a varied, general-education meal idea schedule. You must choose each meal name "
        "exactly from the available_meals_by_slot list for that slot. Never invent, rename, or "
        "modify a recipe, and do not add ingredients, calories, quantities, or medical claims. "
        "Use day numbers from 1 through number_of_days in order. The menu was filtered on the "
        "server; do not override its choices. Return only data matching the requested JSON schema.\n\n"
        + json.dumps(prompt_data, ensure_ascii=False)
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.interactions.create(
            model=GEMINI_MODEL,
            input=prompt,
            store=False,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": AI_PLAN_RESPONSE_SCHEMA,
            },
        )
        generated = json.loads(response.output_text or "")
        generated_days = generated.get("days")
        if not isinstance(generated_days, list) or len(generated_days) != days:
            raise ValueError("Gemini returned an unexpected number of plan days")

        meal_by_slot_and_name = available
        validated_days: list[dict[str, object]] = []
        for index, generated_day in enumerate(generated_days, start=1):
            if generated_day.get("day") != index:
                raise ValueError("Gemini returned invalid day ordering")
            validated: dict[str, object] = {"day": index}
            for slot in ("breakfast", "lunch", "dinner"):
                name = generated_day.get(slot)
                recipe = meal_by_slot_and_name[slot].get(name) if isinstance(name, str) else None
                if recipe is None:
                    raise ValueError("Gemini selected a meal outside the filtered menu")
                validated[slot] = name
                validated[f"{slot}Ingredients"] = list(recipe["ingredients"])
            validated_days.append(validated)

        fallback["days"] = validated_days
        fallback["engine"] = f"Gemini AI meal planner ({GEMINI_MODEL})"
        return fallback
    except Exception:
        logger.exception("Gemini plan generation failed; using the local rule-based fallback")
        fallback["engine"] = "Rule-based fallback (AI unavailable)"
        fallback["notes"].append("AI generation was unavailable, so this plan was assembled using local meal-selection rules.")
        return fallback
