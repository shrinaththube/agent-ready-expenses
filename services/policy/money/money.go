// Package money formats integer minor-unit amounts. There are no floats here.
package money

import (
	"fmt"
	"strings"
)

// minorDigits lists the number of minor-unit digits per ISO 4217 currency.
// Anything not listed defaults to 2.
var minorDigits = map[string]int{
	"USD": 2, "EUR": 2, "GBP": 2, "CAD": 2, "INR": 2,
	"JPY": 0,
	"KWD": 3,
}

// MinorDigits returns the number of decimal digits in the currency's minor unit.
func MinorDigits(currency string) int {
	if d, ok := minorDigits[currency]; ok {
		return d
	}
	return 2
}

// Decimal renders minor units as a decimal string using the currency's own digits,
// e.g. (123456, "KWD") -> "123.456", (1500, "JPY") -> "1500".
func Decimal(minor int64, currency string) string {
	digits := MinorDigits(currency)
	neg := minor < 0
	if neg {
		minor = -minor
	}
	s := fmt.Sprintf("%d", minor)
	if digits > 0 {
		for len(s) <= digits {
			s = "0" + s
		}
		s = s[:len(s)-digits] + "." + s[len(s)-digits:]
	}
	if neg {
		s = "-" + s
	}
	return s
}

// Format renders "75.00 USD".
func Format(minor int64, currency string) string {
	return strings.TrimSpace(Decimal(minor, currency) + " " + currency)
}
