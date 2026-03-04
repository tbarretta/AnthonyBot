from django.core.exceptions import ValidationError


class LettersAndNumbersValidator:
    """Password must contain at least one letter and one number."""

    def validate(self, password, user=None):
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        if not has_letter or not has_number:
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return "Your password must contain at least one letter and one number."
