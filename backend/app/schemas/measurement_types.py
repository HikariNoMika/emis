"""Pydantic schema for measurement types."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("ATMOSPHERIC", "WIND", "PRECIPITATION", "SOLAR", "SOIL", "EQUIPMENT")
AGGREGATIONS = ("AVG", "SUM", "MIN", "MAX", "CIRCULAR_MEAN", "NONE")


class MeasurementTypeSchema(BaseModel):
    code: Optional[str] = Field(default=None, max_length=80)
    name: Optional[str] = Field(default=None, max_length=150)
    category: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=40)
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    is_circular: bool = False
    aggregation_method: str = "AVG"
    description: Optional[str] = None

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        if value is not None and value not in CATEGORIES:
            raise ValueError(f"Category must be one of {CATEGORIES}")
        return value

    @field_validator("aggregation_method")
    @classmethod
    def check_aggregation(cls, value):
        if value not in AGGREGATIONS:
            raise ValueError(f"Aggregation must be one of {AGGREGATIONS}")
        return value
