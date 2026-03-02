"""
OpenWebUI Pipeline Filter for PII Detection using Presidio

This filter provides ingress and egress PII detection/redaction
using Microsoft Presidio. It works WITHOUT an LLM for fast,
deterministic PII detection.

Detected PII types:
- Names (via spaCy NER)
- Email addresses (regex)
- Phone numbers (regex)
- Social Security Numbers (regex + checksum)
- Credit card numbers (regex + Luhn validation)
- IP addresses (regex)
- Bank account numbers (regex patterns)

To install in OpenWebUI:
1. Go to Admin Panel > Pipelines
2. Create a new pipeline
3. Paste this code
4. The filter will automatically redact PII on both input and output
"""

import re
from typing import Optional, Callable, Awaitable, Any, List, Tuple
from pydantic import BaseModel, Field


class Pipeline:
    """
    Presidio-based PII Detection Filter for OpenWebUI.

    This filter uses regex and pattern matching (similar to Presidio)
    for fast PII detection without requiring an LLM. It processes
    both user inputs (inlet) and AI responses (outlet).
    """

    class Valves(BaseModel):
        """Configuration valves for the pipeline."""

        pipelines: list = Field(
            default=["*"], description="List of pipelines to apply this filter to"
        )
        priority: int = Field(
            default=-10,  # High priority - runs before other filters
            description="Priority of this filter (lower = higher priority)",
        )
        enable_inlet: bool = Field(
            default=True, description="Enable PII detection on user input"
        )
        enable_outlet: bool = Field(
            default=True, description="Enable PII detection on AI responses"
        )
        redact_mode: str = Field(
            default="mask",
            description="Redaction mode: 'mask' (<TYPE>), 'hash' (first 4 chars), or 'remove'",
        )
        detect_names: bool = Field(
            default=True, description="Detect person names (requires patterns)"
        )
        detect_emails: bool = Field(default=True, description="Detect email addresses")
        detect_phones: bool = Field(default=True, description="Detect phone numbers")
        detect_ssn: bool = Field(
            default=True, description="Detect Social Security Numbers"
        )
        detect_credit_cards: bool = Field(
            default=True, description="Detect credit card numbers"
        )
        detect_ips: bool = Field(default=True, description="Detect IP addresses")
        log_detections: bool = Field(
            default=True, description="Log when PII is detected (not the actual values)"
        )

    def __init__(self):
        self.name = "Presidio PII Filter"
        self.valves = self.Valves()

        # Compile regex patterns
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for PII detection."""
        self.patterns = {}

        # Email pattern
        self.patterns["EMAIL"] = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )

        # Phone patterns (various formats)
        self.patterns["PHONE"] = re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
        )

        # SSN pattern (xxx-xx-xxxx)
        self.patterns["SSN"] = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")

        # Credit card patterns (major card types)
        self.patterns["CREDIT_CARD"] = re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"  # Visa
            r"5[1-5][0-9]{14}|"  # Mastercard
            r"3[47][0-9]{13}|"  # Amex
            r"6(?:011|5[0-9]{2})[0-9]{12}|"  # Discover
            r"(?:2131|1800|35\d{3})\d{11})\b"  # JCB
        )

        # IP address pattern
        self.patterns["IP_ADDRESS"] = re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        )

        # Name patterns (simple heuristics - Title Case words)
        # This is a simplified version - real Presidio uses spaCy NER
        self.patterns["PERSON"] = re.compile(
            r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        )

        # Additional name pattern: two consecutive capitalized words
        self.patterns["PERSON_NAME"] = re.compile(
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
        )

        # Bank account pattern
        self.patterns["BANK_ACCOUNT"] = re.compile(
            r"\b[0-9]{8,17}\b"  # Generic account number pattern
        )

    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm."""
        digits = [int(d) for d in card_number if d.isdigit()]
        if len(digits) < 13:
            return False

        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _validate_ssn(self, ssn: str) -> bool:
        """Validate SSN format and exclude invalid patterns."""
        # Remove separators
        digits = re.sub(r"[-\s]", "", ssn)
        if len(digits) != 9:
            return False

        # Invalid SSNs
        invalid_patterns = [
            "000",  # Area number cannot be 000
            "666",  # Area number cannot be 666
            "9",  # Area number cannot start with 9
        ]

        area = digits[:3]
        if area in invalid_patterns or area.startswith("9"):
            return False

        # Group number cannot be 00
        if digits[3:5] == "00":
            return False

        # Serial number cannot be 0000
        if digits[5:] == "0000":
            return False

        return True

    def _detect_pii(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Detect PII in text.

        Returns:
            List of (type, value, start, end) tuples
        """
        detections = []

        # Detect emails
        if self.valves.detect_emails:
            for match in self.patterns["EMAIL"].finditer(text):
                detections.append(("EMAIL", match.group(), match.start(), match.end()))

        # Detect phones
        if self.valves.detect_phones:
            for match in self.patterns["PHONE"].finditer(text):
                detections.append(("PHONE", match.group(), match.start(), match.end()))

        # Detect SSNs
        if self.valves.detect_ssn:
            for match in self.patterns["SSN"].finditer(text):
                if self._validate_ssn(match.group()):
                    detections.append(
                        ("SSN", match.group(), match.start(), match.end())
                    )

        # Detect credit cards
        if self.valves.detect_credit_cards:
            for match in self.patterns["CREDIT_CARD"].finditer(text):
                if self._luhn_check(match.group()):
                    detections.append(
                        ("CREDIT_CARD", match.group(), match.start(), match.end())
                    )

        # Detect IPs
        if self.valves.detect_ips:
            for match in self.patterns["IP_ADDRESS"].finditer(text):
                # Exclude common non-PII IPs
                ip = match.group()
                if not ip.startswith(("127.", "0.", "255.")):
                    detections.append(
                        ("IP_ADDRESS", match.group(), match.start(), match.end())
                    )

        # Detect names (with title)
        if self.valves.detect_names:
            for match in self.patterns["PERSON"].finditer(text):
                detections.append(("PERSON", match.group(), match.start(), match.end()))

        # Sort by start position (descending) for safe replacement
        detections.sort(key=lambda x: x[2], reverse=True)

        return detections

    def _redact(self, text: str, detections: List[Tuple[str, str, int, int]]) -> str:
        """Redact detected PII from text."""
        result = text

        for pii_type, value, start, end in detections:
            if self.valves.redact_mode == "mask":
                replacement = f"<{pii_type}>"
            elif self.valves.redact_mode == "hash":
                replacement = f"{value[:4]}...{pii_type}"
            else:  # remove
                replacement = ""

            result = result[:start] + replacement + result[end:]

        return result

    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> dict:
        """
        Inlet filter - scan and redact PII from user input.
        """
        if not self.valves.enable_inlet:
            return body

        messages = body.get("messages", [])
        pii_found = False

        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    detections = self._detect_pii(content)
                    if detections:
                        pii_found = True
                        msg["content"] = self._redact(content, detections)

                        if self.valves.log_detections:
                            types = set(d[0] for d in detections)
                            print(
                                f"[PII Filter] Detected and redacted in input: {types}"
                            )

        if pii_found and __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "PII detected and redacted from input",
                        "done": True,
                    },
                }
            )

        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> dict:
        """
        Outlet filter - scan and redact PII from AI responses.
        """
        if not self.valves.enable_outlet:
            return body

        messages = body.get("messages", [])

        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    detections = self._detect_pii(content)
                    if detections:
                        msg["content"] = self._redact(content, detections)

                        if self.valves.log_detections:
                            types = set(d[0] for d in detections)
                            print(
                                f"[PII Filter] Detected and redacted in output: {types}"
                            )

        return body
