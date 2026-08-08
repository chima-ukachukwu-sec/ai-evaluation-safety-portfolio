"""
Tools for the part of AI evaluation that is not the model: rubric structure,
inter-rater agreement and rater calibration.
"""

from .agreement import (AgreementError, AgreementResult, cohens_kappa,
                        fleiss_kappa, interpret, krippendorff_alpha, rater_bias)
from .schema import Finding, RubricError, load_rubric, summarise, validate

__all__ = ["cohens_kappa", "fleiss_kappa", "krippendorff_alpha", "rater_bias",
           "interpret", "AgreementResult", "AgreementError",
           "validate", "load_rubric", "summarise", "Finding", "RubricError"]
__version__ = "0.1.0"
