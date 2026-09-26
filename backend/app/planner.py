"""Rule-based meal ideas filtered against a structured demo ingredient catalog."""

from datetime import datetime, timezone
import random
import re
from uuid import uuid4


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
