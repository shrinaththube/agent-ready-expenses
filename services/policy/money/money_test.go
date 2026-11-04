package money

import "testing"

func TestDecimal(t *testing.T) {
	tests := []struct {
		name  string
		minor int64
		cur   string
		want  string
	}{
		{"usd", 7500, "USD", "75.00"},
		{"one cent over", 7501, "USD", "75.01"},
		{"sub unit", 5, "USD", "0.05"},
		{"jpy has no decimals", 1500, "JPY", "1500"},
		{"kwd has three", 123456, "KWD", "123.456"},
		{"negative", -250, "EUR", "-2.50"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Decimal(tt.minor, tt.cur); got != tt.want {
				t.Fatalf("Decimal(%d,%s) = %q, want %q", tt.minor, tt.cur, got, tt.want)
			}
		})
	}
}
