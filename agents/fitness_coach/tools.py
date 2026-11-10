"""Fitness calculators the coach calls instead of doing arithmetic itself.

Every function here is pure: it reads its arguments and returns a dict, and
changes nothing outside the conversation. That is why none of them is declared
in `MANIFEST.actions` — they are reads, and autonomy policy governs actions.

Each returns `{"status": "success", ...}` or `{"status": "error",
"error_message": ...}` rather than raising, so a bad input becomes something
the model can read and ask the user about instead of a failed run.

The docstrings are the tool descriptions the model reads, so they say what
each argument means and which unit it is in.

No `from __future__ import annotations` in this file: ADK builds each tool's
schema from the real annotations, and the `Literal` types below are what turn
into the enums the model is constrained to.
"""

from typing import Literal, Optional

Sex = Literal["male", "female"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose_fat", "maintain", "build_muscle"]

# Bounds an adult's measurements fall within. Outside them the input is far
# more likely to be a unit mix-up (pounds as kilograms, metres as centimetres)
# than a real body, so the tool says so instead of returning a confident figure.
_WEIGHT_KG = (25.0, 350.0)
_HEIGHT_CM = (120.0, 250.0)
_AGE_YEARS = (18, 100)

# Standard multipliers on BMR for total daily energy expenditure.
_ACTIVITY_MULTIPLIER: dict[str, float] = {
    "sedentary": 1.2,     # desk job, little or no exercise
    "light": 1.375,       # light exercise 1-3 days a week
    "moderate": 1.55,     # moderate exercise 3-5 days a week
    "active": 1.725,      # hard exercise 6-7 days a week
    "very_active": 1.9,   # hard daily training or a physical job
}

# Change from maintenance calories for each goal: a ~20% deficit for fat loss
# and a ~10% surplus for a lean bulk.
_GOAL_ADJUSTMENT: dict[str, float] = {
    "lose_fat": -0.20,
    "maintain": 0.0,
    "build_muscle": 0.10,
}

# The lowest daily intake this coach will set without medical supervision.
_CALORIE_FLOOR: dict[str, int] = {"male": 1500, "female": 1200}

# Protein in grams per kg of reference body weight, per day.
#   maintain, sedentary  0.8-1.0  the RDA and a little above it
#   maintain, active     1.2-1.6  exercising adults
#   build_muscle         1.6-2.2  where gains plateau in meta-analysis
#   lose_fat             1.6-2.4  higher, to keep muscle in a deficit
_PROTEIN_G_PER_KG: dict[str, tuple[float, float]] = {
    "maintain_sedentary": (0.8, 1.0),
    "maintain_active": (1.2, 1.6),
    "build_muscle": (1.6, 2.2),
    "lose_fat": (1.6, 2.4),
}


def _error(message: str) -> dict:
    return {"status": "error", "error_message": message}


def _out_of_range(name: str, value: float, bounds: tuple[float, float], unit: str) -> Optional[dict]:
    low, high = bounds
    if not low <= value <= high:
        return _error(
            f"{name} of {value} {unit} is outside {low:g}-{high:g} {unit}. "
            f"Check the unit: this tool takes {unit}."
        )
    return None


def _bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return weight_kg / (height_m * height_m)


def calculate_bmi(weight_kg: float, height_cm: float, asian_cutoffs: bool = False) -> dict:
    """Calculate an adult's Body Mass Index and its weight category.

    Use this whenever the user asks for their BMI or whether their weight is
    healthy for their height. Adults only: BMI for under-18s is read against
    age-and-sex percentiles, which this tool does not do.

    Args:
        weight_kg: Body weight in kilograms. Convert pounds first (1 lb = 0.4536 kg).
        height_cm: Height in centimetres. Convert feet and inches first (1 in = 2.54 cm).
        asian_cutoffs: True to use the lower WHO Asia-Pacific thresholds
            (overweight from 23, obese from 25) instead of the standard WHO
            ones. Use it when the user says they are of Asian descent.

    Returns:
        A dict with `bmi`, `category`, the cut-offs used, and the healthy
        weight range in kilograms for this height.
    """
    for problem in (
        _out_of_range("Weight", weight_kg, _WEIGHT_KG, "kg"),
        _out_of_range("Height", height_cm, _HEIGHT_CM, "cm"),
    ):
        if problem:
            return problem

    # Categorised on the ROUNDED figure, so a reported 25.0 is never "normal".
    bmi = round(_bmi(weight_kg, height_cm), 1)
    height_m = height_cm / 100

    if asian_cutoffs:
        bands = [(18.5, "underweight"), (23.0, "normal"), (25.0, "overweight"),
                 (30.0, "obese class I")]
        top = "obese class II"
        healthy_upper = 22.9
        standard = "WHO Asia-Pacific"
    else:
        bands = [(18.5, "underweight"), (25.0, "normal"), (30.0, "overweight"),
                 (35.0, "obese class I"), (40.0, "obese class II")]
        top = "obese class III"
        healthy_upper = 24.9
        standard = "WHO"

    category = next((name for limit, name in bands if bmi < limit), top)

    return {
        "status": "success",
        "bmi": bmi,
        "category": category,
        "cutoffs": standard,
        "healthy_weight_range_kg": [
            round(18.5 * height_m * height_m, 1),
            round(healthy_upper * height_m * height_m, 1),
        ],
        "note": (
            "BMI does not tell muscle from fat, so it over-reads muscular "
            "people and can under-read older adults. Treat it as a screen, not a diagnosis."
        ),
    }


def calculate_daily_calories(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: Sex,
    activity_level: ActivityLevel,
    goal: Goal,
) -> dict:
    """Estimate daily calorie needs: BMR, maintenance, and a target for a goal.

    Uses the Mifflin-St Jeor equation for basal metabolic rate (BMR), scales
    it by activity to get maintenance calories (TDEE), then adjusts for the
    goal: a 20% deficit to lose fat, a 10% surplus to build muscle. A fat-loss
    target never drops below 1500 kcal for men or 1200 kcal for women.

    Args:
        weight_kg: Body weight in kilograms.
        height_cm: Height in centimetres.
        age_years: Age in whole years. Adults only (18+).
        sex: "male" or "female", as the equation is calibrated on.
        activity_level: One of "sedentary" (desk job, little exercise),
            "light" (exercise 1-3 days a week), "moderate" (3-5 days),
            "active" (6-7 days), "very_active" (hard daily training or a
            physical job).
        goal: One of "lose_fat", "maintain" or "build_muscle".

    Returns:
        A dict with `bmr_kcal`, `maintenance_kcal`, `target_kcal`, and notes,
        including whether the target was raised to the safety floor.
    """
    for problem in (
        _out_of_range("Weight", weight_kg, _WEIGHT_KG, "kg"),
        _out_of_range("Height", height_cm, _HEIGHT_CM, "cm"),
        _out_of_range("Age", age_years, _AGE_YEARS, "years"),
    ):
        if problem:
            return problem
    if sex not in _CALORIE_FLOOR:
        return _error(f"sex must be 'male' or 'female', not {sex!r}.")
    if activity_level not in _ACTIVITY_MULTIPLIER:
        return _error(f"activity_level must be one of {sorted(_ACTIVITY_MULTIPLIER)}.")
    if goal not in _GOAL_ADJUSTMENT:
        return _error(f"goal must be one of {sorted(_GOAL_ADJUSTMENT)}.")

    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age_years + (5 if sex == "male" else -161)
    maintenance = bmr * _ACTIVITY_MULTIPLIER[activity_level]
    target = maintenance * (1 + _GOAL_ADJUSTMENT[goal])

    notes: list[str] = []
    floor = _CALORIE_FLOOR[sex]
    # The floor guards a DEFICIT. A small, older person's true maintenance can
    # sit under it, and telling them to eat more than that to maintain would
    # be wrong, so it applies to fat loss only.
    if goal == "lose_fat" and target < floor:
        # If maintenance itself is under the floor, holding at maintenance is
        # the most a diet alone can safely do; the deficit has to come from
        # moving more.
        target = min(floor, maintenance)
        if target == maintenance:
            notes.append(
                "Maintenance is already below the safe minimum for a diet, so "
                "the target is held at maintenance. Fat loss should come from "
                "more activity, ideally with a professional's guidance."
            )
        else:
            notes.append(f"Target raised to the {floor} kcal safety floor.")

    if goal == "lose_fat":
        notes.append("Expect roughly 0.5-1% of body weight lost per week.")
    elif goal == "build_muscle":
        notes.append("Aim for about 0.25-0.5% of body weight gained per week.")
    notes.append("These are estimates; adjust by ~100-200 kcal after 2-3 weeks of tracking.")

    return {
        "status": "success",
        "formula": "Mifflin-St Jeor",
        "bmr_kcal": round(bmr),
        "maintenance_kcal": round(maintenance / 10) * 10,
        "target_kcal": round(target / 10) * 10,
        "goal": goal,
        "activity_multiplier": _ACTIVITY_MULTIPLIER[activity_level],
        "notes": notes,
    }


def calculate_daily_protein(
    weight_kg: float,
    goal: Goal,
    activity_level: ActivityLevel,
    height_cm: Optional[float] = None,
) -> dict:
    """Recommend how many grams of protein to eat per day.

    Ranges in grams per kg of body weight: 0.8-1.0 for a sedentary person
    maintaining, 1.2-1.6 for an active person maintaining, 1.6-2.2 to build
    muscle, and 1.6-2.4 to lose fat while keeping muscle.

    Pass height_cm whenever you know it. With it, a person whose BMI is 30 or
    more is dosed on the weight they would have at BMI 25, because total body
    weight overstates what someone carrying a lot of fat needs.

    Args:
        weight_kg: Body weight in kilograms.
        goal: One of "lose_fat", "maintain" or "build_muscle".
        activity_level: One of "sedentary", "light", "moderate", "active",
            "very_active". It changes the range only for "maintain".
        height_cm: Height in centimetres. Optional, but makes the figure
            right for people with obesity.

    Returns:
        A dict with `min_g`, `max_g`, a `target_g` in the middle, the grams
        per kg used, and the reference weight it was computed against.
    """
    problem = _out_of_range("Weight", weight_kg, _WEIGHT_KG, "kg")
    if problem:
        return problem
    if height_cm is not None:
        problem = _out_of_range("Height", height_cm, _HEIGHT_CM, "cm")
        if problem:
            return problem
    if goal not in _GOAL_ADJUSTMENT:
        return _error(f"goal must be one of {sorted(_GOAL_ADJUSTMENT)}.")
    if activity_level not in _ACTIVITY_MULTIPLIER:
        return _error(f"activity_level must be one of {sorted(_ACTIVITY_MULTIPLIER)}.")

    if goal == "maintain":
        key = "maintain_sedentary" if activity_level == "sedentary" else "maintain_active"
    else:
        key = goal
    low, high = _PROTEIN_G_PER_KG[key]

    reference_kg = weight_kg
    basis = "total body weight"
    if height_cm is not None and _bmi(weight_kg, height_cm) >= 30:
        height_m = height_cm / 100
        reference_kg = 25 * height_m * height_m
        basis = "weight at BMI 25 for this height, because BMI is 30 or more"

    return {
        "status": "success",
        "min_g": round(low * reference_kg),
        "max_g": round(high * reference_kg),
        "target_g": round((low + high) / 2 * reference_kg),
        "g_per_kg": [low, high],
        "reference_weight_kg": round(reference_kg, 1),
        "basis": basis,
        "notes": [
            "Spread it over 3-5 meals of roughly 20-40 g each.",
            "Anyone with kidney disease should agree a protein target with their doctor first.",
        ],
    }


def calculate_macros(target_kcal: float, protein_g: float, fat_percent: float = 25.0) -> dict:
    """Split a daily calorie target into protein, fat and carbohydrate grams.

    Protein is fixed at the grams given, fat takes `fat_percent` of calories,
    and carbohydrates fill the rest. Use it after calculate_daily_calories
    and calculate_daily_protein, passing their `target_kcal` and `target_g`.

    Args:
        target_kcal: Daily calorie target.
        protein_g: Daily protein in grams.
        fat_percent: Share of calories from fat, 20-40. Defaults to 25.

    Returns:
        A dict with grams and calories for each macronutrient, and the share
        of the day's calories each one makes up.
    """
    if not 800 <= target_kcal <= 6000:
        return _error(f"target_kcal of {target_kcal} is outside 800-6000 kcal.")
    if not 0 < protein_g <= 500:
        return _error(f"protein_g of {protein_g} is outside 1-500 g.")
    if not 20 <= fat_percent <= 40:
        return _error(
            f"fat_percent of {fat_percent} is outside 20-40. Below 20% risks "
            "too little essential fat; above 40% is a specialised diet this tool does not plan."
        )

    protein_kcal = protein_g * 4
    fat_kcal = target_kcal * fat_percent / 100
    carb_kcal = target_kcal - protein_kcal - fat_kcal
    if carb_kcal < 0:
        return _error(
            f"{protein_g:g} g protein and {fat_percent:g}% fat already exceed "
            f"{target_kcal:g} kcal. Lower the protein or fat, or raise the calories."
        )

    def share(kcal: float) -> int:
        return round(100 * kcal / target_kcal)

    return {
        "status": "success",
        "target_kcal": round(target_kcal),
        "protein": {"g": round(protein_g), "kcal": round(protein_kcal), "percent": share(protein_kcal)},
        "fat": {"g": round(fat_kcal / 9), "kcal": round(fat_kcal), "percent": share(fat_kcal)},
        "carbs": {"g": round(carb_kcal / 4), "kcal": round(carb_kcal), "percent": share(carb_kcal)},
        "basis": "4 kcal per g protein and carbohydrate, 9 kcal per g fat",
    }
